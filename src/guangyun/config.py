from __future__ import annotations

import os
from pathlib import Path


def _project_root() -> Path:
    configured = os.environ.get("GUANGYUN_ROOT")
    if configured:
        return Path(configured).resolve()

    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "data" / "sources.json").is_file():
        return source_root
    return Path.cwd().resolve()


PROJECT_ROOT = _project_root()
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "guangyun.sqlite"
DEFAULT_SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "sbgy.xml"
DEFAULT_VARIANT_SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "Unihan_Variants.txt"
DEFAULT_SOURCES_PATH = PROJECT_ROOT / "data" / "sources.json"


def database_path() -> Path:
    return Path(os.environ.get("GUANGYUN_DB", DEFAULT_DATABASE_PATH)).resolve()


def cors_origins() -> list[str]:
    value = os.environ.get("GUANGYUN_CORS_ORIGINS", "*")
    return [origin.strip() for origin in value.split(",") if origin.strip()]
