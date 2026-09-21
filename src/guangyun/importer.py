from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from guangyun.config import (
    DEFAULT_DATABASE_PATH,
    DEFAULT_SOURCE_PATH,
    DEFAULT_SOURCES_PATH,
    DEFAULT_VARIANT_SOURCE_PATH,
)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE source_metadata (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    project_url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    license TEXT NOT NULL,
    book_title TEXT NOT NULL
);

CREATE TABLE variant_source_metadata (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    project_url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    license TEXT NOT NULL,
    license_url TEXT NOT NULL
);

CREATE TABLE volumes (
    id INTEGER PRIMARY KEY,
    source_xml_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    tone TEXT NOT NULL,
    sort_order INTEGER NOT NULL UNIQUE
);

CREATE TABLE rhymes (
    id INTEGER PRIMARY KEY,
    volume_id INTEGER NOT NULL REFERENCES volumes(id),
    source_xml_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    rhyme_number TEXT NOT NULL,
    catalog_fanqie TEXT,
    catalog_note TEXT,
    sort_order INTEGER NOT NULL,
    UNIQUE (volume_id, sort_order)
);

CREATE TABLE small_rhymes (
    id INTEGER PRIMARY KEY,
    rhyme_id INTEGER NOT NULL REFERENCES rhymes(id),
    source_xml_id TEXT,
    head_character TEXT NOT NULL,
    primary_fanqie TEXT NOT NULL,
    ipa TEXT,
    onyomi TEXT,
    homophone_count INTEGER,
    sort_order INTEGER NOT NULL,
    UNIQUE (rhyme_id, sort_order)
);

CREATE TABLE entries (
    id INTEGER PRIMARY KEY,
    small_rhyme_id INTEGER NOT NULL REFERENCES small_rhymes(id),
    source_xml_id TEXT,
    character TEXT NOT NULL,
    original_character TEXT,
    definition_text TEXT NOT NULL,
    definition_xml TEXT NOT NULL,
    is_added INTEGER NOT NULL CHECK (is_added IN (0, 1)),
    sort_order INTEGER NOT NULL,
    UNIQUE (small_rhyme_id, sort_order)
);

CREATE TABLE fanqies (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    text TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('primary', 'alternate')),
    sort_order INTEGER NOT NULL,
    UNIQUE (entry_id, sort_order)
);

CREATE TABLE character_aliases (
    id INTEGER PRIMARY KEY,
    input_character TEXT NOT NULL,
    target_character TEXT NOT NULL,
    relation TEXT NOT NULL CHECK (relation = 'simplified-to-traditional'),
    UNIQUE (input_character, target_character)
);

