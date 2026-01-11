# 🌃 LifeGame：賽博人生 OS

> 把日常任務變成可被追蹤、可被獎勵、可被對抗的「人生 RPG」。

**LifeGame** 是一個 Line Bot + Web Dashboard 的生活遊戲化系統：它會理解你的自然語言、判斷意圖、拆解目標、派發今日可完成任務，並用對手 AI、掉寶、Boss、副本、天賦來維持動機循環。

![LifeGame UI](https://via.placeholder.com/1200x640?text=LifeGame+Dashboard)

## ⚡ 核心特色

### 🧠 AI Core（意圖路由 + 記憶）
- **自然語言解析**：輸入「我跑了 5 公里」→ 自動記錄為任務進度。
- **意圖路由器**：依上下文呼叫工具（狀態、背包、任務、用道具、目標設定）。
- **對話記憶**：短期對話歷史納入判斷，提高一致性。
- **繁體中文全域輸出**：系統訊息與 UI 全面繁中化。

### 🎯 目標系統（Goals / Quests）
- **長期目標不壓迫**：目標存檔、任務可完成（30–60 分內）。
- **自動拆解**：長期目標輸入後，AI 生成 3 個可立即執行的微任務。
- **每日任務批次**：依 DDA 時間盒動態派發。

### 📈 DDA（Dynamic Difficulty Adjustment）
- **A 門檻**：Green ≥ 0.85、Red < 0.60。
- **時間盒層級**：T0 微型 / T1 輕量 / T2 標準 / T3 深度。
- **避免震盪**：採 EMA 平滑 + 連續 2 天同區才調整。

### 💀 對手系統（Viper）
- **主動壓力**：長期未行動會遭竊取經驗/金幣。
- **病毒植入**：對手高於你等級時附加 Debuff。
- **Boss 模式**：等級差過大時強制 Boss 任務解除封鎖。

### ✅ 驗證機制
- **文字 / 圖片 / GPS 驗證**：任務完成可多模態驗證。

### 🏠 Cyborg Nerves (Home Assistant)
- **IoT 事件感知**：整合 Home Assistant Webhooks，感知手機開關螢幕、運動、睡眠等真實生活事件。
- **語意理解**：自動將 IoT 訊號轉換為對應的遊戲概念（如：Screen Off -> 自律）。

### 🕸️ Graph Memory (KuzuDB)
- **社交圖譜**：紀錄玩家與 NPC 的互動歷史。
- **事件關聯**：追蹤行為模式與偏好，讓 NPC 反應更具個性化 (Viper, Sage, Ember, Shadow)。

---

## 🚀 快速開始

### 前置需求
- Python 3.10+
- LINE Messaging API（Channel Secret / Token）
- OpenRouter 或 Google Gemini API Key

### 安裝

1. **Clone 專案**
   ```bash
   git clone https://github.com/Charliesj0129/lifegame.git
   cd lifgame
   ```

2. **設定環境變數**（`.env`）
   ```ini
   LINE_CHANNEL_ACCESS_TOKEN=your_token
   LINE_CHANNEL_SECRET=your_secret

   # AI Keys
   OPENROUTER_API_KEY=your_key
   OPENROUTER_MODEL=google/gemini-2.0-flash-thinking-exp

   # Database
   DATABASE_URL=sqlite+aiosqlite:///./test.db

   # Ops（選用）
   AUTO_MIGRATE=0
   ```

3. **安裝依賴**
   ```bash
   uv sync --frozen --dev
   ```

4. **啟動服務**
   ```bash
   uvicorn app.main:app --reload
   ```

### 資料庫 Migration
```bash
python scripts/ops.py migrate
```

### Rich Menu（選用）
```bash
python scripts/ops.py rich-menus
```

---

## ☁️ Azure 部署

本專案已針對 **Azure App Service (Linux Container)** 調整：
- `pool_size=3`（低資源安全）
- `pool_recycle=300`（避免閒置斷線）
- `AUTO_MIGRATE=1`（啟動自動 Migration）

### 快速部署
請參考 `deploy_azure.sh`（完整一鍵建置）。

### 必要 App Settings
- `DATABASE_URL`
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `OPENROUTER_API_KEY` / `OPENROUTER_MODEL`
- `WEBSITES_PORT=8000`
- `AUTO_MIGRATE=1`

---

## 🧪 測試
```bash
uv run pytest -q
```

---

## 📂 專案結構
```
lifgame/
├── app/
│   ├── api/            # Webhook / Dashboard API
│   ├── core/           # Config / DB
│   ├── models/         # SQLAlchemy Tables
│   ├── services/       # AI / DDA / Rival / Quests
│   ├── templates/      # Dashboard HTML
│   └── schemas/        # Pydantic Models
├── doc/                # 設計文檔
├── scripts/            # ops.py (migrate / rich-menus)
└── README.md
```

---

## 📚 文件索引
- `doc/architecture.md`
- `doc/DATA_MODEL.md`
- `doc/LINE_FLOW.md`
- `doc/OPS_RUNBOOK.md`
- `doc/RICH_MENU.md`
- `doc/ROADMAP.md`

---

## 📜 License
MIT License. Hack the planet.
