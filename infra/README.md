# FleetGuard infra

One-command local stack via [docker-compose.yml](./docker-compose.yml):
PostgreSQL → Traccar → backend → frontend.

```bash
cp ../.env.example ../.env       # mock mode is on by default
docker compose -f infra/docker-compose.yml up
# dashboard:   http://localhost:3000
# backend:     http://localhost:8000/health
# Traccar UI:  http://localhost:8082
```

| Service    | Port(s)      | Notes                                            |
| ---------- | ------------ | ------------------------------------------------ |
| `postgres` | (internal)   | Traccar's datastore; data persists in `./data`.  |
| `traccar`  | 8082, 5055   | REST/WebSocket on 8082, OsmAnd device feed on 5055. |
| `backend`  | 8000         | FastAPI relay + detection.                       |
| `frontend` | 3000         | Next.js dashboard.                               |

Traccar is configured from the environment (`CONFIG_USE_ENVIRONMENT_VARIABLES`)
to persist to PostgreSQL instead of its embedded H2 database, so devices and
history survive restarts.

## Going live (relaying a real Traccar)

By default `MOCK_MODE=true`, so the backend serves the simulation and Traccar is
optional. To relay a live Traccar feed:

**1. Bring up the stack and create a Traccar account.** The first account
registered on a fresh Traccar becomes the admin:

```bash
docker compose -f infra/docker-compose.yml up -d postgres traccar
# Register via the API (or do it in the web UI at http://localhost:8082):
curl -X POST http://localhost:8082/api/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"demo","email":"demo@example.com","password":"changeme","administrator":true}'
```

**2. Point the backend at that account.** In `../.env`:

```dotenv
MOCK_MODE=false
TRACCAR_USERNAME=demo@example.com   # Traccar logs in by email
TRACCAR_PASSWORD=changeme
TRACCAR_TRANSPORT=ws                # "ws" streams /api/socket (default); "rest" polls
```

**3. Restart the backend** so it picks up the new settings:

```bash
docker compose -f infra/docker-compose.yml up -d --no-deps backend frontend
```

**4. Add a device and feed it a position.** Register a device with a `uniqueId`
in the Traccar UI (or API), then push a fix over the OsmAnd protocol on 5055:

```bash
curl "http://localhost:5055/?id=test-001&lat=35.4723&lon=133.0505&speed=10&heading=90&timestamp=$(date +%s)"
```

Within a couple of seconds the vehicle appears on the dashboard with live
detection running. Because a raw Traccar feed carries no depot anchor, the
geofence rule is disabled for relayed vehicles; the other four rules
(off-hours, ignition-off, abnormal speed/heading) stay active.

> The relay degrades gracefully: if Traccar is unreachable the backend keeps
> serving the last known snapshot (REST) or reconnects in the background (WS),
> rather than erroring out. So startup ordering is best-effort, not required.
