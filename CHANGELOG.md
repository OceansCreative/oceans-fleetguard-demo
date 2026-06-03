# Changelog

All notable changes to FleetGuard are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project has not
cut a tagged release yet, so everything lands under **Unreleased**.

## [Unreleased]

### Added

- **Live vector map** — migrated to MapLibre GL with a self-contained offline
  style (no API key required) and a light / dark / aerial basemap switcher.
  Optional remote vector/aerial styles (e.g. MapTiler) via `NEXT_PUBLIC_MAP_*`.
- **Bilingual UI** — EN / 日本語 i18n with a header toggle, browser-detected and
  persisted to `localStorage`.
- **Anti-theft rule: signal lost / stale position** — fires when a vehicle stops
  reporting for longer than a threshold (possible GPS jamming / tampering).
- **Alert history** — in-memory ring buffer exposed at `GET /api/alerts/history`
  (deduplicated per vehicle + alert type).
- **CRITICAL webhook notifications** — opt-in `NOTIFY_WEBHOOK_URL`, deduplicated,
  non-blocking.
- **Optional API-key auth** — shared secret on `/api` (header / bearer) and
  `/ws/positions` (`?key=`), constant-time comparison.
- **Optional user login** — a second, independent opt-in gate issuing signed
  stdlib HS256 session tokens via `POST /api/auth/login`, with a login UI.
  Supports **multiple accounts** via an `AUTH_USERS` JSON map
  (`{username: password_hash}`), merged with the single-user
  `AUTH_USERNAME`/`AUTH_PASSWORD_HASH` shorthand. Login is user-enumeration
  resistant (constant-time, hashes unconditionally).
- **AUTH_USERS generator CLI** — `python -m app.tools.gen_auth_users alice bob`
  prompts for each password, scrypt-hashes it, and prints a ready-to-paste
  `AUTH_USERS=...` line.
- **Per-IP rate limiting** — opt-in `RATE_LIMIT_PER_MINUTE` on `/api` and `/ws`.
- **Observability** — structured (JSON) logging with request IDs and a `/ready`
  readiness probe (`LOG_LEVEL` / `LOG_FORMAT`). Gated `/api` requests emit a
  **per-user audit log** line, and the authenticated username rides on every
  log record for the request (the `user` field in JSON logs).
- **CI & supply chain** — GitHub Actions (backend + frontend gates), Dependabot
  (pip / npm / actions), and CodeQL.
- **Developer experience** — `Makefile` (`make lint` / `test` / `fmt` / `dev`)
  and `.pre-commit-config.yaml` mirroring the CI gates.
- **Docs** — dashboard screenshots and a production deployment & hardening guide
  ([docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)).

### Changed

- CORS narrowed to `GET` plus the auth/content headers.
- README feature list, architecture table, and `.env.example` updated to reflect
  the above.

### Security

- All auth, rate-limiting, and notification features are **off by default**, so
  the keyless `MOCK_MODE` quickstart keeps working with zero configuration.
- Login uses a constant-time, non-short-circuiting credential check. Passwords
  are matched against an unsalted sha256 digest (MVP) — use a salted KDF
  (bcrypt / argon2) and an httpOnly-cookie session for hardened deployments;
  see [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md).
