# Schema Change Log

## Guidelines
- Always document new tables or column changes here.
- Run `alembic revision --autogenerate` for migrations.
- Keep `AUTO_MIGRATE=1` in .env for Dev/Staging.

---

## 2024-05-24: System Polish v1
**Added Columns:**
- `habit_states`: `ema_p` (Float), `tier` (String), `last_outcome_date` (Date).
- `quests`: `verification_type` (String, existing), `verification_keywords` (JSON, existing).

**New Features:**
- Habit EMA Tracking & Tiering.
- Time-based Quest Generation contexts.

---

## 2024-05-20: Refactoring v2
**Tables:**
- No schema changes. Structural refactor only.

## 2024-05-15: Feature 3 (DDA)
**Added Tables:**
- `habit_states`: `id`, `user_id`, `habit_tag`, `habit_name`, `current_tier`, `exp`.
- `daily_outcomes`: `id`, `user_id`, `date`, `done`.
