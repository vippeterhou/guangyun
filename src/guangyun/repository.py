from __future__ import annotations

import sqlite3
from typing import Any

ENTRY_SELECT = """
SELECT
    e.id,
    e.source_xml_id,
    e.character,
    e.original_character,
    e.definition_text,
    e.definition_xml,
    e.is_added,
    e.sort_order AS entry_order,
    sr.id AS small_rhyme_id,
    sr.source_xml_id AS small_rhyme_source_id,
    sr.head_character,
    sr.primary_fanqie,
    sr.ipa,
    sr.onyomi,
    sr.homophone_count,
    sr.sort_order AS small_rhyme_order,
    r.id AS rhyme_id,
    r.source_xml_id AS rhyme_source_id,
    r.name AS rhyme_name,
    r.rhyme_number,
    r.catalog_fanqie,
    r.catalog_note,
    r.sort_order AS rhyme_order,
    v.id AS volume_id,
    v.source_xml_id AS volume_source_id,
    v.title AS volume_title,
    v.tone,
    v.sort_order AS volume_order
FROM entries e
JOIN small_rhymes sr ON sr.id = e.small_rhyme_id
JOIN rhymes r ON r.id = sr.rhyme_id
JOIN volumes v ON v.id = r.volume_id
"""


def source_metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM source_metadata WHERE id = 1").fetchone()
    return dict(row)


def variant_source_metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM variant_source_metadata WHERE id = 1").fetchone()
    return dict(row)


def _fanqies(connection: sqlite3.Connection, entry_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT text, role, sort_order
        FROM fanqies
        WHERE entry_id = ?
        ORDER BY sort_order
        """,
        (entry_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def serialize_entry(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source_id": row["source_xml_id"],
        "character": row["character"],
        "original_character": row["original_character"],
        "definition": row["definition_text"],
        "is_added": bool(row["is_added"]),
        "entry_order": row["entry_order"],
        "fanqies": _fanqies(connection, row["id"]),
        "small_rhyme": {
            "id": row["small_rhyme_id"],
            "source_id": row["small_rhyme_source_id"],
            "head_character": row["head_character"],
            "fanqie": row["primary_fanqie"],
            "ipa": row["ipa"],
            "onyomi": row["onyomi"],
            "homophone_count": row["homophone_count"],
            "order": row["small_rhyme_order"],
        },
        "rhyme": {
            "id": row["rhyme_id"],
            "source_id": row["rhyme_source_id"],
            "name": row["rhyme_name"],
            "number": row["rhyme_number"],
            "catalog_fanqie": row["catalog_fanqie"],
            "catalog_note": row["catalog_note"],
            "order": row["rhyme_order"],
        },
        "volume": {
            "id": row["volume_id"],
            "source_id": row["volume_source_id"],
            "title": row["volume_title"],
            "tone": row["tone"],
            "order": row["volume_order"],
        },
    }


def character_aliases(connection: sqlite3.Connection, character: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT input_character, target_character, relation
        FROM character_aliases
        WHERE input_character = ?
        ORDER BY target_character
        """,
        (character,),
    ).fetchall()
    return [dict(row) for row in rows]


def entries_for_character(
    connection: sqlite3.Connection, character: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    aliases = character_aliases(connection, character)
    candidates = list(dict.fromkeys([character, *(item["target_character"] for item in aliases)]))
    placeholders = ", ".join("?" for _ in candidates)
    rows = connection.execute(
        ENTRY_SELECT
        + f"""
        WHERE e.character IN ({placeholders}) OR e.original_character IN ({placeholders})
        ORDER BY v.sort_order, r.sort_order, sr.sort_order, e.sort_order
        """,
        (*candidates, *candidates),
    ).fetchall()
    alias_targets = {item["target_character"]: item for item in aliases}
    entries = []
    for row in rows:
        entry = serialize_entry(connection, row)
        matched_character = (
            row["character"] if row["character"] in alias_targets else row["original_character"]
        )
        entry["matched_via"] = alias_targets.get(matched_character)
        entries.append(entry)
    return entries, aliases


def entry_by_id(connection: sqlite3.Connection, entry_id: int) -> dict[str, Any] | None:
    row = connection.execute(ENTRY_SELECT + " WHERE e.id = ?", (entry_id,)).fetchone()
    return serialize_entry(connection, row) if row else None


def small_rhyme_by_id(connection: sqlite3.Connection, small_rhyme_id: int) -> dict[str, Any] | None:
    rows = connection.execute(
        ENTRY_SELECT
        + """
        WHERE sr.id = ?
        ORDER BY e.sort_order
        """,
        (small_rhyme_id,),
    ).fetchall()
    if not rows:
        return None
    first = serialize_entry(connection, rows[0])
    return {
        **first["small_rhyme"],
        "rhyme": first["rhyme"],
        "volume": first["volume"],
        "entries": [serialize_entry(connection, row) for row in rows],
    }


def list_volumes(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT v.*, COUNT(DISTINCT r.id) AS rhyme_count,
               COUNT(DISTINCT sr.id) AS small_rhyme_count
        FROM volumes v
        LEFT JOIN rhymes r ON r.volume_id = v.id
        LEFT JOIN small_rhymes sr ON sr.rhyme_id = r.id
        GROUP BY v.id
        ORDER BY v.sort_order
        """
    ).fetchall()
    return [dict(row) for row in rows]


def list_rhymes(
    connection: sqlite3.Connection, volume_id: int | None = None
) -> list[dict[str, Any]]:
    parameters: tuple[Any, ...] = ()
    where = ""
    if volume_id is not None:
        where = "WHERE r.volume_id = ?"
        parameters = (volume_id,)
    rows = connection.execute(
        f"""
        SELECT r.*, v.title AS volume_title, v.tone,
               COUNT(DISTINCT sr.id) AS small_rhyme_count,
               COUNT(DISTINCT e.id) AS entry_count
        FROM rhymes r
        JOIN volumes v ON v.id = r.volume_id
        LEFT JOIN small_rhymes sr ON sr.rhyme_id = r.id
        LEFT JOIN entries e ON e.small_rhyme_id = sr.id
        {where}
        GROUP BY r.id
        ORDER BY v.sort_order, r.sort_order
        """,
        parameters,
    ).fetchall()
    return [dict(row) for row in rows]


def search_fanqie(connection: sqlite3.Connection, query: str, limit: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        ENTRY_SELECT
        + """
        WHERE sr.primary_fanqie LIKE ? OR EXISTS (
            SELECT 1 FROM fanqies f WHERE f.entry_id = e.id AND f.text LIKE ?
        )
        ORDER BY v.sort_order, r.sort_order, sr.sort_order, e.sort_order
        LIMIT ?
        """,
        (f"%{query}%", f"%{query}%", limit),
    ).fetchall()
    return [serialize_entry(connection, row) for row in rows]
