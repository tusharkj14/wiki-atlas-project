"""
LLM-powered geotagger.

Sends cleaned Wikipedia article text to Gemini 2.0 Flash and receives
structured location extractions.
"""

import asyncio
import json
import logging
import os
import time

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ClientError, ServerError

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
  city            : the nearest major city this location is in or near (e.g. "Bangalore", "London", "Tokyo"). For cities themselves, repeat the city name. For countries or large regions, leave as empty string "". This field is critical for geocoding accuracy of local places like neighborhoods, roads, and suburbs.

IMPORTANT DISAMBIGUATION RULES:
- Always interpret place names in the context of the article's subject.
- If a place name is ambiguous, prefer the interpretation that is geographically consistent with the article's topic and other locations mentioned.
- Do NOT extract the country itself as a location when the article is about a place within that country (e.g. do not extract "India" when the article is about a neighborhood in Bangalore). Only extract countries when they are meaningfully distinct from the article's subject.
- Do NOT extract generic infrastructure names that exist in every city (e.g. "Outer Ring Road", "Sector 4", "Main Street", "Highway 1", "Block A") unless they are globally unique landmarks.
- Do NOT extract vague directional or sub-national regions that cannot be pinpointed on a map (e.g. "North India", "South China", "Eastern Europe", "the north", "the west", "Central Asia"). Only extract regions that are officially named administrative divisions (e.g. "Uttar Pradesh", "Guangdong", "Bavaria").
- Do NOT extract continent names (e.g. "Asia", "Europe") or very large political/cultural blocs.

Return ONLY a valid JSON array. No preamble. No markdown. Exclude fictional places and metaphorical geography."""

# Models to rotate through on the free tier.
# On a 429, we move to the next model instead of waiting 30s.
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
]

MAX_RETRIES = len(GEMINI_MODELS) * 2  # two full rotations
RETRY_DELAY = 10  # seconds to wait before retrying the same model
MIN_REQUEST_INTERVAL = 2.0  # seconds between any Gemini call

_last_request_time: float = 0.0


# ── Gemini provider ─────────────────────────────────────────────────

async def _throttle():
    """Enforce minimum interval between Gemini API calls."""
    global _last_request_time

    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        wait = MIN_REQUEST_INTERVAL - elapsed
        logger.debug("Throttling Gemini request for %.1fs", wait)
        await asyncio.sleep(wait)
    _last_request_time = time.monotonic()


async def _extract_gemini(text: str, title: str) -> list[GeoTag]:
    """Extract locations using Gemini, rotating through models on rate limits."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    user_prompt = f"Article title: {title}\n\n{text}"

    last_error = None
    for attempt in range(MAX_RETRIES):
        model = GEMINI_MODELS[attempt % len(GEMINI_MODELS)]

        await _throttle()
        try:
            logger.info("Gemini attempt %d/%d using %s", attempt + 1, MAX_RETRIES, model)
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": list[GeoTag],
                },
            )
            raw = json.loads(response.text)
            return [GeoTag(**item) for item in raw]

        except (ClientError, ServerError) as e:
            last_error = e
            code = getattr(e, "code", None) or getattr(e, "status_code", 0)
            if code in (429, 503):
                logger.warning(
                    "Gemini %s on %s (attempt %d/%d), rotating to next model in %ds",
                    code, model, attempt + 1, MAX_RETRIES, RETRY_DELAY,
                )
                await asyncio.sleep(RETRY_DELAY)
            else:
                raise

    raise RuntimeError(
        f"All Gemini models rate-limited after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}. Falling back to Groq."
    )


# ── Groq fallback ──────────────────────────────────────────────────

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

