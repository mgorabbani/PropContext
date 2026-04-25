# AGENTS.md — Buena Context Engine

Cross-tool memory file for Claude Code, Cursor, Codex, and any other agent. Source of truth for design pattern and code style. **Keep current.** When patterns change, update this file in the same commit.

> `CLAUDE.md` is a symlink to this file. Do not duplicate.

---

## What this repo is

Living building memory for Buena (Berlin property mgmt). Pipeline ingests emails / invoices / bank tx / `stammdaten.json`, compresses into one `building.md` per property. External AI agent fetches `building.md` over HTTP. Full PRD: `PRD_Overview`. Hackathon scope: 48h MVP.

## Tech stack (2026-04 baseline)

| Layer | Choice | Version |
|---|---|---|
| Runtime | Python | 3.13+ |
| Pkg/env | uv | 0.11+ |
| API | FastAPI + uvicorn | 0.136.1 |
| Validation | Pydantic v2 | 2.13+ |
| Settings | pydantic-settings | 2.14+ |
| Logging | structlog | 25+ |
| HTTP client | httpx (async) | 0.28+ |
| Async fs | anyio | 4.7+ |
| Lint+format | ruff | 0.15+ |
| Type check | ty (Astral) | 0.0.32+ |
| Test | pytest + pytest-asyncio | 9 / 1.3 |
| Container | Docker (multi-stage, uv) | 29+ |

Do not add libraries without first comparing 2-3 alternatives in chat and getting human sign-off. The ecosystem moves fast; "the classic choice" is usually wrong.

## Layout

```
app/
  main.py              # create_app(), lifespan
  api/v1/
    router.py          # mounts feature routers
    health.py
    buildings.py
  core/
    config.py          # Settings, get_settings (lru_cache)
    logging.py         # configure_logging
  schemas/             # Pydantic response/request models, no business logic
  services/            # business logic, IO, integrations
tests/
  conftest.py          # AsyncClient fixture, dependency_overrides
  test_*.py
data/                  # raw source dataset (read-only)
schema/                # extraction prompts + WIKI_SCHEMA
output/                # building.md files (written by pipeline, served by API)
```

Rule: `api/` knows about `services/`, never the reverse. `services/` knows about external IO + `core/`. `schemas/` is leaf — imports nothing project-internal except other schemas.

## Code style (non-negotiable)

1. **`from __future__ import annotations` at the top of every `.py`** (except `__init__.py` if empty).
2. **Modern types only.** `list[str]` not `List[str]`. `X | None` not `Optional[X]`. `dict[K, V]` not `Dict`. No `typing.Tuple/List/Dict/Optional/Union` imports.
3. **Async by default for routes and IO services.** Blocking IO inside async = bug. Use `anyio` (or `asyncio.to_thread` for CPU-light blocking calls). No `requests` — `httpx.AsyncClient` only.
4. **Lifespan, not `@app.on_event`.** `on_event` is deprecated.
5. **Annotated DI.** Routes take `param: Annotated[T, Depends(provider)]`. Never bare `Depends()` in default arg.
6. **Pydantic v2 idioms.** `model_config = SettingsConfigDict(...)` / `ConfigDict(...)`. No nested `class Config`. Use `Field(default=...)`, not mutable defaults.
7. **Settings are immutable + cached.** One `get_settings()` `@lru_cache(maxsize=1)` factory. Routes get `Settings` only via `Depends(get_settings)` — never import the singleton.
8. **Structured logs only.** `log = structlog.get_logger(__name__)`. `log.info("event", key=value)`. No f-strings in log messages, no `print`.
9. **Errors raise `HTTPException`** with explicit status. Don't return error dicts.
10. **One `create_app()` factory.** Module-level `app = create_app()` is the ASGI entrypoint. No global mutation after import.
11. **Path validation at the edge.** Building IDs / user input go through Pydantic constraints (`Path(pattern=...)`, `StringConstraints`) before touching the filesystem. Never `Path(user_input)` raw.
12. **No comments stating *what*** the code does. Comment only the non-obvious *why*. Docstrings on public service classes/functions only.

