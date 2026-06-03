# CLAUDE.md

Guidance for AI agents (and humans) working in this repository. Read this first;
it lets you orient without scanning the whole tree.

## What this is

**FleetGuard** — a reference fleet-tracking & **anti-theft** dashboard that sits
in front of a [Traccar](https://www.traccar.org/) GPS server. The backend
normalizes Traccar's REST/WebSocket feed, runs theft-detection rules, and streams
vehicles + alerts to a live map dashboard. A built-in **mock mode**
(`MOCK_MODE=true`, the default) runs the whole experience with no Traccar or GPS
hardware.

## Repository layout

| Path | What |
| --- | --- |
| `backend/` | FastAPI relay + anti-theft detection (Python 3.12, `uv`) |
| `backend/app/detection/` | Pure-function detection rules, models, geo helpers |
| `backend/app/traccar/` | Traccar client + WS/REST normalization (thin I/O shells) |
| `backend/app/api/` | Routes, schemas, fleet service, streamer, security, auth, ratelimit |
| `backend/app/notify/`, `app/alerts/`, `app/observability/` | Webhook, alert history, logging/request-id/ready |
| `frontend/` | Next.js 15 (App Router) + React 19 + TS, MapLibre map, Vitest |
| `frontend/lib/` | Pure helpers + hooks (api, useFleet, i18n, auth, parse, format, liveSocket) |
| `e2e/` | Playwright smoke test (isolated package; boots both servers) |
| `infra/` | docker-compose: Traccar + PostgreSQL + backend + frontend |
| `docs/` | Screenshots + `DEPLOYMENT.md` (production & hardening guide) |
| `.claude/` | `commands/ship.md`, `agents/` (backend/frontend engineers, reviewers), `settings.json` |

State worth reading before big changes: `README.md` (features), `CHANGELOG.md`
(what landed), `docs/DEPLOYMENT.md` (ops), `.env.example` (every env var).

## Core conventions (house style)

- **Backend: business logic in pure, exhaustively unit-tested functions; I/O
  (HTTP, WebSocket, time, env) in thin, injectable shells.** See
  `app/notify/webhook.py`, `app/detection/rules.py`, `app/api/security.py`.
  Inject clocks/fakes in tests — no real network or `sleep`.
- **Opt-in features stay OFF by default** so the keyless `MOCK_MODE` quickstart
  works with zero config. Auth (`API_KEY`, `AUTH_SECRET`), rate limiting
  (`RATE_LIMIT_PER_MINUTE`), and webhooks (`NOTIFY_WEBHOOK_URL`) are all disabled
  unless their env var is set.
- **Type everything.** Backend is `mypy --strict`; frontend is strict `tsc`.
- **No new dependencies** unless the task requires it — both stacks are lean.
- **Frontend: localize user-visible strings** via `lib/i18n.tsx` (`t("key")`,
  add to BOTH `en` and `ja`). The offline MapLibre basemap must work with no API
  key; remote styles are optional overrides.
- Keep functions within ruff's `mccabe` complexity ≤ 8; extract helpers.

## Quality gates (run before declaring done — never weaken config)

Backend (in `backend/`, via `uv` so deps resolve — running `mypy` outside `uv`
emits bogus `import-not-found` errors):

```
uv run --extra dev ruff check .
uv run --extra dev black --check .
uv run --extra dev mypy .
uv run --extra dev pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

Frontend (in `frontend/`):

```
npm ci && npm run lint && npm run format:check && npm run typecheck && npm run build && npm test
```

E2E (in `e2e/`): `npm ci && npx playwright install chromium && npx playwright test`
(boots backend mock + frontend automatically). `make lint` / `make test` /
`make fmt` wrap the above; `.pre-commit-config.yaml` mirrors CI.

## Running the app locally

Backend: `cd backend && MOCK_MODE=true CORS_ORIGINS=http://localhost:3000 uv run uvicorn app.main:app --port 8000`
Frontend: `cd frontend && NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000 npm run dev`
Then open http://localhost:3000. Or `docker compose -f infra/docker-compose.yml up`.

## Parallel work (`/ship`)

This repo is set up for worktree-isolated parallel subagents:
- `.claude/commands/ship.md` — the orchestrator: decompose a goal into 2–5
  file-independent workstreams, get approval, run worktree-isolated subagents,
  return a review checklist (no auto-merge). The orchestrator keeps its own
  context minimal — it doesn't read large files, it delegates to read-only
  subagents and takes short summaries.
- `.claude/agents/` — `backend-engineer` / `frontend-engineer` (impl,
  `isolation: worktree`), `code-reviewer` / `security-reviewer` (read-only).
- `.claude/settings.json` — `worktree.baseRef = "fresh"` (worktrees branch from a
  fresh default). When work must build on the current feature branch, the
  subagent resets onto it explicitly before starting.
- `.worktreeinclude` copies env files into new worktrees.

Conventions: stage changes, don't commit unless asked; never print or commit
secrets / `.env` contents; verify a branch's gate independently before trusting a
subagent's "green" report.
