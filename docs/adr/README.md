# Architecture Decision Records

Short, durable decisions for `agentic-test-forge` contributors and agents. ADRs capture **why** we chose a direction, not step-by-step implementation notes (those live in issues, guides, and `docs/domain/CONTEXT.md`).

## When to write an ADR

Write an ADR when a decision is **hard to reverse** or **affects multiple packages or consumers**, for example:

- Package boundaries, dependency direction, or public API shape
- Exit-code / gate semantics that CI and pre-commit rely on
- Release or distribution policy that consumer repos must follow
- Replacing a major external tool or changing default gate behavior

**Skip an ADR** for routine bug fixes, single-file refactors, threshold tweaks in consumer repos, or work already fully specified in a closed epic ticket.

v1.1 does **not** require new ADRs beyond the index below; optional follow-ups (e.g. PyPI trusted publishing details) can stay in `docs/release-checklist.md` unless they change forge's architecture.

## Numbering convention

- File: `docs/adr/NNNN-short-title.md` (four-digit zero-padded serial)
- Title in document: `ADR NNNN: Human-readable title`
- Status line: `Proposed` → `Accepted` | `Superseded` | `Deprecated`
- Superseded ADRs link forward to the replacement; do not delete old files

Next available serial: **0002** (reserve for release/PyPI only if it encodes a durable architectural choice).

## Template

Use this structure for new ADRs:

```markdown
# ADR NNNN: Title

**Status:** Proposed | Accepted | Superseded | Deprecated
**Date:** YYYY-MM-DD
**Epic / issue:** #…

## Context

What problem or constraint forces a decision? What alternatives were considered?

## Decision

What we will do (and what we explicitly will not do).

## Consequences

Positive and negative outcomes: migration cost, consumer impact, follow-up work.
```

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-package-boundaries-and-refactor-conventions.md) | Package boundaries and refactor conventions | Accepted |

Related docs:

- [Domain language](../domain/CONTEXT.md)
- [Consumer CI guide](../consumer-ci.md)
- [Release checklist](../release-checklist.md)
- [Round 2 refactor inventory](../refactor-analysis/round-2-inventory.md)
