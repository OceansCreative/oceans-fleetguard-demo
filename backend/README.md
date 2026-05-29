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
