# WikiMap

**Visualize every location mentioned in any Wikipedia article on an interactive map.**

Paste a Wikipedia URL, and WikiMap scrapes the article, uses an LLM to extract every real-world location mentioned, geocodes them, and plots them on a Leaflet map — with context on *why* each place is relevant.

![WikiMap Screenshot](docs/screenshot.png)

## How It Works

```
Wikipedia URL
     │
     ▼
┌─────────┐    ┌──────────┐    ┌───────────┐    ┌─────────┐
│ Scraper  │ ─▶ │ Gemini   │ ─▶ │ Nominatim │ ─▶ │ GeoJSON │
│ (BS4)   │    │ (LLM)    │    │ (Geocode) │    │  + Map  │
└─────────┘    └──────────┘    └───────────┘    └─────────┘
```

1. **Scrape** — Fetches the Wikipedia article via REST API, strips navigation/references, extracts clean paragraphs + infobox data
2. **Extract** — Sends text to Gemini 2.5 Flash which returns structured JSON: place name, type, relationship to the article, and a reason sentence
3. **Geocode** — Resolves each place to lat/lng via Nominatim with country-code biasing, concurrent staggered requests, and triple-layer caching (in-memory → Redis → API)
4. **Display** — Returns a GeoJSON FeatureCollection rendered on a Leaflet map with interactive popups

Results are cached in Redis (7-day TTL) — re-requesting the same article is instant.

## Tech Stack

| Layer       | Technology                              |
|-------------|-----------------------------------------|
| Frontend    | Next.js 14, React 18, Tailwind CSS      |
| Map         | Leaflet + react-leaflet + OSM tiles      |
| Backend API | FastAPI + Uvicorn (async)                |
| LLM         | Gemini 2.5 Flash (structured JSON output)|
| Geocoding   | Nominatim (OpenStreetMap)                |
| Cache       | Redis 7 (geotag + geocode caching)      |
| Database    | PostgreSQL 16 + PostGIS                  |
| Language    | Python 3.12, TypeScript 5                |

## Features

- Wikipedia search with autocomplete (OpenSearch API)
- LLM-powered location extraction with disambiguation rules
- Vague place name filtering ("North India", "Eastern Europe" etc.)
- Geographic outlier detection (haversine distance from cluster median)
- Country-code biased geocoding to prevent mis-resolution
- Concurrent geocoding with rate limit compliance
- Redis caching for instant repeat lookups
- Shareable permalink for each processed article (`/map/{slug}`)
- Recent searches sidebar (browser session storage)
- Responsive UI with loading states

## Project Structure

```
wiki-project/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── main.py             # App factory, CORS, router includes
│   │   ├── schemas.py          # Request/response Pydantic models
│   │   └── routes/
│   │       ├── health.py       # GET  /health
│   │       ├── scraper.py      # POST /scrape, /scrape/preview
│   │       ├── nlp.py          # POST /extract, /scrape-and-extract
│   │       ├── pipeline.py     # POST /process (full pipeline)
│   │       └── share.py        # GET  /article/{slug}
│   └── web/                    # Next.js frontend
│       └── src/
│           ├── app/
│           │   ├── page.tsx          # Home — search + map
│           │   └── map/[slug]/       # Shareable article page
│           ├── components/
│           │   ├── MapView.tsx       # Leaflet map with markers
│           │   ├── WikiSearchBar.tsx # Search input + autocomplete
│           │   ├── SearchHistory.tsx # Recent searches sidebar
│           │   ├── PinPopup.tsx      # Marker popup with context
│           │   ├── ResultsHeader.tsx # Article metadata bar
│           │   └── ShareButton.tsx   # Copy share link
│           ├── hooks/
│           │   ├── useProcessArticle.ts  # API call state machine
│           │   └── useSearchHistory.ts   # Session storage hook
│           └── lib/
│               └── api.ts            # API client
├── services/
│   ├── scraper/wikipedia.py    # Wikipedia fetch + BeautifulSoup parse
│   ├── nlp/geotagger.py        # Gemini structured extraction + vague filter
│   ├── geocoder/geocode.py     # Nominatim + country bias + concurrent batch
│   └── pipeline/process_page.py # Orchestrator + outlier detection
├── db/
│   ├── postgres/               # SQLAlchemy models, engine, queries
│   └── redis/                  # Async Redis cache client
├── lib/types/models.py         # Domain models (GeoTag, ScrapedArticle, etc.)
├── docker-compose.yml          # Redis + PostgreSQL (dev)
├── main.py                     # Entry point — launches Uvicorn
└── pyproject.toml              # Python dependencies (uv)
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker (for Redis + PostgreSQL)
- [uv](https://docs.astral.sh/uv/) package manager
- A [Gemini API key](https://aistudio.google.com/apikey) (free)

### 1. Clone and configure

```bash
git clone https://github.com/your-username/wiki-project.git
cd wiki-project
```

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/wikimap
REDIS_URL=redis://localhost:6379/0
```

Create `apps/web/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Start infrastructure

```bash
docker compose up -d
```

This starts Redis (port 6379) and PostgreSQL/PostGIS (port 5432).

### 3. Start the backend

```bash
uv sync          # install Python dependencies
uv run python main.py   # starts FastAPI on http://localhost:8000
```

### 4. Start the frontend

```bash
cd apps/web
npm install
npm run dev      # starts Next.js on http://localhost:3000
```

Open http://localhost:3000 and paste a Wikipedia URL.

### One-command start (backend + infra)

```bash
# macOS/Linux
./start.sh

# Windows
.\start.ps1
```

> These scripts start Docker, wait for services to be healthy, then launch the FastAPI server. The frontend still needs to be started separately.

## API Endpoints

| Method | Endpoint              | Description                                     |
|--------|-----------------------|-------------------------------------------------|
| GET    | `/health`             | Health check                                    |
| POST   | `/scrape`             | Scrape a Wikipedia article                      |
| POST   | `/scrape/preview`     | First 3 paragraphs of an article                |
| POST   | `/extract`            | Extract locations from text via LLM             |
| POST   | `/scrape-and-extract` | Scrape + extract in one call                    |
| POST   | `/process`            | **Full pipeline** — scrape, extract, geocode, return GeoJSON |
| GET    | `/article/{slug}`     | Retrieve a previously processed article by share slug |

### Example

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Battle_of_Waterloo"}'
```

Response includes a GeoJSON FeatureCollection with all extracted locations.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment instructions, including:

- Dockerfiles for production builds
- Docker Compose production config
- **Free-tier hosting** (Vercel + Render + Neon + Upstash = $0/mo)
- VPS deployment with Oracle Cloud Always Free
- Nginx/Caddy reverse proxy setup
- CI/CD pipeline with GitHub Actions

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend framework | Next.js over Streamlit | First-class map support, shareable URLs, SSR |
| LLM provider | Gemini 2.5 Flash | Free tier, native structured JSON output |
| Geocoder | Nominatim | Free, no API key needed for MVP |
| Database | PostgreSQL + PostGIS | Spatial queries, free managed options |
| Cache | Redis | TTL-native, fast, simple key-value caching |
| Package manager | uv | Fast, lockfile support, Python 3.12+ |

## License

MIT
