from __future__ import annotations

import sqlite3
from collections import Counter
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

TONE_CORRESPONDENCE_INDEXES = (
    (1, 1, 1, 1),
    (2, None, 2, 2),
    (3, 2, 3, 3),
    (4, 3, 4, 4),
    (5, 4, 5, None),
    (6, 5, 6, None),
    (7, 6, 7, None),
    (8, 7, 8, None),
    (9, 8, 9, None),
    (10, 9, 10, None),
    (11, 10, 11, None),
    (12, 11, 12, None),
    (None, None, 13, None),
    (None, None, 14, None),
    (13, 12, 15, None),
    (14, 13, 16, None),
    (None, None, 17, None),
    (15, 14, 18, None),
    (16, 15, 19, None),
    (None, None, 20, None),
    (17, 16, 21, 5),
    (18, 17, 22, 6),
    (19, None, None, 7),
    (20, 18, 23, 8),
    (21, 19, 24, 9),
    (22, 20, 25, 10),
    (23, 21, 26, 11),
    (24, 22, 27, None),
    (25, 23, 28, 12),
    (26, 24, 29, 13),
    (27, 25, 30, 15),
    (28, 26, 31, 14),
    (29, 27, 32, 16),
    (30, 28, 33, 17),
    (31, 29, 34, None),
    (32, 30, 35, None),
    (33, 31, 36, None),
    (34, 32, 37, None),
    (35, 33, 38, None),
    (36, 34, 39, None),
    (37, 35, 40, None),
    (38, 36, 41, 18),
    (39, 37, 42, 19),
    (40, 38, 43, 20),
    (41, 39, 44, 21),
    (42, 40, 45, 22),
    (43, 41, 46, 23),
    (44, 42, 47, 24),
    (45, 43, 48, 25),
    (46, 44, 49, None),
    (47, 45, 50, None),
    (48, 46, 51, None),
    (49, 47, 52, 26),
    (50, 48, 53, 27),
    (51, 49, 54, 28),
    (52, 50, 55, 29),
    (53, 51, 56, 30),
    (54, 53, 58, 31),
    (55, 54, 59, 32),
    (56, 52, 57, 33),
    (57, 55, 60, 34),
)


def _fanqie_pair(value: str) -> tuple[str, str] | None:
    characters = [character for character in value if character != "切"]
    if len(characters) < 2:
        return None
    return characters[0], characters[1]


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
        SELECT r.*, r.sort_order AS "order", v.title AS volume_title, v.tone,
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


