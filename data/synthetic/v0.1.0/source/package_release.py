#!/usr/bin/env python3
"""Create a reproducible ZIP and SHA-256 manifest for the dataset release."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
ZIP_PATH = RELEASE / "CallCenterFly_Synthetic_Credit_Union_Dataset_v0.1.0.zip"
CHECKSUM_PATH = ROOT / "SHA256SUMS"
FIXED_ZIP_TIME = (2026, 9, 12, 0, 0, 0)


def included_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if rel.parts[0] in {"release", "outputs"}:
            continue
        if "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        if rel.as_posix() == "SHA256SUMS":
            continue
        yield path, rel


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    RELEASE.mkdir(parents=True, exist_ok=True)
    files = list(included_files())
    checksum_text = "".join(f"{sha256(path)}  {rel.as_posix()}\n" for path, rel in files)
    CHECKSUM_PATH.write_text(checksum_text, encoding="utf-8")

    zip_files = list(files) + [(CHECKSUM_PATH, Path("SHA256SUMS"))]
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, rel in zip_files:
            info = zipfile.ZipInfo(f"CallCenterFly_Synthetic_Credit_Union_Dataset_v0.1.0/{rel.as_posix()}")
            info.date_time = FIXED_ZIP_TIME
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    print(f"{ZIP_PATH.name}\t{ZIP_PATH.stat().st_size}\t{sha256(ZIP_PATH)}")


if __name__ == "__main__":
    main()
