# LINE 互動流程

## 入口
- `POST /callback`：所有 LINE 事件進入點
- 事件類型：Text / Image / Location / Postback / Follow

## 文字訊息流程（Text）
1. 觸發 Loading Animation（可關閉）
2. 快速指令分支（狀態/任務/背包/商店/合成/首領/攻擊/指令）
3. 文字驗證分支：
   - 自動比對任務 `verification_service.auto_match_quest`
   - 通過後 `verification_service.verify_text` → 完成任務
4. AI Router 分支：
   - `AIService.router` → ToolRegistry → Service → 回覆

## 圖片/位置驗證
- 圖片：`handle_image_message` → `verification_service.process_verification`
- 位置：`handle_location_message` → `verification_service.process_verification`

## Postback（按鈕）
- `action=reroll_quests`：重新生成
- `action=complete_quest`：手動完成
- `action=check_habit`：習慣打卡
- `action=buy_item` / `action=craft`
- `action=strike_boss`

## Follow
- 建立使用者
- 綁定 Rich Menu

## 回覆型態
- TextMessage
- FlexMessage
- Audio（升級、簡報）

## 保留關鍵字（避免誤入 Router）
- `狀態` `任務` `背包` `商店` `合成` `首領` `攻擊` `指令`