async def _extract_groq(text: str, title: str) -> list[GeoTag]:
    """Extract locations using Groq (Llama) as fallback. Prompt-guided JSON."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")

    user_prompt = f"Article title: {title}\n\n{text}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    raw = json.loads(content)

    print(f"Groq raw response: {raw}")

    # Groq may return {"locations": [...]} or just [...]
    if isinstance(raw, dict):
        raw = raw.get("locations", raw.get("results", list(raw.values())[0]))
    if not isinstance(raw, list):
        raise ValueError(f"Unexpected Groq response shape: {type(raw)}")

    return [GeoTag(**_normalize_tag(item)) for item in raw]


# Map non-standard place_type/relationship values to valid enum values
_PLACE_TYPE_MAP: dict[str, str] = {
    "suburb": "region", "town": "city", "village": "city",
    "locality": "region", "neighborhood": "region", "neighbourhood": "region",
    "district": "region", "state": "region", "province": "region",
    "road": "landmark", "street": "landmark", "highway": "landmark",
    "sector": "region", "constituency": "region", "municipality": "region",
    "lake": "natural_feature", "river": "natural_feature", "mountain": "natural_feature",
    "park": "landmark", "building": "landmark", "monument": "landmark",
    "island": "natural_feature", "bay": "natural_feature", "sea": "natural_feature",
    "ocean": "natural_feature", "forest": "natural_feature", "desert": "natural_feature",
}

_RELATIONSHIP_MAP: dict[str, str] = {
    "located_in": "mentioned", "part_of": "mentioned", "near": "mentioned",
    "capital": "mentioned", "border": "mentioned", "adjacent": "mentioned",
    "origin": "birthplace", "born": "birthplace", "died": "death_place",
    "residence": "visited", "lived": "visited", "worked": "visited",
    "built": "founded_in", "established": "founded_in", "created": "founded_in",
}

_VALID_PLACE_TYPES = {"city", "country", "region", "landmark", "battle_site", "natural_feature", "other"}
_VALID_RELATIONSHIPS = {"birthplace", "death_place", "battle_site", "headquarters", "founded_in", "visited", "mentioned", "other"}


def _normalize_tag(item: dict) -> dict:
    """Normalize Groq's free-form place_type and relationship to valid enum values."""
    pt = item.get("place_type", "other").lower().strip()
    if pt not in _VALID_PLACE_TYPES:
        item["place_type"] = _PLACE_TYPE_MAP.get(pt, "other")

    rel = item.get("relationship", "other").lower().strip()
    if rel not in _VALID_RELATIONSHIPS:
        item["relationship"] = _RELATIONSHIP_MAP.get(rel, "mentioned")

    return item


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


def _is_country_self_ref(tag: GeoTag) -> bool:
    """True if the tag is just the country itself (e.g. place_name='India', country='India')."""
    if not tag.country:
        return False
    return tag.place_name.strip().lower() == tag.country.strip().lower()


# Generic local names that exist in every city and can't be reliably geocoded
_GENERIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(sector|block|phase|zone|ward|plot)\s+\w{1,4}$", re.IGNORECASE),
    re.compile(r"^(main|ring|outer|inner|old|new)\s+(road|street|highway|avenue|boulevard)$", re.IGNORECASE),
    re.compile(r"^(highway|road|street|avenue|lane|drive)\s+\d+$", re.IGNORECASE),
    re.compile(r"^(the\s+)?(old|new)\s+(city|town)$", re.IGNORECASE),
]


def _is_generic_local(tag: GeoTag) -> bool:
    """True if the place name is a generic local feature that can't be reliably geocoded."""
    name = tag.place_name.strip()
    return any(p.match(name) for p in _GENERIC_PATTERNS)


def _filter_tags(tags: list[GeoTag]) -> list[GeoTag]:
    """Remove tags that are vague, country self-refs, or generic local names."""
    filtered = []
    for tag in tags:
        if _is_vague_place(tag.place_name):
            logger.info("Filtered vague place: '%s'", tag.place_name)
        elif _is_country_self_ref(tag):
            logger.info("Filtered country self-ref: '%s'", tag.place_name)
        elif _is_generic_local(tag):
            logger.info("Filtered generic local: '%s'", tag.place_name)
        else:
            filtered.append(tag)
    return filtered


# ── Public API ───────────────────────────────────────────────────────

async def extract_locations(text: str, title: str) -> list[GeoTag]:
    """
    Extract geographic locations from article text.
    Tries Groq models first, falls back to Gemini if all are unavailable.
    """
    try:
        logger.info("Extracting locations with Groq")
        tags = await _extract_groq(text, title)
        
    except RuntimeError as e:
        logger.warning("Extracting locations with Groq failed, falling back to Gemini: %s", e)
        tags = await _extract_gemini(text, title)
    return _filter_tags(tags)
