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


def test_missing_catalog_rhyme_names_are_corrected(database_file: Path) -> None:
    connection = sqlite3.connect(database_file)
    try:
        rows = connection.execute(
            """
            SELECT source_xml_id, name
            FROM rhymes
            WHERE source_xml_id IN ('q05', 'r12', 'r29')
            ORDER BY source_xml_id
            """
        ).fetchall()
        assert rows == [("q05", "寘"), ("r12", "曷"), ("r29", "葉")]
        assert connection.execute(
            "SELECT COUNT(*) FROM rhymes WHERE name = '？'"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_ids_characters_are_normalized(database_file: Path) -> None:
    corrections = {
        "⿰⿱爻火攵": "𢽻",
        "⿰⿱罒⿸厂畏頁": "𩕾",
        "⿰⿸厂己頁": "頋",
        "⿰丩周": "𰀧",
        "⿰市犬": "𢂤",
        "⿰帝巴": "𢑦",
        "⿰朿攴": "㩽",
        "⿰氵⿱一㜽": "涇",
        "⿰氵𤎭": "𤃨",
        "⿰祟蚤": "𧎹",
        "⿰臼宂": "𦥨",
        "⿰舂弋": "㦼",
        "⿰舟灷": "𦩗",
        "⿰言𠂷": "䛭",
        "⿰𦊆刂": "㓻",
        "⿰革朿": "𩊯",
        "⿰鳥𠂜": "𩾳",
        "⿰黍易": "䵘",
        "⿱⿰知于日": "𣉻",
        "⿱䒱豆": "𧯷",
        "⿱丿𠔿": "𡦼",
        "⿱卲糸": "綤",
        "⿱冂父": "𣅝",
        "⿱日黽": "𪓙",
        "⿱士軍": "𨌗",
        "⿱艹尐": "𢘿",
        "⿱雨⿺辶田": "䢮",
        "⿱食芖": "𩛛",
        "⿱髟⿹戈隹": "𩯰",
        "⿱鼓釜": "䥢",
        "⿱𦫶廾": "𦭺",
        "⿲王目义": "瑖",
        "⿳亠圍乂": "𠆎",
        "⿳日八寸": "䙷",
        "⿳栒一八": "𣕍",
        "⿹𠄎夕": "夃",
    }
    connection = sqlite3.connect(database_file)
    try:
        for source, target in corrections.items():
            assert connection.execute(
                "SELECT COUNT(*) FROM entries WHERE character = ?",
                (source,),
            ).fetchone()[0] == 0
            assert connection.execute(
                "SELECT COUNT(*) FROM entries WHERE character = ?",
                (target,),
            ).fetchone()[0] > 0

        rows = connection.execute(
            """
            SELECT character, original_character, definition_text
            FROM entries
            WHERE character = '𪓙'
            ORDER BY id
            """
        ).fetchall()
        assert [(row[0], row[1]) for row in rows] == [
            ("𪓙", "⿱日黽"),
            ("𪓙", "⿱日黽"),
        ]
        assert all("⿱日黽" not in row[2] for row in rows)
        assert "史𪓙之後漢有𪓙錯" in rows[1][2]
        remaining_ids = {
            row[0]
            for row in connection.execute(
                """
                SELECT DISTINCT character
                FROM entries
                WHERE character GLOB '*[⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻]*'
                """
            )
        }
        assert remaining_ids == {"⿻𥈸一", "⿱⿰来攵正", "⿰隺犬", "⿱芖雨"}
    finally:
        connection.close()
