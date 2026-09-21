from __future__ import annotations

import unicodedata
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from guangyun.database import get_connection
from guangyun.repository import (
    character_aliases,
    entries_for_character,
    entry_by_id,
    fanqie_network,
    list_rhymes,
    list_volumes,
    overview_summary,
    rhyme_overview,
    search_fanqie,
    small_rhyme_by_id,
    source_metadata,
    variant_source_metadata,
)

router = APIRouter(prefix="/api/v1")


def valid_character_query(value: str) -> bool:
    if not value or len(value) > 2:
        return False
    if len(value) == 2:
        codepoint = ord(value[1])
        if not (0xFE00 <= codepoint <= 0xFE0F or 0xE0100 <= codepoint <= 0xE01EF):
            return False
    return not unicodedata.category(value[0]).startswith(("C", "Z"))


def validate_character_query(value: str) -> None:
    if not valid_character_query(value):
        raise HTTPException(
            status_code=422,
            detail="char must contain one character, optionally followed by a variation selector",
        )


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    with get_connection() as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@router.get("/source", tags=["system"])
def source() -> dict:
    with get_connection() as connection:
        return {
            "dictionary": source_metadata(connection),
            "character_variants": variant_source_metadata(connection),
        }


@router.get("/characters", tags=["dictionary"])
def character_entries(
    char: Annotated[str, Query(min_length=1, max_length=2, description="One character")],
) -> dict:
    validate_character_query(char)
    with get_connection() as connection:
        entries, aliases = entries_for_character(connection, char)
        metadata = source_metadata(connection)
        variant_metadata = variant_source_metadata(connection)
    return {
        "query": char,
        "count": len(entries),
        "resolved_characters": [item["target_character"] for item in aliases],
        "aliases": aliases,
        "entries": entries,
        "data_source": {
            "dictionary": {
                "name": metadata["name"],
                "project_url": metadata["project_url"],
                "commit_sha": metadata["commit_sha"],
                "license": metadata["license"],
            },
            "character_variants": {
                "name": variant_metadata["name"],
                "version": variant_metadata["version"],
                "project_url": variant_metadata["project_url"],
                "license": variant_metadata["license"],
            },
        },
    }


@router.get("/character-candidates", tags=["dictionary"])
def character_candidates(
    char: Annotated[str, Query(min_length=1, max_length=2, description="One character")],
) -> dict:
    validate_character_query(char)
    with get_connection() as connection:
        aliases = character_aliases(connection, char)
    return {
        "query": char,
        "candidates": [
            {"character": char, "relation": "exact"},
            *[
                {
                    "character": item["target_character"],
                    "relation": item["relation"],
                }
                for item in aliases
            ],
        ],
    }


@router.get("/entries/{entry_id}", tags=["dictionary"])
def get_entry(entry_id: Annotated[int, Path(ge=1)]) -> dict:
    with get_connection() as connection:
        entry = entry_by_id(connection, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.get("/small-rhymes/{small_rhyme_id}", tags=["dictionary"])
def get_small_rhyme(small_rhyme_id: Annotated[int, Path(ge=1)]) -> dict:
    with get_connection() as connection:
        small_rhyme = small_rhyme_by_id(connection, small_rhyme_id)
    if small_rhyme is None:
        raise HTTPException(status_code=404, detail="Small rhyme not found")
    return small_rhyme


@router.get("/volumes", tags=["browse"])
def volumes() -> dict:
    with get_connection() as connection:
        items = list_volumes(connection)
    return {"count": len(items), "items": items}


@router.get("/rhymes", tags=["browse"])
def rhymes(volume_id: Annotated[int | None, Query(ge=1)] = None) -> dict:
    with get_connection() as connection:
        items = list_rhymes(connection, volume_id)
    return {"count": len(items), "items": items}


@router.get("/rhymes/{rhyme_id}", tags=["browse"])
def rhyme_detail(rhyme_id: Annotated[int, Path(ge=1)]) -> dict:
    with get_connection() as connection:
        item = rhyme_overview(connection, rhyme_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Rhyme not found")
    return item


@router.get("/overview", tags=["browse"])
def overview() -> dict:
    with get_connection() as connection:
        return overview_summary(connection)


@router.get("/overview/fanqie", tags=["browse"])
def overview_fanqie(
    mode: Annotated[str, Query(pattern="^(core|global)$")] = "core",
) -> dict:
    with get_connection() as connection:
        return fanqie_network(connection, mode)


@router.get("/search/fanqie", tags=["dictionary"])
def fanqie_search(
    q: Annotated[str, Query(min_length=1, max_length=16)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    with get_connection() as connection:
        items = search_fanqie(connection, q, limit)
    return {"query": q, "count": len(items), "items": items}
