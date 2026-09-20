# Data license

The source data in `data/raw/sbgy.xml` is from the
[CJKVI Dictionary Database](https://github.com/cjkvi/cjkvi-dict), specifically
its `sbgy.xml` edition of 校正宋本廣韻.

The upstream project distributes this data under the GNU General Public
License version 2. A complete copy is included in `LICENSES/GPL-2.0.txt`.
The source revision, download URL, and SHA-256 checksum are recorded in
`data/sources.json`.

Generated SQLite databases and other transformed copies of this dataset should
retain the upstream notices and are distributed under GPL-2.0. The application
source code is separate from the imported dictionary data.

Simplified-to-traditional character aliases are derived from
`Unihan_Variants.txt` in the Unicode Character Database 17.0.0. Unicode data
files are distributed under the Unicode License V3. A complete copy is
included in `LICENSES/UNICODE-3.0.txt`. The pinned archive URL and checksums are
recorded in `data/sources.json`.

The application imports only `kTraditionalVariant` and `kSimplifiedVariant`
relationships.

See `THIRD_PARTY_NOTICES.md` for source-specific attribution and a description
of the transformations performed by this project.
