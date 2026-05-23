"""Tests for mutation manifest persistence."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.manifest.store import (
    FileManifestEntry,
    ForgeManifest,
    MutationManifest,
    file_content_hash,
    load_manifest,
    manifest_path,
    save_manifest,
)


def test_manifest_round_trip(tmp_path: Path) -> None:
    path = manifest_path(tmp_path / ".forge")
    manifest = ForgeManifest(
        files={
            "src/example.py": FileManifestEntry(
                content_hash="abc123",
                score=92.5,
                last_run="2026-05-22T12:00:00+00:00",
            ),
        },
    )

    save_manifest(path, manifest)
    loaded = load_manifest(path)

    assert loaded.files["src/example.py"].content_hash == "abc123"
    assert loaded.files["src/example.py"].score == 92.5


def test_file_content_hash_stable(tmp_path: Path) -> None:
    module = tmp_path / "mod.py"
    module.write_text("def foo():\n    return 1\n", encoding="utf-8")

    assert file_content_hash(module) == file_content_hash(module)


def test_mutation_manifest_alias_matches_forge_manifest() -> None:
    entry = FileManifestEntry(content_hash="abc", score=1.0, last_run=None)
    assert MutationManifest(files={"x": entry}) == ForgeManifest(files={"x": entry})
