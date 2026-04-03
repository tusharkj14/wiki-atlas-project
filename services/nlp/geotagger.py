"""
LLM-powered geotagger.

Sends cleaned Wikipedia article text to Gemini 2.0 Flash and receives
structured location extractions.
"""

import asyncio
import json
import logging
import os

from dotenv import load_dotenv

from lib.types.models import GeoTag

load_dotenv()

logger = logging.getLogger(__name__)

# ── System prompt (from PRD) ────────────────────────────────────────

SYSTEM_PROMPT = """You are a geographic analyst. Extract every real-world location mentioned in the Wikipedia article text.

For each location return a JSON object with:
  place_name      : exact name as written in the text
  place_type      : city | country | region | landmark | battle_site | natural_feature | other
  relationship    : birthplace | death_place | battle_site | headquarters | founded_in | visited | mentioned | other
  reason          : one sentence explaining relevance to the article subject
  source_sentence : the exact sentence from the article mentioning this place
  country         : the country this location is in (use modern country names, e.g. "India", "Turkey"). For countries themselves, repeat the country name. This field is critical for disambiguation during geocoding.

IMPORTANT DISAMBIGUATION RULES:
- Always interpret place names in the context of the article's subject.
- If a place name is ambiguous, prefer the interpretation that is geographically consistent with the article's topic and other locations mentioned.
- Do NOT extract vague directional or sub-national regions that cannot be pinpointed on a map (e.g. "North India", "South China", "Eastern Europe", "the north", "the west", "Central Asia"). Only extract regions that are officially named administrative divisions (e.g. "Uttar Pradesh", "Guangdong", "Bavaria").
- Do NOT extract continent names (e.g. "Asia", "Europe") or very large political/cultural blocs.

Return ONLY a valid JSON array. No preamble. No markdown. Exclude fictional places and metaphorical geography."""

MAX_RETRIES = 3
MIN_REQUEST_INTERVAL = 4.0  # seconds between Gemini calls

_last_request_time: float = 0.0


# ── Gemini provider ─────────────────────────────────────────────────

async def _throttle():
    """Enforce minimum interval between Gemini API calls."""
    global _last_request_time
    import time

    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        wait = MIN_REQUEST_INTERVAL - elapsed
        logger.debug("Throttling Gemini request for %.1fs", wait)
        await asyncio.sleep(wait)
    _last_request_time = time.monotonic()


async def _extract_gemini(text: str, title: str) -> list[GeoTag]:
    """Extract locations using Gemini with native structured output."""
    from google import genai
    from google.genai.errors import ClientError

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    user_prompt = f"Article title: {title}\n\n{text}"

    for attempt in range(MAX_RETRIES):
        await _throttle()
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=user_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": list[GeoTag],
                },
            )
            raw = json.loads(response.text)
            return [GeoTag(**item) for item in raw]

        except ClientError as e:
            if e.code == 429:
                wait = (attempt + 1) * 30
                logger.warning("Gemini 429 rate limited. Retrying in %ds (attempt %d/%d)", wait, attempt + 1, MAX_RETRIES)
                await asyncio.sleep(wait)
            else:
                raise

    raise RuntimeError("Gemini rate limit exceeded after all retries. Wait a minute and try again.")


# ── Vague place filter ──────────────────────────────────────────────

import re

_VAGUE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(north|south|east|west|central|northern|southern|eastern|western|northeast|northwest|southeast|southwest)\s+", re.IGNORECASE),
    re.compile(r"^(the\s+)?(north|south|east|west|middle east)$", re.IGNORECASE),
    re.compile(r"^(asia|europe|africa|north america|south america|oceania|antarctica|the americas)$", re.IGNORECASE),
    re.compile(r"^(indian subcontinent|indian sub-?continent|subcontinent)$", re.IGNORECASE),
]

# Allow through known legitimate places that start with directional words
_VAGUE_ALLOWLIST: set[str] = {
    "south africa", "south korea", "north korea", "north macedonia",
    "east timor", "central african republic", "western sahara",
    "south sudan", "south georgia", "north carolina", "south carolina",
    "north dakota", "south dakota", "west virginia", "western australia",
    "east java", "west java", "central java", "north sumatra",
    "east kalimantan", "west bengal", "north rhine-westphalia",
}


def _is_vague_place(name: str) -> bool:
    """Return True if the place name is too vague to pin on a map."""
    if name.strip().lower() in _VAGUE_ALLOWLIST:
        return False
    return any(p.match(name.strip()) for p in _VAGUE_PATTERNS)


def _filter_vague(tags: list[GeoTag]) -> list[GeoTag]:
    """Remove tags with vague, un-pinpointable place names."""
    filtered = []
    for tag in tags:
        if _is_vague_place(tag.place_name):
            logger.info("Filtered vague place: '%s'", tag.place_name)
        else:
            filtered.append(tag)
    return filtered


# ── Public API ───────────────────────────────────────────────────────

async def extract_locations(text: str, title: str) -> list[GeoTag]:
    """
    Extract geographic locations from article text using Gemini.
    """
    logger.info("Extracting locations with Gemini")
    tags = await _extract_gemini(text, title)
    return _filter_vague(tags)
