"""Persist differential mutation state under the forge manifest directory."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FileManifestEntry:
    """Manifest record for one mutated source file."""

    content_hash: str
    score: float | None = None
    last_run: str | None = None


@dataclass(frozen=True)
class MutationManifest:
    """On-disk mutation manifest."""

    files: dict[str, FileManifestEntry]

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": {
                path: asdict(entry) for path, entry in sorted(self.files.items())
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MutationManifest:
        raw_files = payload.get("files", {})
        if not isinstance(raw_files, dict):
            return cls(files={})
        files: dict[str, FileManifestEntry] = {}
        for path, entry in raw_files.items():
            if not isinstance(entry, dict):
                continue
            files[str(path)] = FileManifestEntry(
                content_hash=str(entry.get("content_hash", "")),
                score=_optional_float(entry.get("score")),
                last_run=_optional_str(entry.get("last_run")),
            )
        return cls(files=files)


def manifest_path(manifest_dir: str | Path) -> Path:
    return Path(manifest_dir) / "mutation-manifest.json"


def file_content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def load_manifest(path: Path) -> MutationManifest:
    if not path.is_file():
        return MutationManifest(files={})
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return MutationManifest(files={})
    return MutationManifest.from_dict(payload)


def save_manifest(path: Path, manifest: MutationManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    temp_path.replace(path)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
