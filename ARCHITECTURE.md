# AI-Native Architecture Overview

This document outlines the architecture of the **LifeGame** system, emphasizing its AI-Native design where core logic is driven by LLMs and an AI Router.

## 1. High-Level Overview

The system is a Python API (FastAPI) acting as a backend for a LINE Messaging Bot. It integrates gamification elements (Quests, Inventory, Rivals) with an AI engine that personalizes content and handles complex user intents.

### Core Components
- **Interface**: LINE Messaging API (Webhook).
- **Backend**: FastAPI (Python 3.12).
- **Database**: PostgreSQL (SQLAlchemy ORM + AsyncPG).
- **AI Engine**: Google Gemini (via `google-generativeai`).
- **Deployment**: Azure App Service (Docker Container).

---

## 2. Key Modules & Data Flow

### 2.1 Webhook & Router
Incoming messages flow through the **AI Router**, which determines the intent before dispatching to specific services.

```mermaid
graph TD
    User[User (LINE)] -->|Message| Webhook[Webhook Handler]
    Webhook -->|Text| AIRouter[AI Router (ai_service)]
    
    AIRouter -->|Intent: QUEST| QuestService
    AIRouter -->|Intent: INVENTORY| InventoryService
    AIRouter -->|Intent: STATUS| FlexRenderer
    AIRouter -->|Intent: CHAT| AIEngine[Gemini Chat]
    
    QuestService --> DB[(PostgreSQL)]
    InventoryService --> DB
```

### 2.2 Core Services

*   **AI Router (`app/services/ai_service.py`)**: The brain of the system. It classifies user input (e.g., "Give me a quest" vs "I ate an apple") and routes it. It can also extract structured data (e.g., "Gym 1 hour" -> `ActionLog(STR, +10 XP)`).
*   **Quest Service (`app/services/quest_service.py`)**: Manages Daily Quests and Long-term Goals. Uses AI to generate personalized quests and decompose goals into milestones.
*   **Inventory Service (`app/services/inventory_service.py`)**: Handles Item usage, Loot drops, and Buff application.
*   **Rival Service (`app/services/rival_service.py`)**: Manages the "Rival" system, generating dynamic commentary and "Boss Mode" challenges based on user progress.

### 2.3 Data Models

*   **User**: Core entity (`stats`, `level`, `xp`, `class`).
*   **Quest**: Tasks with `difficulty`, `status`, `xp_reward`.
*   **Goal**: Long-term objectives decomposed into milestones.
*   **Item/UserItem**: Inventory system.
*   **ActionLog**: Historical log of user activities and gains.

---

## 3. Deployment Architecture (Azure)

The application runs as a stateless Docker container on Azure App Service.

*   **Compute**: Azure App Service (Plan B1).
*   **Database**: Azure Database for PostgreSQL (Flexible Server).
*   **Configuration**: Environment variables (connection strings, API keys) managed via App Service Settings.
*   **Migrations**: Alembic (run via `python migrate_*.py` during deployment/startup).

## 4. Testing Strategy

Refactored into specific domains:
*   `tests/test_core_mechanics.py`: User stats, Accountancy, Webhook/Router logic.
*   `tests/test_quest_system.py`: Quest generation, completion, and AI fallback logic.
*   `tests/test_inventory_system.py`: Item usage, buff logic, loot drops.
