# FleetGuard backend

A thin [FastAPI](https://fastapi.tiangolo.com/) layer that normalizes Traccar's
REST/WebSocket APIs and runs anti-theft detection (implemented as pure
functions). See the [root README](../README.md) for the full picture.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

uvicorn app.main:app --reload   # http://localhost:8000/health

ruff check .      # lint
black --check .   # format check
mypy .            # types (strict)
pytest --cov=app  # tests + coverage
```

## API

With `MOCK_MODE=true` (default) the endpoints serve a simulated fleet around
Matsue / Yasugi / Yonago — no Traccar required.

| Method | Path                  | Description                                   |
| ------ | --------------------- | --------------------------------------------- |
| GET    | `/health`             | Liveness; reports whether mock mode is active |
| GET    | `/api/vehicles`       | All vehicles with latest position + alerts    |
| GET    | `/api/vehicles/{id}`  | A single vehicle (404 if unknown)             |
| GET    | `/api/alerts`         | Active alerts across the fleet                |
| WS     | `/ws/positions`       | Live position + alert snapshots (pushed)      |

Each vehicle's alerts come from the pure-function detection rules in
[`app/detection`](./app/detection).

## Data sources

The API is agnostic about where positions come from: every source implements the
same [`FleetSource`](./app/sources/base.py) contract — `start()`/`aclose()`
bracket its lifetime, `advance()` lets pull sources tick, and `snapshot()` reads
the current state — so the routes, streamer and detection engine never know the
difference.

- **Mock** (`MOCK_MODE=true`): a deterministic, seedable simulation
  ([`app/mock`](./app/mock)).
- **Traccar relay** (`MOCK_MODE=false`): set `TRACCAR_BASE_URL`,
  `TRACCAR_USERNAME` (login email), `TRACCAR_PASSWORD`, and pick a transport
  with `TRACCAR_TRANSPORT`:
  - `ws` (default) — [`TraccarStreamSource`](./app/traccar/stream_source.py)
    authenticates via `/api/session`, then streams `/api/socket` in a
    background task, folding each frame into the snapshot. Reconnects on drop.
  - `rest` — [`TraccarSource`](./app/traccar/source.py) polls `/api/devices` +
    `/api/positions` on each tick; a failed poll keeps the last good snapshot.

The interesting part of the relay is [`app/traccar/normalize.py`](./app/traccar/normalize.py):
pure functions that turn Traccar's wire format into our domain — converting
**speed from knots to m/s**, inferring ignition state from the free-form
`attributes` map (falling back to `motion`, then to speed), parsing timestamps,
joining devices with their latest position (REST), and merging incremental
position frames into the cache (WebSocket). Being pure, they're exhaustively
unit-tested without touching the network; the HTTP/WS plumbing
([`client.py`](./app/traccar/client.py), [`connect.py`](./app/traccar/connect.py))
stays deliberately thin and is the only code that talks to a real server.

> A raw Traccar feed has no depot/anchor, so the geofence rule is disabled for
> relayed vehicles; the other four rules (off-hours, ignition-off, abnormal
> speed/heading) still apply.
