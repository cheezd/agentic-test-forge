"""Partition scoped items by manifest content hash."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from agentic_test_forge.manifest.store import ForgeManifest

T = TypeVar("T")


def partition_by_manifest_hash(
    items: Iterable[T],
    *,
    key_fn: Callable[[T], str],
    hash_fn: Callable[[T], str],
    manifest: ForgeManifest,
    full_run: bool = False,
) -> tuple[list[T], list[T]]:
    """Split items into selected and manifest-skipped buckets."""
    selected: list[T] = []
    skipped: list[T] = []

    for item in items:
        current_hash = hash_fn(item)
        previous = manifest.files.get(key_fn(item))
        if (
            not full_run
            and previous is not None
            and previous.content_hash == current_hash
        ):
            skipped.append(item)
            continue
        selected.append(item)

    return selected, skipped
