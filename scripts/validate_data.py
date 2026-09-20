from __future__ import annotations

import json
import sqlite3

from guangyun.config import DEFAULT_DATABASE_PATH

EXPECTED_COUNTS = {
    "volumes": 5,
    "rhymes": 206,
    "small_rhymes": 3874,
    "entries": 25541,
}


def main() -> None:
    connection = sqlite3.connect(DEFAULT_DATABASE_PATH)
    try:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in EXPECTED_COUNTS
        }
        if counts != EXPECTED_COUNTS:
            raise SystemExit(f"Unexpected counts: {counts}")
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise SystemExit(f"Foreign-key errors: {foreign_key_errors[:5]}")
        sample = connection.execute(
            """
            SELECT e.character, sr.primary_fanqie, r.name, v.title
            FROM entries e
            JOIN small_rhymes sr ON sr.id = e.small_rhyme_id
            JOIN rhymes r ON r.id = sr.rhyme_id
            JOIN volumes v ON v.id = r.volume_id
            WHERE e.character = '東'
            ORDER BY v.sort_order, r.sort_order, sr.sort_order
            LIMIT 1
            """
        ).fetchone()
        if sample != ("東", "德紅切", "東", "廣韻上平聲卷第一"):
            raise SystemExit(f"Unexpected 東 record: {sample}")
        aliases = connection.execute(
            """
            SELECT target_character
            FROM character_aliases
            WHERE input_character = '东'
            ORDER BY target_character
            """
        ).fetchall()
        if aliases != [("東",)]:
            raise SystemExit(f"Unexpected 东 aliases: {aliases}")
        counts["character_aliases"] = connection.execute(
            "SELECT COUNT(*) FROM character_aliases"
        ).fetchone()[0]
        print(json.dumps(counts, ensure_ascii=False, indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
