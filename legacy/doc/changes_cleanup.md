# Cleanup changes (plan C)

- Consolidated rival progression into `app/services/rival_service.py` and reused it from daily briefings.
- Removed runtime admin endpoints and replaced them with `scripts/ops.py` commands.
- Standardized database migrations on Alembic and added a core schema revision.
- Added optional auto-migration on startup (AUTO_MIGRATE).
- Fixed rich menu list handling to avoid duplicate creation.
- Removed legacy migration scripts, one-off test scripts, and duplicate rich menu tests.
- Dropped `requirements.txt` in favor of `pyproject.toml` and `uv.lock` as the single source of truth.
