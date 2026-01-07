# 架構總覽

本文件是 LifeGame/LifeOS 的架構入口，提供整體視角與擴展點索引。細節請見各子文件。

## 系統邊界
- LINE Messaging API Webhook：`app/api/webhook.py`
- API 服務：FastAPI（Python 3.12）
- 資料庫：PostgreSQL（SQLAlchemy + AsyncPG）
- AI 供應商：OpenRouter / Gemini
- 部署：Azure App Service（Linux Container）

## 主要流程（摘要）
1. Webhook 收到訊息（文字/圖片/位置/按鈕）
2. 先走快速指令或驗證分支（狀態、任務、背包、首領等）
3. 未命中時進入 AI Router（`app/services/ai_service.py`）
4. ToolRegistry 執行實際服務邏輯
5. Flex Renderer 組裝回覆（Text/Flex/Audio）

## 模組分層
- API 層：`app/api/*`
- 服務層：`app/services/*`
- 模型層：`app/models/*`
- 視覺輸出：`app/services/flex_renderer.py`、`assets/*`
- Ops：`scripts/*`

## 擴展點
- 新工具：在 `ToolRegistry` 增加對應方法，並更新 AI Router 的工具描述。
- 新驗證模式：擴充 `verification_service` 與任務欄位（`verification_type`）。
- DDA：以 `habit_states`/`daily_outcomes` 為核心資料，接上排程推播。
- 世界觀/敘事：擴充 `lore_service` 與回覆模板。

## 相關文件
- `doc/DATA_MODEL.md`
- `doc/LINE_FLOW.md`
- `doc/OPS_RUNBOOK.md`
- `doc/RICH_MENU.md`
- `doc/ROADMAP.md`
