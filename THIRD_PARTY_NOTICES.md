# Third-party data notices

## CJKVI 校正宋本廣韻

- Project: CJKVI Dictionary Database
- Project URL: https://github.com/cjkvi/cjkvi-dict
- Source file: `sbgy.xml`
- Pinned revision and checksum: `data/sources.json`
- License: GNU General Public License version 2
- License text: `LICENSES/GPL-2.0.txt`

This project converts the XML source into an indexed SQLite database and
exposes selected records through a search website and REST API. The original
XML is preserved in `data/raw/sbgy.xml`; generated database copies remain
subject to GPL-2.0.

## Facsimile images

- Source: https://www.wul.waseda.ac.jp/kotenseki/html/ho04/ho04_01757/index.html

Facsimile images are from Waseda University Library's Japanese and Chinese
Classics database and are displayed in their original format through direct
links to the source image files, without modification or rehosting. Use of
these images is subject to the terms published by Waseda University Library.

## Unicode Unihan Variants

- Project: Unicode Character Database
- Project URL: https://www.unicode.org/reports/tr38/
- Source file: `Unihan_Variants.txt`
- Pinned version and checksums: `data/sources.json`
- License: Unicode License V3
- License text: `LICENSES/UNICODE-3.0.txt`

This project extracts `kTraditionalVariant` and `kSimplifiedVariant`
relationships to support simplified-character lookup. Unicode copyright and
permission notices are retained in the accompanying license text.
