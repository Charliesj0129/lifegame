# Architecture

## Entry Points
- Line webhook: `app/api/webhook.py` receives events and routes messages through `app/services/ai_service.py`.
- Postback events: `app/api/webhook.py` dispatches quest and inventory actions.
- Daily briefing: `app/services/daily_briefing_service.py` pushes scheduled briefings.

## Core Flow
1. `AIService.router` builds context, asks the model for a tool decision, and executes through `ToolRegistry`.
2. `ToolRegistry` fans out to `user_service`, `quest_service`, and `inventory_service`.
3. `flex_renderer` builds rich responses for status, quests, and action logs.

## Persistence
- SQLAlchemy models live in `app/models/`.
- Migrations are managed by Alembic in `app/alembic/`.
- Run `python scripts/ops.py migrate` for schema upgrades.

## Operations
- Rich menus are managed via `python scripts/ops.py rich-menus`.
