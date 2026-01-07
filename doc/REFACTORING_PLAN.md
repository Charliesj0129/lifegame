# LifeGame Refactoring & Migration Plan

**From**: Azure Cloud Native (FastAPI + Postgres)
**To**: Cyborg Hybrid (Local/VPS + SQLite + Kuzu + Chroma + Tailscale)

## 1. Inventory & Analysis (The "As-Is" State)

### A. Repo Inventory
*   **Entry Point**: `app/main.py` (FastAPI app factory, router inclusion).
*   **Controller**: `app/api/webhook.py` (LINE Webhook). **[High Coupling]**
    *   Handles HTTP, Signature Auth, Token Parsing.
    *   Orchestrates Business Logic (`hollowed`, `rival`, `dispatcher`).
    *   Constructs Response Objects (`TextMessage`, `FlexMessage`).
*   **Dispatcher**: `app/core/dispatcher.py` (Command Bus).
    *   Decouples intent matching, but handlers return `linebot` specific objects.
*   **Services** (`app/services/`):
    *   `ai_engine.py`: Wrapper for OpenRouter/Gemini. Mixes prompt logic with API calls.
    *   `user_service.py`, `quest_service.py`, `hp_service.py`: Business logic + DB access.
    *   `graph_service.py`, `vector_service.py`: New hybrid components (Phase 1/2 additions).
*   **Data Layer** (`app/models/`):
    *   SQLAlchemy ORM models (`User`, `Quest`, `DDA`, `Talent`, etc.).
*   **Infrastructure**:
    *   `alembic/`: DB Migrations (Postgres focused).
    *   `deploy_azure.sh`: Azure deployment script.
    *   `install_service.sh`: New Systemd installer (Phase 3).

### B. Execution Map (Request Path)
**LINE Message Event**:
1.  **Input**: `POST /callback` -> `app.api.webhook.callback`
2.  **Auth**: `x-line-signature` validation.
3.  **Session**: `async with AsyncSessionLocal()`.
4.  **User Loading**: `user_service.get_or_create_user(session, user_id)`.
5.  **interceptors**:
    *   Check `is_hollowed` -> `hp_service.trigger_rescue`.
    *   Check `rival_encounter` -> `rival_service.process`.
6.  **Dispatch**: `dispatcher.dispatch(session, text)`.
    *   Matches strategy (Regex/Exact) -> Calls Service -> Returns `TextMessage`.
    *   Fallback: AI Router (`ai_engine`) -> Returns `TextMessage`.
7.  **Response**: `line_bot_api.reply_message(reply_token, messages)`.

### C. Coupling Report
| Module | Coupled With | Risk |
| :--- | :--- | :--- |
| `app/api/webhook.py` | `linebot.*` | Cannot easily swap to Home Assistant/Discord without duplicating logic. |
| `app/core/dispatcher.py` | `linebot.messaging.TextMessage` | Handlers return LINE-specific UI objects, making core logic channel-dependent. |
| `app/services/*.py` | `sqlalchemy.ext.asyncio.AsyncSession` | Business logic hard-coded to SQL DB. Hard to swap to file-based or in-memory for tests. |
| `app/models/*.py` | `app.core.database.Base` | Data models are tightly bound to ORM. |

### D. Risks
*   **State Split**: Migrating Postgres -> SQLite means strictly strictly defining the "Source of Truth".
*   **Dependency Hell**: `line-bot-sdk` is pervasive. Removing it from Domain requires creating generic `Message` / `Event` DTOs.
*   **Migration**: `alembic` is tailored for Postgres. SQLite `ALTER TABLE` support is limited; migrations might break.
*   **Concurrency**: Local SQLite has lower write concurrency than Azure Postgres. `AsyncSession` helps, but locking might occur.

---

## 2. Target Architecture (The "To-Be" State)

Adopting **Clean Architecture** (Hexagonal) to enforce separation of concerns.

### Directory Structure
```
lifgame/
├── domain/                 # [PURE PYTHON] No external libs (SQLAlchemy, LineBot)
│   ├── models/             # Data Classes (User, Quest, Event)
│   ├── events/             # Domain Events (UserLeveledUp, QuestCompleted)
│   ├── ports/              # Interfaces (Repositories, Gateways)
│   └── rules/              # Game Rules (XP formulas, HP logic)
├── application/            # [ORCHESTRATION] Use Cases
│   ├── handlers/           # Command Handlers (HandleMessage, CompleteQuest)
│   └── services/           # Application Services (GameEngine, Scheduler)
├── adapters/               # [INFRASTRUCTURE] Implementations
│   ├── perception/         # Input Adapters
│   │   ├── line_adapter/   # Webhook -> GameEvent
│   │   └── ha_adapter/     # HA Payload -> GameEvent
│   ├── persistence/        # Storage Adapters
│   │   ├── sqlite/         # SQLAlchemy implementation
│   │   ├── chroma/         # Vector Memory
│   │   └── kuzu/           # Graph Memory
│   ├── cognition/          # AI Adapters (Gemini, OpenAI)
│   └── notifications/      # Output Adapters (LineBot, Push)
├── api/                    # [ENTRY POINTS] REST, CLI
│   ├── routers/            # FastAPI Routes
│   └── dependencies.py     # DI Container
└── tests/                  # Strategy
    ├── unit/               # Domain tests
    ├── integration/        # Adapter tests
    └── e2e/                # API tests
```

