# 🌃 LifeGame: Cyberpunk LifeOS

> *The street finds its own uses for things. Turn your life into a game.*

**LifeGame** is a Line Bot application that gamifies your daily habits using Generative AI (Gemini/OpenAI) and RPG mechanics. It acts as a "LifeOS" neuro-implant, analyzing your text logs and converting them into Experience Points (XP), Attributes (STR/INT/VIT), and Loot.

![Cyberpunk UI](https://via.placeholder.com/800x400?text=LifeGame+Interface+Placeholder)

## ⚡ Features

### 🧠 AI Core (LifeOS)
-   **Natural Language Processing**: Logs like "Ran 5km in the rain" are analyzed for context.
-   **Dynamic Attributes**: Automatically categorizes actions into **STR** (Strength), **INT** (Intelligence), **VIT** (Vitality), **WIS** (Wisdom), or **CHA** (Charisma).
-   **Reasoning Model**: Uses advanced models (`gemini-2.0-flash-thinking`) to determine difficulty tiers (E to S rank).
-   **Cyberpunk Persona**: Responses are immersive, styled as a futuristic OS interface.

### 🎮 Gamification Mechanics
-   **🔥 Visual Streaks**: Tracks consecutive daily activity with immediate visual feedback.
-   **🪪 Identity Titles**: Evolve from "Runner" to "Street Samurai" as you level up.
-   **⚔️ Difficulty Scaling**: Harder tasks grant exponentially more XP.
-   **🎁 Loot System**: 20% chance to drop "Cyberware" or "Buffs" (e.g., *Synaptic Booster*, *Small XP Potion*) on action logs.

### 🛠 Technical Architecture
-   **Backend**: Python (FastAPI) + Uvicorn.
-   **Database**: PostgreSQL / SQLite (Async SQLAlchemy).
-   **AI Provider**: OpenRouter (OpenAI Compatible) / Google Gemini API.
-   **Messaging**: Line Messaging API (Flex Messages).
-   **Cloud**: Optimized for Azure App Service (Linux Web App).

---

## 🚀 Getting Started

### Prerequisites
-   Python 3.10+
-   A Line Developer Account (Message API Channel)
-   OpenRouter or Google Gemini API Key

### Installation

1.  **Clone the Repo**
    ```bash
    git clone https://github.com/Charliesj0129/lifegame.git
    cd lifegame
    ```

2.  **Environment Setup**
    Create a `.env` file:
    ```ini
    LINE_CHANNEL_ACCESS_TOKEN=your_token
    LINE_CHANNEL_SECRET=your_secret
    
    # AI Keys
    OPENROUTER_API_KEY=your_key
    OPENROUTER_MODEL=google/gemini-2.0-flash-thinking-exp
    
    # Database
    SQLALCHEMY_DATABASE_URI=sqlite+aiosqlite:///./test.db
    ```

3.  **Install Dependencies**
    We use `uv` for fast package management, or standard pip:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run Locally**
    ```bash
    uvicorn app.main:app --reload
    ```

---

## ☁️ Deployment (Azure)

This project is tuned for **Azure App Service (Linux, Free Tier)**.

### Optimizations Included
-   **Connection Pooling**: `pool_size=3` to prevent memory exhaustion on small instances.
-   **Keep-Alive**: `pool_recycle=300` to bypass Azure Load Balancer idle timeouts.
-   **Startup Migration**: Automatically patches database schema on container startup.

### Deploy Command
```bash
az webapp up --runtime "PYTHON:3.10" --sku F1 --name <your-app-name>
```

---

## 📂 Project Structure

```
lifgame/
├── app/
│   ├── api/            # Webhook & API Endpoints
│   ├── core/           # Config & Database logic
│   ├── models/         # SQLAlchemy Tables (User, Items, Streaks)
│   ├── services/       # Business Logic (AI, Accountant, Inventory)
│   └── schemas/        # Pydantic Models
├── doc/
│   └── rules_of_the_world.md # The "Bible" for the AI's logic
├── scripts/
│   └── setup_rich_menu.py # Line Rich Menu Uploader
└── main.py             # Entry point
```

## 📜 License
MIT License. Hack the planet.
