# Contributing to LifeGame (Cyborg Hybrid)

## Prerequisities
- Python 3.12+ (managed by `uv` or `pyenv`)
- `uv` (Universal Python Package Manager) -> `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker (Optional, only if running localized Postgres/Kuzu in container, though SQLite is default)
- Tailscale (For remote perception events)

## Getting Started (Local Dev)

1. **Install Dependencies**
   ```bash
   uv sync
   ```

2. **Environment Setup**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to set `GOOGLE_API_KEY` if you want real AI, or leave blank to use Mock/Fallback.*

3. **Database Initialization (SQLite)**
   The system defaults to Hybrid Mode (SQLite) if no Postgres credentials are found.
   ```bash
   # Initialize tables
   uv run python3 scripts/init_db.py
   ```

4. **Run Server**
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   Open http://localhost:8000/docs to see the Swagger UI.

## Architecture Guidelines
This project follows **Clean Architecture**:
- **`domain/`**: Pure logic. NO imports from `app/` or external libs (except Pydantic).
- **`adapters/`**: Where `linebot`, `sqlalchemy`, `google-genai` live.
- **`application/`**: Use cases that wire Domain and Adapters.

## Testing
We use `pytest`.
```bash
uv run pytest tests/
```