## Patterns

### Adding a route

1. New module in `app/api/v1/<feature>.py` exposing `router = APIRouter()`.
2. Register in `app/api/v1/router.py` with `prefix=` and `tags=`.
3. Pydantic response model in `app/schemas/<feature>.py`.
4. Business logic in `app/services/<feature>.py` with a `get_<feature>_service()` Depends provider.
5. Test in `tests/test_<feature>.py` using the `client` fixture.

### Adding a setting

1. Field on `Settings` in `app/core/config.py` with type + default.
2. Document in `.env.example` (create when first needed).
3. Override in tests via the `settings` fixture / `dependency_overrides`.

### Adding a dependency

```bash
uv add <pkg>            # runtime
uv add --group dev <pkg> # dev/test
```

Pin a sane lower bound (`>=X.Y`). Never pin exact (`==`) except for security CVEs.

## Commands

```bash
# Install / sync env
uv sync

# Dev server (hot reload, structured console logs)
uv run fastapi dev app/main.py

# Prod-ish (no reload)
uv run fastapi run app/main.py

# Tests
uv run pytest
uv run pytest -k buildings -vv

# Lint / format / fix
uv run ruff check .
uv run ruff format .
uv run ruff check --fix .

# Types
uv run ty check
```

CI gate (when added) must run, in order: `ruff format --check`, `ruff check`, `ty check`, `pytest`.

### Docker

```bash
# Prod image (multi-stage, runs as non-root, healthcheck on /api/v1/health)
docker build -t buena-context:latest .
docker run --rm -p 8000:8000 buena-context:latest

# Compose — prod profile (default)
docker compose up --build

# Compose — dev profile (hot reload, source-mounted)
docker compose --profile dev up --build api-dev
```

Image conventions:
- Builder stage uses `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`, `uv sync --frozen --no-dev`.
- Runtime is `python:3.13-slim-bookworm`, copies only `/app/.venv` + `app/`. No uv at runtime.
- Runs as uid 1000 (`app` user). Never run as root.
- `output/` is a volume — `building.md` files persist across container restarts; never bake them into the image.
- Settings read env vars with `APP_` prefix: `APP_ENV`, `APP_LOG_LEVEL`, `APP_OUTPUT_DIR`, etc.

## Test conventions

- `pytest-asyncio` in `auto` mode — async tests don't need `@pytest.mark.asyncio`.
- HTTP tests use `httpx.AsyncClient` with `ASGITransport(app=app)`. No live network.
- Override deps via `app.dependency_overrides[get_settings] = lambda: settings` in fixture, `clear()` in teardown.
- One assertion concept per test. Use `tmp_path` for filesystem.
- Security tests: every endpoint that accepts a path/id needs a "rejects bad id" test.

## Don'ts

- No `print()` anywhere. Use structlog.
- No `requests`, `urllib`. Use `httpx`.
- No `os.path`. Use `pathlib.Path` (sync) or `anyio.Path` (async).
- No `datetime.utcnow()`. Use `datetime.now(UTC)`.
- No global mutable state. State lives behind `Depends()` providers.
- No business logic in route functions — push to `services/`.
- No silent `except: pass`. Catch narrowly, log with context, re-raise or return typed error.
- No `Any` unless boundary-justified (and `# noqa` with reason).

## When this file goes stale

If you add a pattern, drop a pattern, change a tool, or notice the rules drifting from the code: update this file *in the same PR*. Stale agent docs are worse than none.

## Pointers

- Product spec: `PRD_Overview`
- Schema / extraction: `schema/CLAUDE.md`, `schema/WIKI_SCHEMA.md`
- Raw data: `data/` (read-only)
- Plan / problem: `PLAN.md`, `PROBLEM_STATEMENT.md`, `IDEA.md`
- Container: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