def tone_correspondence(
    connection: sqlite3.Connection, rhymes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_tone = {
        tone: [rhyme for rhyme in rhymes if rhyme["tone"] == tone]
        for tone in ("平", "上", "去", "入")
    }

    def rhyme_at(tone: str, index: int | None) -> dict[str, Any] | None:
        if index is None:
            return None
        rhyme = by_tone[tone][index - 1]
        return {
            "id": rhyme["id"],
            "name": rhyme["name"],
            "volume_title": rhyme["volume_title"],
            "small_rhyme_count": rhyme["small_rhyme_count"],
            "entry_count": rhyme["entry_count"],
        }

    merged_rows = connection.execute(
        """
        SELECT sr.id AS small_rhyme_id, sr.head_character,
               r.id AS rhyme_id, r.name AS rhyme_name, v.tone
        FROM small_rhymes sr
        JOIN rhymes r ON r.id = sr.rhyme_id
        JOIN volumes v ON v.id = r.volume_id
        WHERE (sr.head_character = '湩' AND v.tone = '上')
           OR sr.head_character IN ('𧤛', '櫬', '麧')
        """
    ).fetchall()
    merged_by_character = {
        row["head_character"]: {
            "small_rhyme_id": row["small_rhyme_id"],
            "head_character": row["head_character"],
            "rhyme_id": row["rhyme_id"],
            "rhyme_name": row["rhyme_name"],
        }
        for row in merged_rows
    }
    merged_cells = {
        (2, "rising"): merged_by_character["湩"],
        (23, "rising"): merged_by_character["𧤛"],
        (23, "departing"): merged_by_character["櫬"],
        (28, "entering"): merged_by_character["麧"],
    }

    rows = []
    columns = ("level", "rising", "departing", "entering")
    tones = ("平", "上", "去", "入")
    for row_number, indexes in enumerate(TONE_CORRESPONDENCE_INDEXES, start=1):
        row = {
            column: rhyme_at(tone, index)
            for column, tone, index in zip(columns, tones, indexes, strict=True)
        }
        for column in columns:
            merged = merged_cells.get((row_number, column))
            if merged is not None:
                row[column] = {"merged": merged}
        row["kind"] = (
            "departing-only"
            if row["level"] is None
            and row["rising"] is None
            and row["departing"] is not None
            and row["entering"] is None
            else "correspondence"
        )
        rows.append(row)
    return rows


def overview_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    volumes = [
        dict(row)
        for row in connection.execute(
            """
            SELECT v.id, v.source_xml_id AS source_id, v.title, v.tone,
                   v.sort_order AS "order",
                   COUNT(DISTINCT r.id) AS rhyme_count,
                   COUNT(DISTINCT sr.id) AS small_rhyme_count,
                   COUNT(DISTINCT e.id) AS entry_count
            FROM volumes v
            LEFT JOIN rhymes r ON r.volume_id = v.id
            LEFT JOIN small_rhymes sr ON sr.rhyme_id = r.id
            LEFT JOIN entries e ON e.small_rhyme_id = sr.id
            GROUP BY v.id
            ORDER BY v.sort_order
            """
        ).fetchall()
    ]
    rhymes = list_rhymes(connection)
    totals = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM volumes) AS volumes,
            (SELECT COUNT(*) FROM rhymes) AS rhymes,
            (SELECT COUNT(*) FROM small_rhymes) AS small_rhymes,
            (SELECT COUNT(*) FROM entries) AS entries
        """
    ).fetchone()
    profile = connection.execute(
        """
        SELECT
            SUM(is_added) AS added_entries,
            SUM(original_character IS NOT NULL) AS corrected_headwords,
            SUM(INSTR(definition_xml, '〾') > 0) AS glyph_variant_entries,
            SUM(INSTR(definition_text, '？') > 0) AS unresolved_definition_entries
        FROM entries
        """
    ).fetchone()
    characters = connection.execute("SELECT character FROM entries").fetchall()
    ids_headwords = sum(
        any(0x2FF0 <= ord(character) <= 0x2FFF for character in row["character"])
        for row in characters
    )
    supplementary_headwords = sum(
        any(ord(character) > 0xFFFF for character in row["character"]) for row in characters
    )
    private_use_headwords = sum(
        any(
            0xE000 <= ord(character) <= 0xF8FF
            or 0xF0000 <= ord(character) <= 0xFFFFD
            or 0x100000 <= ord(character) <= 0x10FFFD
            for character in row["character"]
        )
        for row in characters
    )
    largest_small_rhymes = [
        dict(row)
        for row in connection.execute(
            """
            SELECT sr.id, sr.head_character, sr.primary_fanqie,
                   r.id AS rhyme_id, r.name AS rhyme_name,
                   v.tone, COUNT(e.id) AS entry_count
            FROM small_rhymes sr
            JOIN rhymes r ON r.id = sr.rhyme_id
            JOIN volumes v ON v.id = r.volume_id
            JOIN entries e ON e.small_rhyme_id = sr.id
            GROUP BY sr.id
            ORDER BY entry_count DESC, v.sort_order, r.sort_order, sr.sort_order
            LIMIT 10
            """
        ).fetchall()
    ]
    fanqies = connection.execute(
        "SELECT primary_fanqie FROM small_rhymes ORDER BY id"
    ).fetchall()
    upper_counts: Counter[str] = Counter()
    lower_counts: Counter[str] = Counter()
    for row in fanqies:
        pair = _fanqie_pair(row["primary_fanqie"])
        if pair is not None:
            upper, lower = pair
            upper_counts[upper] += 1
            lower_counts[lower] += 1

    return {
        "totals": dict(totals),
        "volumes": volumes,
        "rhymes": rhymes,
        "tone_correspondence": tone_correspondence(connection, rhymes),
        "profile": {
            **dict(profile),
            "ids_headwords": ids_headwords,
            "supplementary_headwords": supplementary_headwords,
            "private_use_headwords": private_use_headwords,
            "average_small_rhymes_per_rhyme": round(
                totals["small_rhymes"] / totals["rhymes"], 1
            ),
            "average_entries_per_small_rhyme": round(
                totals["entries"] / totals["small_rhymes"], 1
            ),
        },
        "largest_rhymes": sorted(
            rhymes,
            key=lambda rhyme: (-rhyme["entry_count"], rhyme["order"]),
        )[:10],
        "largest_small_rhymes": largest_small_rhymes,
        "top_fanqie_upper": [
            {"character": character, "count": count}
            for character, count in upper_counts.most_common(12)
        ],
        "top_fanqie_lower": [
            {"character": character, "count": count}
            for character, count in lower_counts.most_common(12)
        ],
    }


def rhyme_overview(connection: sqlite3.Connection, rhyme_id: int) -> dict[str, Any] | None:
    rhyme = connection.execute(
        """
        SELECT r.id, r.source_xml_id AS source_id, r.name, r.rhyme_number,
               r.catalog_fanqie, r.catalog_note, r.sort_order AS "order",
               v.id AS volume_id, v.title AS volume_title, v.tone,
               v.sort_order AS volume_order
        FROM rhymes r
        JOIN volumes v ON v.id = r.volume_id
        WHERE r.id = ?
        """,
        (rhyme_id,),
    ).fetchone()
    if rhyme is None:
        return None
    small_rhymes = [
        dict(row)
        for row in connection.execute(
            """
            SELECT sr.id, sr.source_xml_id AS source_id, sr.head_character,
                   sr.primary_fanqie, sr.ipa, sr.onyomi, sr.homophone_count,
                   sr.sort_order AS "order", COUNT(e.id) AS entry_count
            FROM small_rhymes sr
            LEFT JOIN entries e ON e.small_rhyme_id = sr.id
            WHERE sr.rhyme_id = ?
            GROUP BY sr.id
            ORDER BY sr.sort_order
            """,
            (rhyme_id,),
        ).fetchall()
    ]
    return {
        **dict(rhyme),
        "small_rhyme_count": len(small_rhymes),
        "entry_count": sum(item["entry_count"] for item in small_rhymes),
        "small_rhymes": small_rhymes,
    }


def fanqie_network(connection: sqlite3.Connection, mode: str) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT sr.id, sr.head_character, sr.primary_fanqie,
               r.name AS rhyme_name, COUNT(e.id) AS entry_count
        FROM small_rhymes sr
        JOIN rhymes r ON r.id = sr.rhyme_id
        LEFT JOIN entries e ON e.small_rhyme_id = sr.id
        GROUP BY sr.id
        ORDER BY sr.id
        """
    ).fetchall()
    edge_groups: dict[tuple[str, str], dict[str, Any]] = {}
    upper_counts: Counter[str] = Counter()
    lower_counts: Counter[str] = Counter()
    for row in rows:
        pair = _fanqie_pair(row["primary_fanqie"])
        if pair is None:
            continue
        upper, lower = pair
        upper_counts[upper] += 1
        lower_counts[lower] += 1
        key = (upper, lower)
        group = edge_groups.setdefault(
            key,
            {
                "source": upper,
                "target": lower,
                "count": 0,
                "small_rhymes": [],
            },
        )
        group["count"] += 1
        if len(group["small_rhymes"]) < 8:
            group["small_rhymes"].append(
                {
                    "id": row["id"],
                    "head_character": row["head_character"],
                    "rhyme_name": row["rhyme_name"],
                    "entry_count": row["entry_count"],
                }
            )

    all_characters = set(upper_counts) | set(lower_counts)
    ranked_characters = sorted(
        all_characters,
        key=lambda character: (
            -(upper_counts[character] + lower_counts[character]),
            character,
        ),
    )
    included = set(ranked_characters[:48]) if mode == "core" else all_characters
    edges = [
        edge
        for edge in edge_groups.values()
        if edge["source"] in included and edge["target"] in included
    ]
    connected = {edge["source"] for edge in edges} | {edge["target"] for edge in edges}
    nodes = [
        {
            "id": character,
            "upper_count": upper_counts[character],
            "lower_count": lower_counts[character],
            "count": upper_counts[character] + lower_counts[character],
        }
        for character in ranked_characters
        if character in connected
    ]
    return {
        "mode": mode,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": sorted(
            edges,
            key=lambda edge: (-edge["count"], edge["source"], edge["target"]),
        ),
    }


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
