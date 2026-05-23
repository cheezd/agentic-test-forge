"""Safe temporary editing of Gherkin feature files during mutation."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


class FeatureFileEditor:
    """Maintain a disposable copy of a feature file for mutation runs."""

    def __init__(self, source_path: Path) -> None:
        self._source_path = source_path
        self._original_lines = source_path.read_text(encoding="utf-8").splitlines()
        self._temp_dir = tempfile.TemporaryDirectory(prefix="forge-gherkin-")
        self._work_path = Path(self._temp_dir.name) / source_path.name
        shutil.copy2(source_path, self._work_path)

    @property
    def source_path(self) -> Path:
        return self._source_path

    @property
    def work_path(self) -> Path:
        return self._work_path

    @property
    def original_lines(self) -> list[str]:
        return list(self._original_lines)

    def write_lines(self, lines: list[str]) -> None:
        """Write mutated content to the temporary copy only."""
        self._work_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def cleanup(self) -> None:
        self._temp_dir.cleanup()

    def __enter__(self) -> FeatureFileEditor:
        return self

    def __exit__(self, *args: object) -> None:
        self.cleanup()
