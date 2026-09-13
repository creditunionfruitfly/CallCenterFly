"""External dataset registry and digest verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileVerification:
    filename: str
    present: bool
    bytes_match: bool
    sha256_match: bool
    observed_bytes: int | None
    observed_sha256: str | None

    @property
    def passed(self) -> bool:
        return self.present and self.bytes_match and self.sha256_match


def load_registry(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def verify_registry(registry_path: Path, data_dir: Path) -> list[FileVerification]:
    registry = load_registry(registry_path)
    results: list[FileVerification] = []
    for filename, expected in registry["files"].items():
        target = data_dir / filename
        if not target.is_file():
            results.append(FileVerification(filename, False, False, False, None, None))
            continue
        observed_bytes = target.stat().st_size
        observed_sha256 = sha256_file(target)
        results.append(
            FileVerification(
                filename=filename,
                present=True,
                bytes_match=observed_bytes == int(expected["bytes"]),
                sha256_match=observed_sha256 == expected["sha256"],
                observed_bytes=observed_bytes,
                observed_sha256=observed_sha256,
            )
        )
    return results
