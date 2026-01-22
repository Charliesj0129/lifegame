---
name: verify-project-health
description: Performs a comprehensive health check of the LifeOS project, including Database Schema, Critical Unit Tests, and Behavioral Logic integrity.
---

# Verify Project Health Skill

This skill runs a deep audit of the project to ensure functional and architectural integrity.

## Usage

Run this skill whenever you need to confirm the project state, especially after major refactors or before deployment.

## Steps

1.  **Database Migration Status**
    - Checks if the Alembic `head` is consistent with the current codebase.
    - Run: `uv run alembic current && uv run alembic history --verbose | head -n 20`

2.  **Critical Logic Verification**
    - Runs a targeted subset of unit tests focusing on the "Brain" and "Rules" modules.
    - Run: `uv run pytest tests/unit/test_flow_controller.py tests/unit/domain/test_rules.py -v`

3.  **Process Health Check**
    - Checks for lingering debug processes or stale services.
    - Run: `ps aux | grep "uv run python" | grep -v grep`

4.  **Behavioral Integrity Check**
    - **Narrator Context**: Verify `narrator_service.py` fetches `recent_performance`.
    - **Immediate Feedback**: Verify `immediate_responder.py` is actively called in `main.py`.
    - **Multi-Objective**: Verify `QuestService` uses `_calculate_diversity_score`.

5.  **Synergy Verification (Phase 4)**
    - Verifies the rigorous interaction between PID, Narrator, Fogg, and AI Director.
    - Run: `uv run pytest tests/system/test_behavioral_synergy.py -v`


## Output
Review the output of the commands. 
- If Alembic is not at `head`, run `uv run alembic upgrade head`.
- If tests fail, Fix immediately (P0).
- If Behavioral Integrity checks fail (via `grep` or manual review), mark functions as "Latent/Broken".
