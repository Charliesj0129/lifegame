# Phase 1 Strategy: Cyborg Hybrid Migration (Preparation)

## 0. Goal & Invariants
**Goal**: Structure the optimization of LifeGame to support a "Cyborg Hybrid" architecture (Local Core + Cloud Cognitive) without breaking the existing "Azure Cloud Native" behavior.
**Invariants**:
- [x] **LINE Consistency**: External behavior (Webhooks/Replies) must remain identical.
- [x] **No "Big Bang"**: Use Strangler Fig pattern; abstract first, switch later.
- [x] **Pure Domain**: No `FastAPI`, `SQLAlchemy`, or `LINE SDK` in `domain/`.
- [x] **Reversibility**: All changes feature-flagged or interface-switched.
- [x] **Organization First**: Phase 1 is strictly structural (Boundaries & Tests), no Infra migration.

---

## 1. Reports

### A. Repo Inventory
| Component | Key Files | External Dependencies |
| :--- | :--- | :--- |
| **Entry Points** | `app/main.py`, `legacy/webhook.py` | `FastAPI`, `Uvicorn` |
| **Perception** | `legacy/webhook.py`, `app/api/nerves.py` | `line-bot-sdk`, `pydantic` |
| **Core Logic** | `app/core/dispatcher.py`, `app/services/*` | `google-genai` (Gemini), `sqlalchemy` |
| **Models** | `app/models/user.py`, `app/models/gamification.py` | `sqlalchemy` (ORM) |
| **Infra** | `app/core/database.py`, `app/core/config.py` | `asyncpg`, `aiosqlite` |

### B. Execution Map (Legacy Golden Path)
**Flow**: `POST /callback` (LINE) -> `User Reply`
1.  **Entry**: `webhook.callback` verifies signature.
2.  **Dispatch**: `webhook_handler.handle(body)` parses JSON events.
3.  **Handler**: `handle_message(MessageEvent)` triggered.
4.  **Logic (Mixed)**:
    *   `user_service.get_or_create_user` (DB Write).
    *   `rival_service.process_encounter` (DB/Logic Mixed).
    *   `dispatcher.dispatch` (Service Routing).
5.  **View**: `flex_renderer` generates JSON/Dict.
6.  **Response**: `messaging_api.reply_message` sends HTTP req to LINE.

### C. Coupling Report
**High Risk Areas**:
1.  **`legacy/webhook.py`**:
    *   **Mixed Concerns**: Handles HTTP, Parsing, DB Transaction Management, *and* Game Logic (Rival/HP checks).
    *   **Deep Coupling**: Imports services (`persona`, `audio`, `quest`) directly.
2.  **`app/core/dispatcher.py`**:
    *   Acts as a Service Locator but returns tuples/mixed types, causing tight coupling with the receiver.
3.  **`app/services/`**:
    *   Services often import `app.core.database` directly, making them hard to test without a DB.

### D. Risk List
1.  **Webhook Idempotency**: `handle_message` has side effects (HP deduction, XP gain) but no idempotency key check. Retries will duplicate rewards/penalties.
2.  **Transaction Scope**: Explicit `AsyncSessionLocal` in handler is manual; risk of uncommitted/orphaned transactions if exceptions occur outside the try/except block.
3.  **State Consistency**: Rival logic updates DB *before* message dispatch. If dispatch fails, Rival state (cooldowns) might still advance.

---

## 2. Target Architecture

### Repo Tree
```text
/
├── domain/                  # PURE LOGIC (No I/O)
│   ├── models/             # Data Classes (GameEvent, Quest, UserState)
│   ├── rules/              # Scoring, XP curves, State Machines
│   └── ports/              # Abstract Interfaces (Repositories, Gateways)
├── application/             # USE CASES
│   ├── services/           # PerceptionService, GameEngine, Scheduler
│   └── dtos/               # Data Transfer Objects
├── adapters/                # I/O IMPLEMENTATIONS
│   ├── perception/         # line_bot_adapter.py, ha_adapter.py (Webhooks)
│   ├── persistence/        # sqlalchemy/repo.py, kuzu/adapter.py
│   └── cognition/          # gemini_client.py
├── api/                     # FASTAPI (Routers)
│   ├── v1/                 # REST Endpoints
│   └── dependencies.py     # DI Wiring
├── infra/                   # CONFIG & SCRIPTS
│   ├── config.py
│   └── docker/
└── tests/                   # TESTS
    ├── unit/               # Domain testing
    └── integration/        # Adapter/Flow testing
```

### Dependency Rules
*   **Domain**: Depends on NOTHING.
*   **Application**: Depends on `Domain`.
*   **Adapters**: Depends on `Application` (execution) and `Domain` (types).
*   **API**: Depends on `Application` (use cases) and `Adapters` (wiring).
*   **Infra**: Depends on All (configuration).

---

## 3. Phase 1: Organization & Preparation

### Plan Overview
We will not rebuild the DB yet. We will "strangle" the confusing `webhook.py` by wrapping it in a clean Adapter -> Application flow.

### PR 1: The Skeleton & Ports
**Goal**: Establish clear boundaries.
1.  Create `domain/rules`, `application/use_cases`.
2.  Define Protocols in `domain/ports`:
    *   `MessagingPort` (send_reply)
    *   `PersistencePort` (get_user, save_user)
3.  **DoD**: No functional change. Empty directories created. Interfaces defined.

### PR 2: Domain Extraction (Safe)
**Goal**: Move pure logic out of `webhook.py`.
1.  Extract `Rival` encounter logic to `domain/rules/rival_rules.py`.
2.  Extract `HP` calculation to `domain/rules/health_rules.py`.
3.  Write Unit Tests for these Rules.
4.  **DoD**: Tests pass. `webhook.py` imports these rules instead of hardcoded `if`.

### PR 3: Adapter Pattern for LINE
**Goal**: Decouple FastAPI/LINE-SDK from Logic.
1.  Create `adapters/perception/line_client.py` implementing `PerceptionPort`.
2.  Move `handle_message` parsing logic here.
3.  Make `legacy/webhook.py` a thin router that calls `LineClient.handle_request()`.
4.  **DoD**: Webhook still works. CI passes contract test.

### PR 4: Application Layer Orchestration
**Goal**: Centralize flow.
1.  Create `application/services/game_loop.py`.
2.  Move the "Rival -> Dispatch -> Reply" sequence from `webhook.py` to `GameLoop.execute()`.
3.  **DoD**: `webhook.py` becomes just `await game_loop.execute(event)`.

---

## 4. Phase 1 Execution Details

### File Signatures (Draft)

**`domain/ports/messaging.py`**
```python
from typing import Protocol
from domain.models.game_result import GameResult

class MessagingPort(Protocol):
    async def send_reply(self, token: str, result: GameResult) -> bool:
        ...
```

**`application/use_cases/process_line_event.py`**
```python
from domain.ports.messaging import MessagingPort
from domain.ports.persistence import Repository

class ProcessLineEvent:
    def __init__(self, repo: Repository, messenger: MessagingPort):
        self.repo = repo
        self.messenger = messenger

    async def execute(self, user_id: str, text: str):
        # 1. Load User (Repo)
        # 2. Apply Domain Rules (Rival/Score)
        # 3. Save User
        # 4. Send Reply (Messenger)
        pass
```

### Reference README (Local Dev)
```bash
# Install
uv sync

# Run Tests (Domain)
uv run pytest tests/unit/domain

# Run App (Local)
uv run uvicorn app.main:app --reload

# Verify Webhook (Contract)
uv run pytest tests/contracts/test_line_parsing.py
```