### Layer Boundaries
1.  **Domain**: Knows NOTHING about the outer world.
2.  **Application**: Knows Domain and Interfaces.
3.  **Adapters**: Implements Interfaces, depends on external libs.
4.  **API**: Wires everything together (Dependency Injection).

---

## 3. Migration Strategy (Strangler Fig)

### Phase 1: Abstraction (The "Interface" Layer)
**Goal**: Decouple `webhook.py` from specific implementations without changing behavior.
1.  Define `PerceptionPort` (Receive Input) and `NotificationPort` (Send Output).
2.  Create `GameEvent` DTO (Generic event object).
3.  Refactor `dispatcher` to return `GameResult` (Generic data) instead of `TextMessage`.
4.  Create `LineAdapter` to convert `GameResult` -> `TextMessage`.

### Phase 2: Storage Switch (Postgres -> SQLite)
**Goal**: Enable fully local operation.
1.  Modify `Settings` to allow easy toggle `DB_TYPE=sqlite`.
2.  Ensure `alembic` works for SQLite (or use `Base.metadata.create_all` for local).
3.  Create Data Migration Script: Dump Azure Postgres -> Load Local SQLite.

### Phase 3: Local Memory (Chroma & Kuzu Integration)
**Goal**: deeply integrate the new "Cyborg" organs.
1.  Refactor `BrainService` to implement `CognitionPort`.
2.  Inject `VectorPort` and `GraphPort` into `BrainService`.

### Phase 4: Perception Expansion (HA + Tasker)
**Goal**: Enable "Real Life" events.
1.  Implement `HAAdapter` mapping HA Webhooks -> `GameEvent`.
2.  Route these events through the same `Application` layer as LINE.

---

## 4. Data Migration Strategy

### Postgres -> SQLite
*   **Tool**: Custom Python script using `sqlalchemy`.
*   **Logic**:
    1.  Connect to Postgres (Azure).
    2.  Read all `User`, `Quest`, `Log` records into Pydantic models.
    3.  Connect to SQLite (Local).
    4.  Bulk Insert.
*   **ID Handling**: Keep generic UUIDs or Strings. SQLite `ROWID` is hidden.

### Vector Data
*   **Re-indexing**: Since we are moving context, it's best to **re-embed** critical logs (Logs/Memories) from the SQL database into ChromaDB upon initialization if empty.

### Graph Data
*   **Seeding**: Run a "Seed" script to populate basic Ontology (Nodes: Concept, Location).
*   **Migration**: Scan `Logs` table for keywords to retroactive create some edges (Optional).

---

## 5. Security & Network (Cyborg Hybrid)

*   **Tailscale**:
    *   Use **Tailscale Funnel** for public ingress (LINE Webhook).
    *   Use **Tailnet** (Private IP) for Home Assistant & Phone.
*   **Authentication**:
    *   **LINE**: `X-Line-Signature` (Existing).
    *   **HA/Tasker**: Add `X-LifeGame-Token` (Shared Secret in `.env`).
*   **Secrets**:
    *   `.env` is git-ignored.
    *   Use `pydantic-settings` to load.

---

## 6. Legacy Code Treatment

| File/Module | Strategy | Action |
| :--- | :--- | :--- |
| `app/api/webhook.py` | **Refactor** | Keep logic but delegate to `Application Layer`. Remove DB sessions & business logic. |
| `app/services/ai_engine.py` | **Wrap** | Rename to `adapters/cognition/gemini_adapter.py`. Implement `CognitionPort`. |
| `app/core/dispatcher.py` | **Deprecate** | Replace with new `application/mediator.py`. |
| `app/services/line_bot.py` | **Keep** | Move to `adapters/notifications/line_adapter.py`. |
| `app/models/*.py` | **Keep (Temporary)** | Keep during Phase 1/2. In Phase 3, replace with Domain Entities + Repository. |
| `deploy_azure.sh` | **Keep** | Maintain for "Cloud Native" fallback until Cyborg is fully stable. |

