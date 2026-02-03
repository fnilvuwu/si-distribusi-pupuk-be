# SI Distribusi Pupuk Backend

FastAPI backend for Sistem Informasi Distribusi Pupuk with role-based auth (petani, admin, distributor, super_admin), stock management, jadwal distribusi, and reporting.

## Quick Start
1) Python 3.10+: create venv and activate
   - Windows: `python -m venv venv && .\venv\Scripts\activate`
2) Install deps: `pip install -r requirements.txt`
3) Copy `.env.example` to `.env` and fill DB URL, secret key, etc.
4) Initialize schema (uses `db/schema.sql`):
   - Set `AUTO_CREATE_TABLES=1` and start the app **or** run `python db/init_db.py` after configuring DB access in `.env`.
5) Run API: `uvicorn main:app --reload`
6) Docs: http://localhost:8000/docs

## Database & Seed Helpers
- Schema: `db/schema.sql`; ORM models in `db/models.py` (includes stok, riwayat stock, jadwal distribusi event/item).
- Seed scripts (optional for local data):
  - `python db/seed_dummy_data.py`
  - `python db/seed_users_profiles.py`
  - `python db/query_dummy_data.py` / `db/verify_seed.py` for quick checks.

## Tests
- Run: `python -m pytest` (uses `pytest-sugar` for the PASS/progress view).
- Config: `pytest.ini` (colors, top slow tests, warnings shown).
- Tests use in-memory SQLite with dependency overrides; no external DB required.

## Lint/Format
- Settings in `pyproject.toml` (Black, Ruff with isort profile).
- Suggested commands (if tools installed):
  - `ruff check .`
  - `black .`

## Project Layout
- `api/` FastAPI routers
- `core/` config, dependencies, utilities
- `db/` engine, models, schema, seed helpers
- `schemas/` Pydantic models
- `tests/` pytest suite
- `requirements.txt` dependencies
- `pytest.ini` pytest defaults
- `pyproject.toml` lint/format settings

## Environment
- Copy `.env.example` to `.env`; set DB connection, `SECRET_KEY`, and `AUTO_CREATE_TABLES` if you want schema auto-create on start.
