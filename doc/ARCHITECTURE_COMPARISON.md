# Architecture Decision Record: Embedded Trinity vs. API-First Ecosystem

## 1. Context
We are evaluating two distinct architectural approaches for the "LifeGame" system:
1.  **Embedded Trinity (Local-First)**: Self-hosted, offline-capable, $0 cost, relying on In-Process libraries (SQLite, KuzuDB, Ollama).
2.  **API-First Ecosystem (Cloud-Native)**: Managed services, always-online, freemium, relying on APIs (Supabase, Neo4j Aura, Cloud LLMs).

## 2. Comparison Matrix

| Feature | **Embedded Trinity (Local)** | **API-First (Cloud)** |
| :--- | :--- | :--- |
| **Philosophy** | "I own the atoms." (Sovereignty) | "I rent the best." (Convenience) |
| **Connectivity** | 🔴 **Broken** (Requires VPN/Tunnel for Mobile) | 🟢 **Solved** (Public APIs accessible everywhere) |
| **Maintenance** | 🟡 **Medium** (Backup scripts, Hardware monitoring) | 🟢 **Low** (No server patching, Auto-backups) |
| **Privacy** | 🟢 **Absolute** (Data stays on disk) | 🟡 **Trusted 3rd Party** (Data on Supabase/OpenAI) |
| **Cost** | 🟢 **$0** (CapEx only) | 🟡 **Variable** (Freemium limits, Token costs) |
| **Downtime Risk** | Power outage / ISP fail | "Free Tier Pausing" (Neo4j/Supabase sleep) |
| **Development** | Python Heavy (Pydantic, SQLAlchemy) | Integration Heavy (Webhooks, JSON wrangling) |

## 3. Deep Dive: API-First Risks

### A. The "Sleep" Problem (Cold Starts)
Both Supabase (Free) and Neo4j Aura (Free) have aggressive "pausing" policies for inactive projects.
*   **Supabase**: Pauses after 1 week of inactivity.
*   **Neo4j Aura**: Pauses after 3 days of inactivity.
*   **Impact**: If you don't engage with your LifeOS for a few days (e.g., vacation), your "Brain" shuts down. Waking it up takes minutes and might fail your first API call.

### B. Latency Stacking
In `Embedded Trinity`, query latency is microseconds (RAM/Disk).
In `API-First`, a single "Concept" might involve:
1.  Tasker -> Internet -> FastAPI (Azure) [200ms]
2.  FastAPI -> Supabase (Auth/DB) [100ms]
3.  FastAPI -> Neo4j Aura (Graph) [150ms]
4.  FastAPI -> Anthropic (LLM) [1-3s]
*   **Total**: ~2-4 seconds per interaction. This feels "sluggish" compared to instant local processing.

### C. Vendor Lock-in
*   **Supabase**: While Postgres is standard, their `Realtime` and `Auth` are specific to their platform.
*   **Neo4j**: Cypher is standard, but the driver and connection details for Aura are specific.
*   **Tasker**: Android only. Hardlock on Android.

## 4. Recommendation

**Choose "Embedded Trinity" if:**
*   You prioritize **Privacy** and **Archive** (game.db forever).
*   You enjoy **Systems Engineering** (Linux, Networking).
*   You want **Instant Response** (Low latency).

**Choose "API-First" if:**
*   You prioritize **Mobile Access** (Works on 4G immediately).
*   You hate **DevOps** (Docker management, Backups).
*   You want **SOTA Intelligence** (Claude 3.5 Sonnet is smarter than local Llama 3).

## 5. Proposed Hybrid Path (The "Cyborg" Approach)

Do not go 100% one way.
1.  **Core**: Keep **FastAPI** + **Postgres/SQLite** (Local or VPS) for sovereignty.
2.  **Brain**: Use **Cloud LLMs** (Claude/Gemini) because local LLMs are resource hogs.
3.  **Graph**: Use **KuzuDB** (Local) because Neo4j Free Tier limits are too tight (nodes count) and the "Sleep" issue is annoying for a 24/7 service.
4.  **Sync**: Use **Tailscale** for easy mobile connectivity.
