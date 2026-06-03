# FleetGuard — Production Deployment & Hardening Guide

This guide covers running FleetGuard in an internet-exposed environment: environment
configuration, authentication, CORS, TLS termination, notifications, basemap
providers, and a hardening checklist.

---

## Contents

1. [Overview & modes](#1-overview--modes)
2. [Environment setup](#2-environment-setup)
3. [Authentication (API key)](#3-authentication-api-key)
4. [CORS](#4-cors)
5. [Reverse proxy & TLS](#5-reverse-proxy--tls)
6. [Notifications](#6-notifications)
7. [Basemap providers](#7-basemap-providers)
8. [Hardening checklist](#8-hardening-checklist)
9. [Known limitations](#9-known-limitations)

---

## 1. Overview & modes

FleetGuard has two runtime modes, selected by `MOCK_MODE`:

| Mode | `MOCK_MODE` | What runs |
|------|-------------|-----------|
| **Mock** (default) | `true` | Backend generates simulated vehicles around Matsue / Yasugi / Yonago. No Traccar server required. |
| **Live** | `false` | Backend relays a real [Traccar](https://www.traccar.org/) server over WebSocket (`TRACCAR_TRANSPORT=ws`, the default) or REST polling (`TRACCAR_TRANSPORT=rest`). |

The mock is the safe starting point for verifying the stack. Switch to live mode
only after confirming Traccar is reachable and credentialed (see
[infra/README.md](../infra/README.md)).

---

## 2. Environment setup

Copy the example file and edit it before starting the stack:

```bash
cp .env.example .env
# edit .env — never commit .env
```

The docker-compose stack reads `../.env` relative to `infra/`:

```bash
docker compose -f infra/docker-compose.yml up
```

### Key variables for an exposed deployment

| Variable | Default | Notes |
|----------|---------|-------|
| `MOCK_MODE` | `true` | Set `false` to relay a live Traccar feed. |
| `BACKEND_HOST` | `0.0.0.0` | Listen address; usually leave as-is behind a proxy. |
| `BACKEND_PORT` | `8000` | |
| `CORS_ORIGINS` | `http://localhost:3000` | **Must** be set to your real dashboard origin(s). |
| `API_KEY` | _(empty)_ | **Must** be set to a strong random value for any exposed deployment. |
| `NOTIFY_WEBHOOK_URL` | _(empty)_ | Optional. Receives CRITICAL alert POSTs. |
| `TRACCAR_BASE_URL` | `http://traccar:8082` | Used when `MOCK_MODE=false`. |
| `TRACCAR_WS_URL` | `ws://traccar:8082/api/socket` | Used when `MOCK_MODE=false` and `TRACCAR_TRANSPORT=ws`. |
| `TRACCAR_USERNAME` | _(empty)_ | Traccar login (email). |
| `TRACCAR_PASSWORD` | _(empty)_ | Traccar password. |
| `TRACCAR_TRANSPORT` | `ws` | `ws` (streaming) or `rest` (polling). |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Rewrite to your public backend URL. |
| `NEXT_PUBLIC_WS_BASE_URL` | `ws://localhost:8000` | Rewrite to your public backend WebSocket URL. |
| `NEXT_PUBLIC_API_KEY` | _(empty)_ | Must match `API_KEY` when auth is enabled. See §3. |
| `NEXT_PUBLIC_MAP_STYLE_URL` | _(empty)_ | Optional remote vector-tile style (light). |
| `NEXT_PUBLIC_MAP_STYLE_URL_DARK` | _(empty)_ | Optional remote vector-tile style (dark). |
| `NEXT_PUBLIC_MAP_AERIAL_URL` | _(empty)_ | Optional aerial/hybrid raster style; toggle disabled until set. |
| `NEXT_PUBLIC_MAP_ATTRIBUTION` | OSM/ekidata credit | Override when using a third-party tile provider. |
| `POSTGRES_DB` | `traccar` | PostgreSQL database name (Traccar storage). |
| `POSTGRES_USER` | `traccar` | |
| `POSTGRES_PASSWORD` | `change-me-in-local-env` | **Change this** for any non-local deployment. |

---

## 3. Authentication (API key)

### How it works

When `API_KEY` is set to a non-empty value, all `/api/*` routes and the
`/ws/positions` WebSocket require the key. The `/health` endpoint is always
open (by design, for orchestrator probes).

**REST endpoints** — send the key in one of two ways:

```http
GET /api/vehicles HTTP/1.1
X-API-Key: <your-key>
```

or

```http
GET /api/vehicles HTTP/1.1
Authorization: Bearer <your-key>
```

**WebSocket** — browsers cannot set custom headers on a WebSocket handshake, so
the key is passed as a query parameter:

```
wss://your-host/ws/positions?key=<your-key>
```

Connections with a missing or incorrect key are closed immediately with
WebSocket close code 1008 (Policy Violation).

### Generating a strong key

```bash
openssl rand -hex 32
```

Set the result as `API_KEY` in `.env` and as `NEXT_PUBLIC_API_KEY` in the same
file (the frontend picks it up at build time).

### Important caveat: `NEXT_PUBLIC_API_KEY` is browser-visible

Any variable prefixed `NEXT_PUBLIC_` is embedded in the compiled Next.js bundle
and is visible to anyone who can load the page. It gates casual / accidental
access but is not a secret.

**Before exposing the dashboard publicly:**
- Add real user authentication (e.g. an identity provider in front of the
  frontend, or a backend-for-frontend that exchanges a user session for
  API access).
- Consider not setting `NEXT_PUBLIC_API_KEY` at all and using a
  backend-for-frontend that injects the backend key server-side.

---

## 4. CORS

The backend's CORS policy is deliberately narrow:

- **Allowed methods:** `GET` only.
- **Allowed headers:** `Authorization`, `Content-Type`, `X-API-Key`.
- **Allowed origins:** the comma-separated list in `CORS_ORIGINS`.

For a production deployment, set `CORS_ORIGINS` to the exact origin(s) of your
dashboard (scheme + host + port if non-standard):

```dotenv
CORS_ORIGINS=https://fleet.example.com
```

Multiple origins (e.g. staging + production):

```dotenv
CORS_ORIGINS=https://fleet.example.com,https://staging.fleet.example.com
```

Do **not** use a wildcard (`*`) in combination with `allow_credentials=True`;
the browser will block the requests.

---

## 5. Reverse proxy & TLS

Terminate HTTPS at a reverse proxy (nginx, Caddy, Traefik, etc.) in front of
both the backend (port 8000) and the frontend (port 3000). The WebSocket
endpoint requires the proxy to forward the `Upgrade` header.

### Example: nginx

```nginx
# /etc/nginx/sites-available/fleetguard

# Redirect bare HTTP to HTTPS
server {
    listen 80;
    server_name fleet.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name fleet.example.com;

    ssl_certificate     /etc/letsencrypt/live/fleet.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fleet.example.com/privkey.pem;

    # Frontend (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend REST API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend health (liveness probe)
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # WebSocket — must forward Upgrade / Connection headers
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;   # keep long-lived WS connections alive
    }
}
```

Update `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_WS_BASE_URL` accordingly:

```dotenv
NEXT_PUBLIC_API_BASE_URL=https://fleet.example.com
NEXT_PUBLIC_WS_BASE_URL=wss://fleet.example.com
```

### Example: Caddy (automatic HTTPS)

```caddyfile
fleet.example.com {
    # Frontend
    reverse_proxy / http://127.0.0.1:3000

    # Backend REST & health
    reverse_proxy /api/* http://127.0.0.1:8000
    reverse_proxy /health http://127.0.0.1:8000

    # WebSocket (Caddy handles Upgrade automatically)
    reverse_proxy /ws/* http://127.0.0.1:8000
}
```

---

## 6. Notifications

Set `NOTIFY_WEBHOOK_URL` to receive HTTP POST notifications when a vehicle
enters a **CRITICAL** alert state:

```dotenv
NOTIFY_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/replace-me
```

Behaviour:

- The POST fires once when a vehicle *enters* a critical state, not on every
  broadcast tick (deduplicated per vehicle + alert type).
- The alert is re-sent only if the condition clears and then recurs.
- If the webhook endpoint is unreachable the error is logged but the position
  feed continues uninterrupted.
- Leave `NOTIFY_WEBHOOK_URL` empty to disable notifications entirely.

Payload shape:

```json
{
  "event": "critical_alert",
  "vehicle": { "id": "...", "name": "...", "plate": "..." },
  "alert":   { "type": "...", "severity": "critical", "reason": "..." },
  "position": { "lat": 35.47, "lon": 133.05 },
  "at": "2024-01-15T09:23:00+00:00"
}
```

This format is compatible with Slack/Discord incoming webhooks when the
receiving endpoint transforms the body, or can be consumed directly by a custom
receiver, an email/SMS gateway, or an alerting pipeline.

---

## 7. Basemap providers

By default the frontend renders a self-contained offline vector basemap built
from bundled GeoJSON. It works without any API key and in air-gapped
environments, but covers only the local area.

For full street detail in production, point the map at a remote vector-tile
style:

```dotenv
# Light basemap (MapTiler example)
NEXT_PUBLIC_MAP_STYLE_URL=https://api.maptiler.com/maps/streets/style.json?key=replace-me

# Dark basemap
NEXT_PUBLIC_MAP_STYLE_URL_DARK=https://api.maptiler.com/maps/streets-dark/style.json?key=replace-me

# Aerial / satellite — the toggle in the UI stays disabled until this is set
NEXT_PUBLIC_MAP_AERIAL_URL=https://api.maptiler.com/maps/hybrid/style.json?key=replace-me

# Attribution override when using a third-party provider
NEXT_PUBLIC_MAP_ATTRIBUTION=© MapTiler © OpenStreetMap contributors
```

If a remote style fails to load (network error, bad key, etc.) the app falls
back to the offline basemap automatically rather than showing a blank map.

**Provider host allowlisting:** the provider's domain (e.g.
`api.maptiler.com`) must be reachable from the browser. If your deployment is
behind a corporate proxy or firewall, add the tile host to your allowlist.

---

## 8. Hardening checklist

Work through this list before exposing the stack to the internet:

- [ ] **API key** — set `API_KEY` to a cryptographically random value
      (`openssl rand -hex 32`); set the same value as `NEXT_PUBLIC_API_KEY`.
- [ ] **PostgreSQL password** — change `POSTGRES_PASSWORD` from the default
      `change-me-in-local-env` to a strong password.
- [ ] **CORS origins** — set `CORS_ORIGINS` to the exact origin(s) of your
      dashboard; remove `localhost` entries.
- [ ] **TLS** — terminate HTTPS at the reverse proxy; never serve the API or
      frontend over plain HTTP in production.
- [ ] **WebSocket URL** — use `wss://` (not `ws://`) in
      `NEXT_PUBLIC_WS_BASE_URL`.
- [ ] **Do not expose Traccar directly** — in live mode, Traccar runs on port
      8082; bind it to `127.0.0.1` or keep it behind the docker network.
      The backend is the only service that should talk to Traccar.
- [ ] **Do not expose PostgreSQL** — the database port should never be
      reachable from outside the docker network.
- [ ] **Health endpoint** — `/health` is intentionally unauthenticated (for
      orchestrator probes); verify nothing sensitive is added to its response.
- [ ] **Rate limiting** _(recommended)_ — add rate limiting at the reverse
      proxy (e.g. nginx `limit_req_zone`, Caddy `rate_limit`, Traefik
      `rateLimit` middleware) to protect the API and WebSocket upgrade path.
- [ ] **Real user authentication** _(recommended)_ — `NEXT_PUBLIC_API_KEY` is
      visible in the browser bundle. For any deployment with non-trivial data
      sensitivity, front the dashboard with a proper identity provider (OAuth,
      OIDC, etc.) or implement a backend-for-frontend that authenticates users
      before proxying requests to the backend API.

---

## 9. Known limitations

**Single-process, in-memory state.** The backend holds all vehicle state and
alert deduplication in memory within a single process. This means:

- Running multiple backend workers (e.g. `uvicorn --workers N` or a replicated
  container) will result in split state — different clients may see different
  snapshots. Run a single backend instance, or add a shared state layer (Redis,
  a database) before scaling horizontally.
- A backend restart discards in-flight alert deduplication; the first broadcast
  after restart will re-fire CRITICAL notifications for any currently active
  conditions.

**Mock mode is keyless by design.** When `MOCK_MODE=true` and `API_KEY` is
empty, the backend accepts all requests without authentication. This is
intentional for local quick-start. In an exposed deployment, always set
`API_KEY` regardless of mode.

**Geofence rule is disabled for live Traccar vehicles.** A raw Traccar feed
carries no depot anchor, so the geofence breach rule is suppressed for relayed
vehicles. The off-hours, ignition-off, abnormal speed, and abnormal heading
rules remain active.

**Traccar reconnection.** In `TRACCAR_TRANSPORT=ws` mode, if the Traccar
WebSocket drops, the backend reconnects in the background and serves the last
known snapshot in the interim. In `rest` mode, the last successful poll result
is served. Either way no error is surfaced to the dashboard until Traccar has
been unreachable for several consecutive cycles.
