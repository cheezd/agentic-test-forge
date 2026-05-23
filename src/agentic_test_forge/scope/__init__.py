"""Shared git and path utilities for forge scope and analysis."""

from agentic_test_forge.scope.git import GitScopeError, run_git_diff_names
from agentic_test_forge.scope.paths import (
    filter_git_changed_files,
    is_under_any,
    iter_files_by_suffix,
    normalize_paths,
    resolve_search_root,
    to_posix_relative,
)

__all__ = [
    "GitScopeError",
    "filter_git_changed_files",
    "is_under_any",
    "iter_files_by_suffix",
    "normalize_paths",
    "resolve_search_root",
    "run_git_diff_names",
    "to_posix_relative",
]
