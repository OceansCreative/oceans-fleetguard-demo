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
[`app/detection`](./app/detection). When `MOCK_MODE=false` the fleet is empty
(the live Traccar relay lands in a later PR).
