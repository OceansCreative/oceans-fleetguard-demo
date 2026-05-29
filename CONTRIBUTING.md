# Contributing to FleetGuard

Thanks for your interest in contributing! This document describes how we work,
so that history stays clean and reviewable.

## Code of Conduct

This project adheres to a [Code of Conduct](./CODE_OF_CONDUCT.md). By
participating, you are expected to uphold it.

## Development workflow

We keep history clean and every change reviewable — even for solo work.

1. **One issue per unit of work.** Open (or pick up) an issue describing the
   change before you start.
2. **Branch.** Create a feature branch off the default branch:
   `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`, etc.
3. **Commit in logical units.** One commit = one logical change. We follow
   [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` a new feature
   - `fix:` a bug fix
   - `docs:` documentation only
   - `test:` adding or fixing tests
   - `refactor:` code change that neither fixes a bug nor adds a feature
   - `chore:` tooling, config, dependencies, CI
4. **Open a PR** that closes the issue (`Closes #N`). The PR description must
   cover **Background / Changes / How to verify / Impact** (the template does
   this for you).
5. **Self-review**, ensure CI is green, then **squash-merge**.

No merges without passing CI. No feature merges without tests.

## Definition of done

A change is "done" when it is:

- ✅ **Tested** — new logic has unit tests; theft-detection rules are covered
  including boundary and error cases.
- ✅ **Typed** — TypeScript `strict` passes `tsc --noEmit`; Python passes
  `mypy --strict`.
- ✅ **Linted & formatted** — ESLint + Prettier (TS); ruff + black (Python).
- ✅ **Documented** — relevant docs / README updated.

## Local development

```bash
cp .env.example .env

# Frontend (Next.js)
cd frontend
npm install
npm run dev          # lint: npm run lint · types: npm run typecheck · test: npm test

# Backend (FastAPI)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload   # lint: ruff check . · types: mypy . · test: pytest

# Full stack via Docker
docker compose -f infra/docker-compose.yml up
```

## Security & secrets

**Never commit credentials, API keys, or personal information.** Use `.env`
locally (git-ignored) and GitHub Secrets in CI. See [SECURITY.md](./SECURITY.md)
to report vulnerabilities.
