from __future__ import annotations

import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "data" / "sources.json"


def main() -> None:
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))["sources"]
    metadata = sources["guangyun"]
    target = ROOT / metadata["file"]
    target.parent.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(metadata["source_url"], timeout=60) as response:
        content = response.read()
    digest = hashlib.sha256(content).hexdigest()
    if digest != metadata["sha256"]:
        raise SystemExit(f"SHA-256 mismatch: expected {metadata['sha256']}, received {digest}")
    target.write_bytes(content)
    print(f"Downloaded {len(content)} bytes to {target}")

    unihan_metadata = sources["unihan_variants"]
    with urllib.request.urlopen(unihan_metadata["source_url"], timeout=60) as response:
        archive = response.read()
    archive_digest = hashlib.sha256(archive).hexdigest()
    if archive_digest != unihan_metadata["archive_sha256"]:
        raise SystemExit(
            "Unihan archive SHA-256 mismatch: "
            f"expected {unihan_metadata['archive_sha256']}, received {archive_digest}"
        )
    with zipfile.ZipFile(io.BytesIO(archive)) as unihan_zip:
        variant_content = unihan_zip.read(unihan_metadata["archive_member"])
    variant_digest = hashlib.sha256(variant_content).hexdigest()
    if variant_digest != unihan_metadata["sha256"]:
        raise SystemExit(
            "Unihan variants SHA-256 mismatch: "
            f"expected {unihan_metadata['sha256']}, received {variant_digest}"
        )
    variant_target = ROOT / unihan_metadata["file"]
    variant_target.write_bytes(variant_content)
    print(f"Downloaded {len(variant_content)} bytes to {variant_target}")


if __name__ == "__main__":
    main()
