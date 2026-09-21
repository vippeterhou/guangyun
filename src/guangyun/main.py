from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from guangyun import __version__
from guangyun.api.routes import router
from guangyun.config import cors_origins, database_path
from guangyun.database import get_connection
from guangyun.repository import source_metadata, variant_source_metadata

PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")


@asynccontextmanager
async def lifespan(_: FastAPI):
    path = database_path()
    if not path.is_file():
        raise RuntimeError(
            f"Database not found at {path}. Run `python scripts/import_sbgy.py` first."
        )
    with get_connection(path) as connection:
        dictionary = source_metadata(connection)
        variants = variant_source_metadata(connection)
    app.state.data_version = f"cjkvi-{dictionary['commit_sha'][:12]}-unihan-{variants['version']}"
    yield


app = FastAPI(
    title="廣韻 API",
    summary="Character lookup for 校正宋本廣韻",
    description=(
        "Search the CJKVI 校正宋本廣韻 data by character, small rhyme, rhyme, volume, or fanqie."
    ),
    version=__version__,
    lifespan=lifespan,
    license_info={
        "name": "GPL-2.0 data",
        "url": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
app.include_router(router)


@app.middleware("http")
async def cache_read_only_api(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET" and request.url.path.startswith("/api/v1/"):
        response.headers["X-Data-Version"] = app.state.data_version
        if request.url.path == "/api/v1/health":
            response.headers["Cache-Control"] = "no-store"
        elif response.status_code == 200:
            max_age = (
                86400
                if request.url.path
                in {
                    "/api/v1/overview",
                    "/api/v1/source",
                    "/api/v1/volumes",
                    "/api/v1/rhymes",
                }
                else 3600
            )
            response.headers["Cache-Control"] = f"public, max-age={max_age}"
    return response


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/overview", response_class=HTMLResponse, include_in_schema=False)
def overview_page(request: Request):
    return templates.TemplateResponse(request=request, name="overview.html")
