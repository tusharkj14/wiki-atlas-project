

**PRODUCT REQUIREMENTS DOCUMENT**

**Wikipedia Geotagging Map**

*Visualise every location mentioned in any Wikipedia article on an interactive map.*

| Version | 1.0 — Draft |
| :---- | :---- |
| Date | March 2026 |
| Status | In development |

## Implementation Progress

| Component | Status | Notes |
| :---- | :---- | :---- |
| Project structure | Done | Decoupled: models, schemas, routes, services |
| Scraper service | Done | Wikipedia REST API, BeautifulSoup, strips nav/footer/refs |
| LLM Geotagger | Done | Gemini 2.0 Flash with structured output, 429 retry logic |
| Geocoder service | Done | Nominatim with 1 req/sec rate limit, in-memory cache |
| Pipeline orchestrator | Done | scrape → extract → geocode → GeoJSON FeatureCollection |
| FastAPI endpoints | Done | /health, /scrape, /scrape/preview, /extract, /scrape-and-extract, /process |
| Redis cache layer | Done | geotags:{url_hash} 7-day TTL, geocode:{place_name} permanent |
| PostgreSQL/PostGIS persistence | Done | SQLAlchemy + asyncpg + GeoAlchemy2, PostGIS geography column |
| Next.js frontend | Not started | |
| Shareable permalinks | Not started | share_slug generated on persist, lookup query ready |

# **1\. Problem Statement**

Wikipedia articles on places, events, people, and topics often reference dozens of real-world locations scattered through their text. There is no native way to see those references spatially — a reader has to mentally resolve sentences like "the battle took place near Kursk, north of Kharkiv" into geography.

This tool does that automatically: paste a Wikipedia URL, get an interactive map of every location mentioned with a short explanation of why it appears — and what relationship it has to the article's subject.

# **2\. Framework Decision**

## **Choice: Next.js \+ FastAPI sidecar**

Next.js is the correct choice for this project. The comparison at a glance:

| Dimension | Next.js | Streamlit |
| :---- | :---- | :---- |
| Map quality | First-class (react-leaflet / Mapbox GL) | Embedded iframe (pydeck / folium) |
| Async pipeline | Native async API routes \+ streaming | Single-threaded per session |
| Deployment | Vercel — one-command deploy | Streamlit Cloud or self-hosted |
| Python NLP | Via FastAPI sidecar | Native |
| Shareable URLs | Native routing \+ slugs | Requires workarounds |

| *The Python NLP/scraping ecosystem (spaCy, BeautifulSoup, LLM clients) is preserved via a small FastAPI sidecar service. Next.js handles the frontend and orchestration; Python handles the intelligence.* |
| :---- |

# **3\. Storage Decision**

## **Choice: Redis (cache) \+ PostgreSQL/PostGIS (persistence)**

Cassandra is significant overengineering for this project — it is built for Netflix-scale multi-region replication, not a Wikipedia scraper. The right split:

* Redis — hot cache layer. Key: geotags:{url\_hash}, Value: full JSON tag set. TTL of 7 days. Same URL requested again skips the scrape entirely.

* PostgreSQL with PostGIS — persistent store. Enables native geospatial queries (ST\_Within, bounding box lookups) that Cassandra cannot do without full table scans.

| *If Cassandra is required: it works as a persistent layer with a (url\_hash, place\_id) partition key, but geospatial query capability is lost and operational complexity increases significantly.* |
| :---- |

# **4\. LLM Geotagger**

## **Choice: Gemini 2.0 Flash (primary) \+ Groq/Llama 3.3 70B (fallback)**

Both options are free. Gemini is the primary because it supports native structured JSON output via response\_schema — no prompt-engineering tricks needed to get schema-compliant responses. Groq is the fallback, offering extremely fast inference if Gemini rate-limits on a long article.

| Provider | Free tier | Structured output | Best for |
| :---- | :---- | :---- | :---- |
| Gemini 2.0 Flash | 1M tokens/min | Native schema support | Primary geotagger |
| Groq (Llama 3.3 70B) | 1,000 req/day | Prompt-guided | Rate-limit fallback |
| Ollama (local) | Unlimited | Prompt-guided | Development only |

**Geotagger prompt**

| SYSTEM\_PROMPT \= """ You are a geographic analyst. Extract every real-world location mentioned in the Wikipedia article text. For each location return a JSON object with:   place\_name    : exact name as written in the text   place\_type    : city | country | region | landmark | battle\_site |                   natural\_feature | other   relationship  : birthplace | death\_place | battle\_site | headquarters |                   founded\_in | visited | mentioned | other   reason        : one sentence explaining relevance to the article subject   source\_sentence: the exact sentence from the article mentioning this place Return ONLY a valid JSON array. No preamble. No markdown. Exclude fictional places and metaphorical geography. """ |
| :---- |

# **5\. Data Model**

## **articles table**

| Field | Type | Notes |
| :---- | :---- | :---- |
| id | uuid PK | Primary key |
| url | text UNIQUE | Full Wikipedia URL |
| url\_hash | text UNIQUE | SHA-256 for cache key lookup |
| title | text | Article title |
| scraped\_at | timestamptz | Timestamp of last scrape |
| share\_slug | text UNIQUE | Short slug for permalink, e.g. xk3p9 |

## **geotags table**