CREATE INDEX idx_entries_character ON entries(character);
CREATE INDEX idx_entries_original_character ON entries(original_character);
CREATE INDEX idx_small_rhymes_head_character ON small_rhymes(head_character);
CREATE INDEX idx_small_rhymes_primary_fanqie ON small_rhymes(primary_fanqie);
CREATE INDEX idx_fanqies_text ON fanqies(text);
CREATE INDEX idx_rhymes_name ON rhymes(name);
CREATE INDEX idx_character_aliases_input ON character_aliases(input_character);
"""

CHINESE_ORDINAL = re.compile(r"第[一二三四五六七八九十百]+$")
COUNT_SUFFIX = re.compile(r"([一二三四五六七八九十百廿卅]+)$")
EDITORIAL_MARKS = "〾"
UNIHAN_CODEPOINT = re.compile(r"U\+([0-9A-F]{4,6})")
RHYME_NAME_CORRECTIONS = {
    "q05": "寘",
    "r12": "曷",
    "r29": "葉",
}
CHARACTER_CORRECTIONS = {
    "⿰⿱爻火攵": "𢽻",  # 卷三・巧韻・絞小韻
    "⿰⿱罒⿸厂畏頁": "𩕾",  # 卷四・願韻・願小韻
    "⿰⿸厂己頁": "頋",  # 卷四・暮韻・顧小韻
    "⿰丩周": "𰀧",  # 卷二・尤韻・𠁫小韻
    "⿰市犬": "𢂤",  # 卷四・隊韻・佩小韻
    "⿰帝巴": "𢑦",  # 卷二・宵韻・韶小韻
    "⿰朿攴": "㩽",  # 卷一・支韻・竒小韻
    "⿰氵⿱一㜽": "涇",  # 卷三・靜韻・痙小韻
    "⿰氵𤎭": "𤃨",  # 卷四・勘韻・顲小韻
    "⿰祟蚤": "𧎹",  # 卷四・泰韻・最小韻
    "⿰臼宂": "𦥨",  # 卷三・小韻・鷕小韻
    "⿰舂弋": "㦼",  # 卷四・絳韻・淙小韻
    "⿰舟灷": "𦩗",  # 卷三・寢韻・朕小韻
    "⿰言𠂷": "䛭",  # 卷四・映韻・䛭小韻
    "⿰𦊆刂": "㓻",  # 卷二・唐韻・岡小韻
    "⿰革朿": "𩊯",  # 卷五・麥韻・栜小韻
    "⿰鳥𠂜": "𩾳",  # 卷五・緝韻・急/𩾳小韻；卷五・葉韻・衱小韻
    "⿰黍易": "䵘",  # 卷四・卦韻・曬小韻
    "⿱⿰知于日": "𣉻",  # 卷四・寘韻・智小韻
    "⿱䒱豆": "𧯷",  # 卷三・隱韻・謹小韻
    "⿱丿𠔿": "𡦼",  # 卷三・腫韻・宂小韻
    "⿱卲糸": "綤",  # 卷三・小韻・紹小韻
    "⿱冂父": "𣅝",  # 卷五・沒韻・𣅝小韻
    "⿱日黽": "𪓙",  # 卷二・宵韻・朝/𪓙小韻
    "⿱士軍": "𨌗",  # 卷四・至韻・喟小韻
    "⿱艹尐": "𢘿",  # 卷二・戈韻・莎小韻
    "⿱雨⿺辶田": "䢮",  # 卷五・錫韻・荻小韻
    "⿱食芖": "𩛛",  # 卷一・之韻・飴小韻
    "⿱髟⿹戈隹": "𩯰",  # 卷四・祭韻・祭小韻
    "⿱鼓釜": "䥢",  # 卷一・冬韻・䃧小韻
    "⿱𦫶廾": "𦭺",  # 卷二・幽韻・樛小韻
    "⿲王目义": "瑖",  # 卷四・換韻・鍛小韻
    "⿳亠圍乂": "𠆎",  # 卷一・微韻・幃小韻
    "⿳日八寸": "䙷",  # 卷四・代韻・礙小韻
    "⿳栒一八": "𣕍",  # 卷三・準韻・筍小韻
    "⿹𠄎夕": "夃",  # 卷一・模韻・孤小韻；卷三・姥韻・古小韻
}


@dataclass(frozen=True)
class EntryForm:
    character: str
    original_character: str | None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unihan_character(value: str) -> str:
    match = UNIHAN_CODEPOINT.fullmatch(value)
    if match is None:
        raise ValueError(f"Invalid Unihan code point: {value}")
    return chr(int(match.group(1), 16))


def variant_aliases(path: Path) -> set[tuple[str, str]]:
    aliases: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            subject_value, property_name, target_values = line.split("\t")
            if property_name not in {"kTraditionalVariant", "kSimplifiedVariant"}:
                continue
            subject = unihan_character(subject_value)
            targets = [
                chr(int(codepoint, 16)) for codepoint in UNIHAN_CODEPOINT.findall(target_values)
            ]
            if property_name == "kTraditionalVariant":
                pairs = ((subject, target) for target in targets)
            else:
                pairs = ((target, subject) for target in targets)
            aliases.update(
                (input_character, target_character)
                for input_character, target_character in pairs
                if input_character != target_character
            )
    return aliases


def clean_text(value: str | None) -> str:
    return "".join((value or "").split())


def normalized_character(value: str) -> str:
    normalized = clean_text(value).lstrip(EDITORIAL_MARKS)
    return CHARACTER_CORRECTIONS.get(normalized, normalized)


def corrected_characters(value: str) -> str:
    for source, target in CHARACTER_CORRECTIONS.items():
        value = value.replace(source, target)
    return value


def direct_text(node: ET.Element) -> str:
    return clean_text(node.text).lstrip(EDITORIAL_MARKS)


def corrected_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    parts: list[str] = []
    if node.text:
        parts.append(node.text)
    for child in node:
        if child.tag == "original_text":
            rewrite = child.find("rewrite_text")
            if rewrite is not None:
                parts.append(corrected_text(rewrite))
                if rewrite.tail:
                    parts.append(rewrite.tail)
            else:
                parts.append(corrected_text(child))
        elif child.tag in {"rewrite_text", "check_note"} and node.tag == "original_text":
            pass
        else:
            parts.append(corrected_text(child))
        if child.tail:
            parts.append(child.tail)
    return corrected_characters(
        clean_text("".join(parts)).replace(EDITORIAL_MARKS, "")
    )


def entry_form(node: ET.Element) -> EntryForm:
    original_word = node.find("original_word")
    if original_word is None:
        original = direct_text(node)
        character = normalized_character(original)
        return EntryForm(
            character=character,
            original_character=original if original and original != character else None,
        )

    original = direct_text(original_word)
    rewrite = original_word.find("rewrite_word")
    character = (
        normalized_character(corrected_text(rewrite))
        if rewrite is not None
        else normalized_character(original)
    )
    return EntryForm(
        character=character,
        original_character=original if original and original != character else None,
    )


def rhyme_catalog(volume: ET.Element) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    catalog = volume.find("catalog")
    if catalog is None:
        return rows
    for item in catalog.findall("rhythmic_entry"):
        fanqie = item.find("fanqie")
        label = clean_text(fanqie.tail if fanqie is not None else item.text)
        name = CHINESE_ORDINAL.sub("", label)
        note = item.find("note")
        rows.append(
            {
                "name": name,
                "fanqie": corrected_text(fanqie) or None,
                "note": corrected_text(note) or None,
            }
        )
    return rows


def volume_tone(volume_id: str) -> str:
    return {
        "v1": "平",
        "v2": "平",
        "v3": "上",
        "v4": "去",
        "v5": "入",
    }[volume_id]


def extract_homophone_count(note_text: str) -> int | None:
    match = COUNT_SUFFIX.search(note_text)
    if not match:
        return None
    values = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
        "十一": 11,
        "十二": 12,
        "十三": 13,
        "十四": 14,
        "十五": 15,
        "十六": 16,
        "十七": 17,
        "十八": 18,
        "十九": 19,
        "二十": 20,
        "廿": 20,
        "三十": 30,
        "卅": 30,
    }
    return values.get(match.group(1))


def create_database(
    source_path: Path = DEFAULT_SOURCE_PATH,
    target_path: Path = DEFAULT_DATABASE_PATH,
    sources_path: Path = DEFAULT_SOURCES_PATH,
    variant_source_path: Path = DEFAULT_VARIANT_SOURCE_PATH,
) -> dict[str, int]:
    manifest = json.loads(sources_path.read_text(encoding="utf-8"))
    metadata = manifest["sources"]["guangyun"]
    variant_metadata = manifest["sources"]["unihan_variants"]
    actual_sha256 = sha256(source_path)
    if actual_sha256 != metadata["sha256"]:
        raise ValueError(
            f"Source SHA-256 mismatch: expected {metadata['sha256']}, got {actual_sha256}"
        )
    actual_variant_sha256 = sha256(variant_source_path)
    if actual_variant_sha256 != variant_metadata["sha256"]:
        raise ValueError(
            "Variant source SHA-256 mismatch: "
            f"expected {variant_metadata['sha256']}, got {actual_variant_sha256}"
        )

    root = ET.parse(source_path).getroot()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_suffix(target_path.suffix + ".tmp")
    temporary_path.unlink(missing_ok=True)

    connection = sqlite3.connect(temporary_path)
    connection.execute("PRAGMA foreign_keys = ON")
    counts = {
        "volumes": 0,
        "rhymes": 0,
        "small_rhymes": 0,
        "entries": 0,
        "fanqies": 0,
        "character_aliases": 0,
    }

    try:
        connection.executescript(SCHEMA)
        connection.execute(
            """
            INSERT INTO source_metadata
                (id, name, project_url, source_url, commit_sha, sha256, license, book_title)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metadata["name"],
                metadata["project_url"],
                metadata["source_url"],
                metadata["version"],
                actual_sha256,
                metadata["license"],
                root.attrib["title"],
            ),
        )
        connection.execute(
            """
            INSERT INTO variant_source_metadata
                (id, name, version, project_url, source_url, sha256, license, license_url)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                variant_metadata["name"],
                variant_metadata["version"],
                variant_metadata["project_url"],
                variant_metadata["source_url"],
                actual_variant_sha256,
                variant_metadata["license"],
                variant_metadata["license_url"],
            ),
        )

        aliases = sorted(variant_aliases(variant_source_path))
        connection.executemany(
            """
            INSERT INTO character_aliases
                (input_character, target_character, relation)
            VALUES (?, ?, 'simplified-to-traditional')
            """,
            aliases,
        )
        counts["character_aliases"] = len(aliases)

        rhyme_global_order = 0
        for volume_order, volume in enumerate(root.findall("volume"), start=1):
            volume_xml_id = volume.attrib["id"]
            cursor = connection.execute(
                """
                INSERT INTO volumes (source_xml_id, title, tone, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (
                    volume_xml_id,
                    clean_text(volume.findtext("volume_title")),
                    volume_tone(volume_xml_id),
                    volume_order,
                ),
            )
            volume_id = cursor.lastrowid
            counts["volumes"] += 1

            catalog = rhyme_catalog(volume)
            rhymes = volume.findall("rhyme")
            if len(catalog) != len(rhymes):
                raise ValueError(
                    f"Catalog/rhyme count mismatch in {volume_xml_id}: "
                    f"{len(catalog)} != {len(rhymes)}"
                )

            for rhyme_order, (rhyme, catalog_row) in enumerate(
                zip(rhymes, catalog, strict=True), start=1
            ):
                rhyme_global_order += 1
                rhyme_source_id = rhyme.attrib["id"]
                cursor = connection.execute(
                    """
                    INSERT INTO rhymes
                        (volume_id, source_xml_id, name, rhyme_number, catalog_fanqie,
                         catalog_note, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        volume_id,
                        rhyme_source_id,
                        RHYME_NAME_CORRECTIONS.get(rhyme_source_id, catalog_row["name"]),
                        clean_text(rhyme.findtext("rhyme_num")),
                        catalog_row["fanqie"],
                        catalog_row["note"],
                        rhyme_order,
                    ),
                )
                rhyme_id = cursor.lastrowid
                counts["rhymes"] += 1

                for small_rhyme_order, voice_part in enumerate(
                    rhyme.findall("voice_part"), start=1
                ):
                    entry_nodes = [
                        child for child in voice_part if child.tag in {"word_head", "added_word"}
                    ]
                    if not entry_nodes or entry_nodes[0].tag != "word_head":
                        raise ValueError(f"Small rhyme without a word-head in {rhyme.attrib['id']}")

                    head_form = entry_form(entry_nodes[0])
                    head_note = entry_nodes[0].find("note")
                    primary_fanqie_node = (
                        head_note.find(".//fanqie") if head_note is not None else None
                    )
                    if primary_fanqie_node is None:
                        raise ValueError(f"Small rhyme {head_form.character} has no primary fanqie")
                    primary_fanqie = corrected_text(primary_fanqie_node)
                    head_note_text = corrected_text(head_note)

                    cursor = connection.execute(
                        """
                        INSERT INTO small_rhymes
                            (rhyme_id, source_xml_id, head_character, primary_fanqie,
                             ipa, onyomi, homophone_count, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            rhyme_id,
                            entry_nodes[0].attrib.get("id"),
                            head_form.character,
                            primary_fanqie,
                            voice_part.attrib.get("ipa"),
                            voice_part.attrib.get("onyomi"),
                            extract_homophone_count(head_note_text),
                            small_rhyme_order,
                        ),
                    )
                    small_rhyme_id = cursor.lastrowid
                    counts["small_rhymes"] += 1

                    for entry_order, entry_node in enumerate(entry_nodes, start=1):
                        form = entry_form(entry_node)
                        note = entry_node.find("note")
                        if note is None:
                            note = entry_node.find("added_note")
                        definition_text = corrected_text(note)
                        definition_xml = (
                            ET.tostring(note, encoding="unicode") if note is not None else ""
                        )
                        cursor = connection.execute(
                            """
                            INSERT INTO entries
                                (small_rhyme_id, source_xml_id, character,
                                 original_character, definition_text, definition_xml,
                                 is_added, sort_order)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                small_rhyme_id,
                                entry_node.attrib.get("id"),
                                form.character,
                                form.original_character,
                                definition_text,
                                definition_xml,
                                int(entry_node.tag == "added_word"),
                                entry_order,
                            ),
                        )
                        entry_id = cursor.lastrowid
                        counts["entries"] += 1

                        fanqie_nodes = note.findall(".//fanqie") if note is not None else []
                        for fanqie_order, fanqie_node in enumerate(fanqie_nodes, start=1):
                            role = (
                                "primary"
                                if entry_order == 1 and fanqie_node is primary_fanqie_node
                                else "alternate"
                            )
                            connection.execute(
                                """
                                INSERT INTO fanqies (entry_id, text, role, sort_order)
                                VALUES (?, ?, ?, ?)
                                """,
                                (
                                    entry_id,
                                    corrected_text(fanqie_node),
                                    role,
                                    fanqie_order,
                                ),
                            )
                            counts["fanqies"] += 1

        if counts["volumes"] != 5 or counts["rhymes"] != 206:
            raise ValueError(f"Unexpected Guangyun structure: {counts}")
        if counts["small_rhymes"] != 3874:
            raise ValueError(f"Unexpected small-rhyme count: {counts['small_rhymes']}")

        connection.commit()
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise ValueError(f"Foreign-key validation failed: {foreign_key_errors[:5]}")
        connection.execute("VACUUM")
    except Exception:
        connection.close()
        temporary_path.unlink(missing_ok=True)
        raise
    else:
        connection.close()
        target_path.unlink(missing_ok=True)
        temporary_path.replace(target_path)

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a searchable SQLite database from sbgy.xml")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--target", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES_PATH)
    parser.add_argument("--variant-source", type=Path, default=DEFAULT_VARIANT_SOURCE_PATH)
    args = parser.parse_args()
    counts = create_database(
        args.source,
        args.target,
        args.sources,
        args.variant_source,
    )
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
