from __future__ import annotations

import sqlite3
from pathlib import Path


def test_expected_source_counts(database_file: Path) -> None:
    connection = sqlite3.connect(database_file)
    try:
        assert connection.execute("SELECT COUNT(*) FROM volumes").fetchone()[0] == 5
        assert connection.execute("SELECT COUNT(*) FROM rhymes").fetchone()[0] == 206
        assert connection.execute("SELECT COUNT(*) FROM small_rhymes").fetchone()[0] == 3874
        assert connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 25541
        assert connection.execute("SELECT COUNT(*) FROM character_aliases").fetchone()[0] > 1000
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()


def test_variation_indicator_is_hidden_from_plain_text(database_file: Path) -> None:
    connection = sqlite3.connect(database_file)
    try:
        definition_text, definition_xml = connection.execute(
            "SELECT definition_text, definition_xml FROM entries WHERE character = '東' LIMIT 1"
        ).fetchone()
        assert "〾" not in definition_text
        assert "春方也說文曰" in definition_text
        assert "〾" in definition_xml
    finally:
        connection.close()


def test_simplified_to_traditional_aliases(database_file: Path) -> None:
    connection = sqlite3.connect(database_file)
    try:
        assert connection.execute(
            """
            SELECT target_character
            FROM character_aliases
            WHERE input_character = '东'
            """
        ).fetchall() == [("東",)]
        assert set(
            connection.execute(
                """
                SELECT target_character
                FROM character_aliases
                WHERE input_character = '发'
                """
            ).fetchall()
        ) == {("發",), ("髮",)}
    finally:
        connection.close()


def test_first_small_rhyme_is_east(database_file: Path) -> None:
    connection = sqlite3.connect(database_file)
    try:
        row = connection.execute(
            """
            SELECT sr.head_character, sr.primary_fanqie, r.name, v.title
            FROM small_rhymes sr
            JOIN rhymes r ON r.id = sr.rhyme_id
            JOIN volumes v ON v.id = r.volume_id
            ORDER BY v.sort_order, r.sort_order, sr.sort_order
            LIMIT 1
            """
        ).fetchone()
        assert row == ("東", "德紅切", "東", "廣韻上平聲卷第一")
    finally:
        connection.close()
