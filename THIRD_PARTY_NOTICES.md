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

