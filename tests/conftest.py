from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from guangyun.config import (
    DEFAULT_SOURCE_PATH,
    DEFAULT_SOURCES_PATH,
    DEFAULT_VARIANT_SOURCE_PATH,
)
from guangyun.importer import create_database


@pytest.fixture(scope="session")
def database_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("data") / "guangyun.sqlite"
    create_database(
        DEFAULT_SOURCE_PATH,
        path,
        DEFAULT_SOURCES_PATH,
        DEFAULT_VARIANT_SOURCE_PATH,
    )
    return path


@pytest.fixture()
def client(database_file: Path):
    os.environ["GUANGYUN_DB"] = str(database_file)
    from guangyun.main import app

    with TestClient(app) as test_client:
        yield test_client
