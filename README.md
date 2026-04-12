<p align="center">
  <img src="docs/logo.png" alt="WikiAtlas" width="80" />
</p>

<h1 align="center">WikiAtlas</h1>

<p align="center">
  <strong>Visualize every location mentioned in any Wikipedia article on an interactive map.</strong>
</p>

<p align="center">
  <a href="#demo">View Demo</a> &middot;
  <a href="#getting-started">Get Started</a> &middot;
  <a href="DEPLOYMENT.md">Deploy</a> &middot;
  <a href="#contributing">Contribute</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.135+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

---

<!-- Replace with actual screenshot/GIF -->
<p align="center">
  <img src="docs/demo.gif" alt="WikiAtlas Demo" width="700" />
</p>

## What is WikiAtlas?

Paste a Wikipedia URL and get an interactive map of every real-world location mentioned in the article — with context on *why* each place is relevant.

Wikipedia articles reference dozens of locations scattered through their text. WikiAtlas extracts them automatically using an LLM, geocodes them, and plots them on a map you can explore and share.

## Demo

> **Live demo:** [wikiatlas.vercel.app](https://wikiatlas.vercel.app) 

<!-- Remove this note once deployed -->

## How It Works

```
  Wikipedia URL
       │
       ▼
 ┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
 │  Scraper   │ ──▶ │  Gemini   │ ──▶ │ Nominatim │ ──▶ │  Leaflet  │
 │ (BS4)      │     │  (LLM)    │     │ (Geocode) │     │   Map     │
 └───────────┘     └───────────┘     └───────────┘     └───────────┘
   Fetch &           Extract           Resolve           Render
   parse HTML        locations         lat/lng            GeoJSON
```

1. **Scrape** — Fetches the article via Wikipedia REST API, strips boilerplate, extracts paragraphs + infobox
2. **Extract** — Gemini 2.5 Flash returns structured JSON: place name, type, relationship, reason
3. **Geocode** — Nominatim resolves places to coordinates with country-code biasing and triple-layer caching
4. **Display** — GeoJSON FeatureCollection rendered on a Leaflet map with interactive popups

Cached in Redis — re-requesting the same article is instant.

## Features

- Wikipedia search with autocomplete
- LLM-powered location extraction with structured output
- Vague place name filtering ("North India", "Eastern Europe", etc.)
- Geographic outlier detection via haversine distance
- Country-biased geocoding to prevent mis-resolution
- Concurrent geocoding with Nominatim rate limit compliance
- Redis caching (7-day TTL) for instant repeat lookups
- Shareable permalinks (`/map/{slug}`)
- Recent searches sidebar (session storage)
- Responsive design with loading states

## Tech Stack

| Layer       | Technology                                |
|-------------|-------------------------------------------|
| Frontend    | Next.js 14 &middot; React 18 &middot; Tailwind CSS |
| Map         | Leaflet &middot; react-leaflet &middot; OpenStreetMap tiles |
| Backend     | FastAPI &middot; Uvicorn (async)          |
| LLM         | Gemini 2.5 Flash (structured JSON output) |
| Geocoding   | Nominatim (OpenStreetMap)                 |
| Cache       | Redis 7                                   |
| Database    | PostgreSQL 16 &middot; PostGIS            |
| Package Mgr | uv (Python) &middot; npm (Node)           |

## Getting Started

### Prerequisites

- **Python 3.12+** and [uv](https://docs.astral.sh/uv/)
- **Node.js 18+** and npm
- **Docker** (for Redis + PostgreSQL)
- A free [Gemini API key](https://aistudio.google.com/apikey)

### Setup

```bash
# Clone
git clone https://github.com/your-username/wikiatlas.git
cd wikiatlas

# Environment variables
cp .env.example .env
# Edit .env → add your GEMINI_API_KEY
```

<details>
<summary><strong>.env</strong> (project root)</summary>

```env
GEMINI_API_KEY=your_key_here
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/wikiatlas
REDIS_URL=redis://localhost:6379/0
```

</details>

<details>
<summary><strong>.env.local</strong> (apps/web/)</summary>

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

</details>

### Run

```bash
# 1. Start Redis + PostgreSQL
docker compose up -d

# 2. Start backend (terminal 1)
uv sync
uv run python main.py          # → http://localhost:8000

# 3. Start frontend (terminal 2)
cd apps/web
npm install
npm run dev                     # → http://localhost:3000
```

Or use the one-command scripts (starts infra + backend):

```bash
./start.sh        # macOS / Linux
.\start.ps1       # Windows
```

Open **http://localhost:3000** and paste any Wikipedia URL.

## API

| Method | Endpoint                | Description                          |
|--------|-------------------------|--------------------------------------|
| `GET`  | `/health`               | Health check                         |
| `POST` | `/process`              | Full pipeline — scrape, extract, geocode, return GeoJSON |
| `POST` | `/scrape`               | Scrape a Wikipedia article           |
| `POST` | `/scrape/preview`       | First 3 paragraphs preview           |
| `POST` | `/extract`              | Extract locations from text via LLM  |
| `POST` | `/scrape-and-extract`   | Scrape + extract in one call         |
| `GET`  | `/article/{slug}`       | Retrieve processed article by share slug |

<details>
<summary><strong>Example request</strong></summary>

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Battle_of_Waterloo"}'
```

Returns a GeoJSON FeatureCollection with all extracted locations, metadata, and a shareable slug.

</details>

## Project Structure

```
WikiAtlas/
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── main.py                 # App factory, CORS, routers
│   │   ├── schemas.py              # Pydantic request/response models
│   │   └── routes/                 # Endpoint handlers
│   └── web/                        # Next.js frontend
│       └── src/
│           ├── app/                # Pages (home, /map/[slug])
│           ├── components/         # MapView, SearchBar, Sidebar, etc.
│           ├── hooks/              # useProcessArticle, useSearchHistory
│           └── lib/api.ts          # API client
├── services/
│   ├── scraper/wikipedia.py        # Wikipedia fetch + BS4 parse
│   ├── nlp/geotagger.py            # Gemini extraction + vague filter
│   ├── geocoder/geocode.py         # Nominatim + country bias + concurrency
│   └── pipeline/process_page.py    # Orchestrator + outlier detection
├── db/
│   ├── postgres/                   # SQLAlchemy models + queries
│   └── redis/                      # Async cache client
├── lib/types/models.py             # Domain models
├── docker-compose.yml              # Dev infrastructure
├── main.py                         # Entry point
└── pyproject.toml                  # Python dependencies
```

## Architecture Decisions

| Decision    | Choice                  | Why                                            |
|-------------|-------------------------|------------------------------------------------|
| Frontend    | Next.js | First-class maps, shareable URLs, SSR          |
| LLM         | Gemini 2.5 Flash        | Free, native structured JSON output            |
| Geocoder    | Nominatim               | Free, no API key, sufficient for MVP           |
| Database    | PostgreSQL + PostGIS    | Spatial queries, great free managed tiers      |
| Cache       | Redis                   | TTL-native, simple, fast                       |
| Python pkgs | uv                      | Fast installs, lockfile, Python 3.12+          |

## Contributing

Contributions are welcome! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes
4. Push and open a Pull Request

For bugs or feature requests, [open an issue](../../issues).

## License

[MIT](LICENSE)
