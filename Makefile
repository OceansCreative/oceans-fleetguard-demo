# FleetGuard — developer convenience targets.
# All targets are phony (no build artefacts). Run `make help` for a summary.

.PHONY: help install dev lint test fmt precommit

# Default target — print a short help menu.
help:
	@printf "\n\033[1mFleetGuard Makefile\033[0m\n\n"
	@printf "  \033[36minstall\033[0m      Install all backend and frontend dependencies\n"
	@printf "  \033[36mdev\033[0m          Start backend (uvicorn) and frontend (next dev) — see NOTE below\n"
	@printf "  \033[36mlint\033[0m         Run ruff + black --check + mypy (backend) and lint + format:check + typecheck (frontend)\n"
	@printf "  \033[36mtest\033[0m         Run pytest with coverage (backend) and vitest (frontend)\n"
	@printf "  \033[36mfmt\033[0m          Auto-format: ruff --fix + black (backend), prettier --write (frontend)\n"
	@printf "  \033[36mprecommit\033[0m    Run pre-commit against all files\n"
	@printf "\n  NOTE: 'make dev' starts both servers sequentially in the \033[1msame terminal\033[0m.\n"
	@printf "        For a better experience, run each in its own terminal:\n"
	@printf "          terminal 1:  cd backend && uv run uvicorn app.main:app --reload\n"
	@printf "          terminal 2:  cd frontend && npm run dev\n\n"

# ---------------------------------------------------------------------------
# install — set up both stacks
# ---------------------------------------------------------------------------
install:
	cd backend && uv sync --extra dev
	cd frontend && npm ci

# ---------------------------------------------------------------------------
# dev — run both servers (blocks on backend; Ctrl-C kills both via trap)
# ---------------------------------------------------------------------------
dev:
	@echo "Starting backend (uvicorn) in background, then frontend (next dev)…"
	@echo "Press Ctrl-C to stop both."
	@trap 'kill %1 2>/dev/null; exit' INT; \
	  (cd backend && uv run uvicorn app.main:app --reload) & \
	  (cd frontend && npm run dev); \
	  wait

# ---------------------------------------------------------------------------
# lint — mirror CI checks exactly (no auto-fix)
# ---------------------------------------------------------------------------
lint:
	cd backend && uv run --extra dev ruff check .
	cd backend && uv run --extra dev black --check .
	cd backend && uv run --extra dev mypy .
	cd frontend && npm run lint
	cd frontend && npm run format:check
	cd frontend && npm run typecheck

# ---------------------------------------------------------------------------
# test — backend pytest (coverage >= 80 %) + frontend vitest
# ---------------------------------------------------------------------------
test:
	cd backend && uv run --extra dev pytest --cov=app --cov-report=term-missing --cov-fail-under=80
	cd frontend && npm test

# ---------------------------------------------------------------------------
# fmt — auto-format (ruff --fix + black for backend, prettier for frontend)
# ---------------------------------------------------------------------------
fmt:
	cd backend && uv run --extra dev ruff check --fix .
	cd backend && uv run --extra dev black .
	cd frontend && npm run format

# ---------------------------------------------------------------------------
# precommit — run pre-commit against every file in the repo
# ---------------------------------------------------------------------------
precommit:
	pre-commit run --all-files