| Field | Type | Notes |
| :---- | :---- | :---- |
| id | uuid PK | Primary key |
| article\_id | uuid FK | References articles.id |
| place\_name | text | Exact name as in article text |
| place\_type | enum | city | country | region | landmark | battle\_site | other |
| relationship | enum | birthplace | death\_place | battle\_site | headquarters | founded\_in | visited | mentioned | other |
| lat / lng | float | WGS84 coordinates from geocoder |
| reason | text | LLM-generated relevance sentence |
| source\_sentence | text | Original article sentence |
| geocoder | text | nominatim | google |
| created\_at | timestamptz | Row creation time |

| *PostGIS: add a geography(Point, 4326\) column on (lat, lng) for spatial queries such as ST\_Within and bounding box lookups.* |
| :---- |

## **Redis cache**

* Key: geotags:{sha256(url)}

* Value: JSON array of geotag objects (full tag set)

* TTL: 7 days — same URL within 7 days skips the entire scrape \+ LLM pipeline

* Secondary key: geocode:{place\_name} — permanent TTL for individual geocode results

# **6\. System Design**

Pipeline on a fresh request (cache miss):

1. Cache check — hash the URL, look up Redis. Cache hit returns immediately.

2. Scrape — fetch Wikipedia page, strip nav/footer/references, extract clean paragraphs and infobox text via BeautifulSoup.

3. Geotagging — send cleaned text chunks to Gemini 2.0 Flash with structured output schema. Falls back to Groq on rate limit.

4. Geocoding — for each extracted place, query Nominatim (1 req/sec). Individual results are cached in Redis permanently.

5. Persist \+ cache — write full tag set to PostgreSQL, write to Redis with 7-day TTL, generate share\_slug.

6. Respond — return GeoJSON FeatureCollection to the frontend for map rendering.

# **7\. Tech Stack**

| Layer | Choice | Reason |
| :---- | :---- | :---- |
| Frontend | Next.js 14 (App Router) | Streaming, Vercel deploy, React ecosystem |
| Map | react-leaflet \+ OpenStreetMap | Free tiles, no API key for MVP |
| Scraper | Python \+ BeautifulSoup (FastAPI sidecar) | Best HTML parsing ecosystem |
| LLM (primary) | Gemini 2.0 Flash | Free, native structured JSON output |
| LLM (fallback) | Groq / Llama 3.3 70B | Free, very fast inference |
| Geocoding | Nominatim (OSM) | Free; 1 req/sec limit acceptable for MVP |
| Cache | Redis (Upstash) | Zero-ops serverless Redis, TTL-native |
| Database | PostgreSQL \+ PostGIS (Supabase) | Geo queries, free tier, managed |
| Deployment | Vercel (Next.js) \+ Railway (FastAPI) | Simple, cheap |

# **8\. Features**

## **MVP**

* Wikipedia URL input field

* Scrape and clean article text (paragraphs, infobox, captions)

* Extract location mentions with LLM — name, type, relationship, reason

* Geocode each location to lat/lng via Nominatim

* Interactive map with pins; clicking a pin shows reason \+ relationship

* Cache results so re-requesting the same URL is instant

* Shareable permalink — /map/{slug} — generated on first scrape

## **V2**

* Sidebar list of all tags, sortable by type or relationship

* Filter pins by place\_type and relationship enum

* Export as GeoJSON or KML

* Multi-article comparison on the same map

* Heatmap mode for tag density

# **9\. Scope & Constraints**

* English Wikipedia only — no multilingual support in MVP

* Nominatim rate limit: 1 req/sec — scraped articles with 50+ locations will take \~1 min to geocode on first request

* LLM accuracy: fictional places and metaphorical geography excluded by prompt; edge cases may require manual review

* No user authentication in MVP — permalinks are public and unguarded

* Cassandra explicitly out of scope — PostgreSQL/PostGIS handles all persistence needs at this scale

# **10\. Project Structure**

wikimap/
│
├── apps/
│   ├── web/                  # Next.js frontend (not started)
│   └── api/
│       ├── main.py           # App factory — middleware + router includes
│       ├── schemas.py         # All request/response Pydantic models
│       └── routes/
│           ├── health.py      # GET /health
│           ├── scraper.py     # POST /scrape, /scrape/preview
│           ├── nlp.py         # POST /extract, /scrape-and-extract
│           └── pipeline.py    # POST /process (full pipeline → GeoJSON)
│
├── services/
│   ├── scraper/
│   │   └── wikipedia.py       # Wikipedia REST API fetch + BeautifulSoup parse
│   ├── nlp/
│   │   └── geotagger.py       # Gemini 2.0 Flash structured extraction
│   ├── geocoder/
│   │   └── geocode.py         # Nominatim geocoding with rate limiting
│   ├── cache/                 # Redis cache (not started)
│   └── pipeline/
│       └── process_page.py    # Orchestrator: scrape → extract → geocode → GeoJSON
│
├── db/
│   ├── redis/                 # Redis client (not started)
│   └── postgres/              # PostgreSQL/PostGIS schema + queries (not started)
│
├── jobs/                      # Background persistence (not started)
│
├── lib/
│   └── types/
│       └── models.py          # Domain models: ScrapedArticle, GeoTag, GeocodedTag
│
├── tests/
│
├── main.py                    # Entry point — launches uvicorn
└── pyproject.toml             # uv-managed dependencies

# **11\. Layer Responsibilities**

apps/: Entry points (frontend \+ API)\\  
services/: Core business logic (scraping, NLP, geocoding,  
orchestration)\\  
db/: Database interaction layer\\  
jobs/: Background processing and persistence\\  
lib/: Shared utilities and types\\  
tests/: Unit and integration tests

