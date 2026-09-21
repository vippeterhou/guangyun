# 廣韻查詢

按漢字查詢《校正宋本廣韻》的卷、韻、小韻、反切與釋義，並提供公開 REST API。
簡體字會通過 Unicode Unihan 映射自動查詢所有對應繁體，例如 `东` → `東`、
`发` → `發`／`髮`。

## Data

The canonical source is CJKVI's `sbgy.xml`, pinned by commit and SHA-256 in
`data/sources.json`. The source and transformed dictionary data are GPL-2.0;
see `DATA_LICENSE.md`.

Simplified/traditional aliases come from Unicode 17.0.0
`Unihan_Variants.txt`, pinned in `data/sources.json` under the Unicode
License V3.

Complete data license texts and attribution are included in `LICENSES/`,
`DATA_LICENSE.md`, and `THIRD_PARTY_NOTICES.md`.

## Development

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python scripts/fetch_data.py
.venv/bin/python scripts/import_sbgy.py
.venv/bin/uvicorn guangyun.main:app --reload
```

Open:

- Website: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs
- Character lookup: http://127.0.0.1:8000/api/v1/characters?char=東
- Whole-book overview: http://127.0.0.1:8000/overview

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/characters?char=東` | Look up all entries for one character |
| `GET /api/v1/characters?char=东` | Resolve simplified aliases and return traditional entries |
| `GET /api/v1/entries/{id}` | Retrieve one dictionary entry |
| `GET /api/v1/small-rhymes/{id}` | Retrieve a small rhyme and its entries |
| `GET /api/v1/volumes` | List the five volumes |
| `GET /api/v1/rhymes` | List the 206 rhymes |
| `GET /api/v1/rhymes/{id}` | Retrieve one rhyme and its small rhymes |
| `GET /api/v1/overview` | Retrieve whole-book counts, rhyme density, and data profile |
| `GET /api/v1/overview/fanqie?mode=core` | Retrieve the core or global fanqie network |
| `GET /api/v1/search/fanqie?q=德紅` | Search by fanqie |
| `GET /api/v1/source` | Retrieve source and license metadata |
| `GET /api/v1/health` | Health check |

Responses include the source project, pinned revision, and data license.

## Validate

```bash
.venv/bin/python scripts/validate_data.py
.venv/bin/pytest
.venv/bin/ruff check .
```

## Docker

Build the database before creating the image:

```bash
.venv/bin/python scripts/import_sbgy.py
docker build -t guangyun .
docker run --rm -p 8000:8000 guangyun
```

## Deploy to Render

The repository includes `render.yaml`. Create a new Render Blueprint from the
GitHub repository; Render will:

1. Install the application.
2. Download and checksum the pinned CJKVI and Unihan sources.
3. Build and validate the read-only SQLite database.
4. Start two Uvicorn workers.
5. Monitor `/api/v1/health`.

No persistent disk or external database is required. The SQLite database is
rebuilt for each deployment and remains read-only at runtime.

The Blueprint selects Render's Free compute plan. Free services spin down after
15 minutes without inbound traffic and can take about a minute to start again.
This is suitable for an initial hobby deployment, but not for an availability
guarantee.

After the Render URL is healthy, attach the production domain and place it
behind Cloudflare. Do not cache `/api/v1/health`; other successful GET API
responses include cache headers and an `X-Data-Version` header.

## Configuration

- `GUANGYUN_ROOT`: project root containing `data/sources.json`.
- `GUANGYUN_DB`: SQLite database path.
- `GUANGYUN_CORS_ORIGINS`: comma-separated allowed origins; defaults to `*`.
