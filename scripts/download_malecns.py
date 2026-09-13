#!/usr/bin/env python3
"""Download the three locked MaleCNS inputs without enabling the simulator."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "datasets" / "malecns_v1.json"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    args.destination.mkdir(parents=True, exist_ok=True)
    print(f"MaleCNS license: {registry['license']}")
    print(f"Release: {registry['release_url']}")
    for filename, entry in registry["files"].items():
        target = args.destination / filename
        if target.exists():
            if target.stat().st_size == entry["bytes"] and digest(target) == entry["sha256"]:
                print(f"verified existing {filename}")
                continue
            raise RuntimeError(f"existing file failed verification; refusing overwrite: {target}")
        print(f"download {filename} ({entry['bytes']} bytes)")
        if args.dry_run:
            continue
        partial = target.with_suffix(target.suffix + ".partial")
        urllib.request.urlretrieve(entry["url"], partial)
        if partial.stat().st_size != entry["bytes"] or digest(partial) != entry["sha256"]:
            raise RuntimeError(f"download verification failed: {filename}")
        partial.replace(target)
        print(f"verified {filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
