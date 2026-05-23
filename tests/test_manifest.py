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
    prune_stale_manifest_entries,
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


def test_prune_stale_manifest_entries_drops_invalid_keys() -> None:
    active = FileManifestEntry(content_hash="live", score=1.0, last_run=None)
    stale = FileManifestEntry(content_hash="gone", score=2.0, last_run=None)
    files = {
        "src/live.py": active,
        "src/removed.py": stale,
    }

    pruned = prune_stale_manifest_entries(
        files,
        key_is_valid=lambda key: key == "src/live.py",
    )

    assert set(pruned) == {"src/live.py"}
    assert pruned["src/live.py"] == active


def test_prune_stale_manifest_entries_retains_untouched_valid_keys() -> None:
    untouched = FileManifestEntry(content_hash="old", score=90.0, last_run="2026-01-01")
    updated = FileManifestEntry(content_hash="new", score=100.0, last_run="2026-05-23")
    files = {
        "src/unchanged.py": untouched,
        "src/updated.py": updated,
    }
    valid_keys = {"src/unchanged.py", "src/updated.py"}

    pruned = prune_stale_manifest_entries(
        files,
        key_is_valid=lambda key: key in valid_keys,
    )

    assert pruned == files
