# Roadmap（後續擴展）

## 1. 驗證系統補完
- 文字/圖片/位置多模態一致化
- 任務驗證結果與回覆模板統一

## 2. DDA 任務生成與推播
- 每日排程生成（Morning/Midday/Night）
- EMA 成功率與 Tier 調整

## 3. 世界觀擴展
- Lore 解鎖
- HP / Hollowed 狀態與救援邏輯

## 4. 觀測與延遲簡化
- 移除 `print` 型 latency log（改為 logger + env 開關）
- 可選停用 `show_loading_animation`
- 統一錯誤回覆與追蹤格式

## Phase 5｜品質門檻
- CI Gate：核心流程測試必過（狀態/任務/背包/首領/驗證）
- Pre-deploy 檢查：環境變數、DB migration、靜態資產、Line Token
- Post-deploy Smoke：`/health`、模擬 `/callback`（預期 400/Invalid signature）
- 發版阻擋規則：測試或 smoke 未過 → 中止上線
- 變更守門：有 DB/規則/PROMPT 變更需附回滾說明

## 6. 文件與資料治理
- 核心規則與 Prompt 版本化
- Schema 變更記錄與遷移規範化

---

# BDD 規格草案（部分完成 / 尚未實作）

## Feature: 驗證系統多模態一致化

### Scenario: 文字回報模糊時要求補充
- Given 使用者有一個需要文字驗證的任務「晨跑 5 公里」
- When 使用者回報「剛跑完步，流了一身汗」
- Then 系統判定為 `UNCERTAIN`
- And 回覆統一模板「🤔 收到回報，請補充：今日里程數是多少？」

### Scenario: 圖片不符合任務
- Given 使用者有一個圖片驗證任務「吃一頓健康午餐」
- When 使用者上傳一張「電腦螢幕」照片
- Then 系統判定為 `REJECTED`
- And 回覆「❌ 驗證失敗：此圖片不符合健康午餐」

### Scenario: 位置驗證成功
- Given 使用者有一個位置驗證任務「到健身房打卡」
- And 任務半徑為 100m
- When 使用者上傳位置距離目標 50m
- Then 系統判定為 `APPROVED`
- And 回覆「✅ 任務完成！+XP（判定：抵達目標範圍）」

## Feature: DDA 任務生成與推播（A 門檻）

### Scenario: Morning 生成 3 任務 + 2 打卡
- Given 使用者當日尚無任務
- When Morning 排程啟動
- Then 系統生成 3 個任務與 2 個打卡項目
- And 任務與打卡內容皆為繁體中文

### Scenario: EMA 落入 Red 降階
- Given 使用者 7 日 EMA < 0.60 且連續 2 天位於 Red
- When 生成今日任務
- Then 任務難度與時間盒降一階（例如 T2 → T1）
- And 夜間推播優先提供 T0 最小任務或救援

### Scenario: EMA 進入 Green 升階
- Given 使用者 7 日 EMA >= 0.85 且連續 2 天位於 Green
- When 生成今日任務
- Then 任務難度與時間盒升一階（例如 T1 → T2）

### Scenario: Midday/Night 推播內容依 DDA 調整
- Given 使用者今日尚未完成任何任務
- When Midday 推播觸發
- Then 推送「最小一步」任務（T0/T1）與快速回覆
- And Night 推播優先「保連勝」選項與救援券

## Feature: 目標拆解代理人（長期 → 每日）

### Scenario: 長期目標拆解為精確每日任務
- Given 使用者輸入「兩個月內考到多益 800 分」
- When 系統辨識為長期目標
- Then 產生 3 個可於一天內完成的任務（≤ 60 分鐘）
- And 產生 2 個打卡習慣項目
- And 任務與習慣皆為繁體中文且含明確完成條件

## Feature: Lore 解鎖（資料磁碟）

### Scenario: 使用資料磁碟解鎖下一章
- Given 使用者背包中有 `ITEM_DATA_SHARD`
- And Lore 進度為「起源系列：2/5」
- When 使用者使用該道具
- Then 系統解鎖第 3 章並回覆 Lore 卡片
- And 道具從背包移除

## Feature: HP / Hollowed 救援流程

### Scenario: HP 歸零時強制救援任務
- Given 使用者 HP = 0 且進入瀕死狀態
- When 使用者嘗試取得高難度任務
- Then 系統拒絕並派發「緊急修復任務」
- And 完成後恢復 HP 至 10 並解除瀕死狀態

## Feature: 黑市每日刷新與稀有商品

### Scenario: 每日 00:00 刷新黑市
- Given 系統時間為 00:00
- When 黑市刷新作業執行
- Then 產生 3 個商品
- And 至少 1 個為稀有或傳說等級
- And 推播「黑市已更新」通知

### Scenario: 購買贖罪券解除懲罰
- Given 使用者處於 `PENALTY_PENDING` 且金幣足夠
- When 使用者購買贖罪券
- Then 系統扣除金幣並移除懲罰狀態

## Feature: 合成失敗與風險機制

### Scenario: 合成成功
- Given 使用者擁有合成所需素材
- When 使用者執行合成指令
- Then 消耗素材並新增產物至背包
- And 回覆「⚒️ 合成成功」

### Scenario: 合成失敗（高階）
- Given 使用者合成傳說裝備且成功率為 50%
- When 隨機結果為失敗
- Then 消耗所有素材但不產生裝備
- And 回覆「💥 實驗失敗」

## Feature: 副本（Dungeon）完整流程

### Scenario: 開啟副本並建立階段
- Given 使用者未進行中的副本
- When 使用者開啟「專注副本」120 分鐘
- Then 系統建立 3 個階段性任務並開始計時

### Scenario: 通關結算掉落保底
- Given 使用者在時限內完成所有階段
- When 副本結算
- Then 保證掉落至少 1 個 RARE 以上道具

## Feature: AI JSON 修復與降級輸出

### Scenario: AI JSON 格式錯誤自我修正
- Given AI 回傳 JSON 解析失敗
- When 系統觸發修復流程
- Then 重試一次並回傳有效 JSON
- And 若仍失敗則回退到保底模板
