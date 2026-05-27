# Release checklist — Phase A (PyPI + public repository)

Use this checklist **before** the first `v1.0.0` tag. Order matters: complete secrets scan and repository visibility **before** publishing to PyPI.

## 1. Pre-public secrets scan (required)

The repository is currently **private** and will be made **public** at release. Scan for credentials that must not be exposed.

### Automated / local checks

```bash
# From repo root — no .env or credential files tracked
git ls-files | rg -i '\.(env|pem|key|p12|pfx)$' || true
git grep -iE '(api[_-]?key|secret|password|token|pypi-[a-zA-Z0-9-]{50,}|ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{20,})' -- ':!docs/release-checklist.md' ':!.github/workflows/publish.yml'
```

### Manual review

- [ ] No `.env`, `.env.*`, or credential JSON files in git history or working tree
- [ ] No API keys, PyPI tokens, GitHub PATs, or private URLs with embedded credentials in source or docs
- [ ] No real hostnames, database URLs, or internal-only paths that should stay private
- [ ] `workspace/` remains gitignored (local discovery artifacts only)
- [ ] GitHub Actions secrets: only intended names (`PYPI_API_TOKEN` fallback if used); no secret values in workflow YAML

### If findings exist

Remove secrets, rotate compromised credentials, rewrite history if needed, then re-run the scan before continuing.

## 2. Make repository public (required)

PyPI metadata, README, and VCS install URLs point at this GitHub repository. Consumers expect public source for an LGPL-licensed package.

- [ ] Secrets scan (section 1) complete with no blockers
- [ ] GitHub → **Settings → General → Danger Zone → Change repository visibility → Public**
- [ ] Confirm README and `pyproject.toml` `[project.urls]` links resolve without authentication

**Note:** Other repos (e.g. `compliance-llm-analysis-platform`) may remain private.

## 3. PyPI Trusted Publishing (required)

- [ ] Register [agentic-test-forge](https://pypi.org/project/agentic-test-forge/) on PyPI (verify name at registration)
- [ ] PyPI → Publishing → Add pending publisher:
  - Owner: `cheezd`
  - Repository: `agentic-test-forge`
  - Workflow: `publish.yml`
  - Environment: `pypi`
- [ ] GitHub → Settings → Environments → create **`pypi`** (optional protection rules)

## 4. Merge, tag, verify

- [ ] Merge Phase A PR to `main`
- [ ] Tag and push: `git tag v1.0.0 && git push origin v1.0.0`
- [ ] Confirm Publish workflow succeeds (PyPI upload + GitHub Release)
- [ ] Verify: `pip install agentic-test-forge==1.0.0` and `forge --help` ([#68](https://github.com/cheezd/agentic-test-forge/issues/68))

## Rollback

- PyPI: yank bad release; ship patch tag (e.g. `v1.0.1`)
- Do not force-delete published tags
