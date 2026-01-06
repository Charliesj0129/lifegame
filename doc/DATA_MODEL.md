# 資料模型總覽

以下為目前核心資料表與用途摘要，方便擴展與排錯時快速定位。

## 核心帳號/行為
- `users`：玩家狀態（等級、屬性、HP、金幣、連勝等）。
- `action_logs`：行為紀錄（文字輸入 → 屬性/獎勵）。
- `goals`：長期目標（AI 拆解原始資料）。
- `quests`：每日/支線任務（難度、驗證、獎勵）。
- `rivals`：對手（Viper）狀態與等級。

## DDA（動態難度）
- `habit_states`：習慣狀態（tier、EMA 成功率、連續天數）。
- `daily_outcomes`：每日結果（habit/global、完成與救援券）。
- `completion_logs`：完成記錄（來源、使用的 tier、時長）。
- `push_profiles`：推播時間偏好。

## 經濟/道具/合成
- `items`：道具定義（效果、稀有度、價格）。
- `user_items`：使用者背包與數量。
- `user_buffs`：臨時增益/減益。
- `recipes`：合成配方。
- `recipe_ingredients`：配方材料。

## 世界觀/敘事
- `lore_entries`：劇情章節內容。
- `lore_progress`：使用者的劇情進度。

## 戰鬥/副本/天賦
- `bosses`：首領狀態（HP、等級、狀態）。
- `dungeons`：副本主體。
- `dungeon_stages`：副本階段。
- `talent_trees`：天賦樹定義。
- `user_talents`：玩家天賦進度。

## 關聯速覽
- `users` → `quests` / `goals` / `action_logs` / `habit_states` / `user_items` / `bosses` / `rivals`
- `goals` → `quests`
- `items` → `user_items` / `recipes`
- `recipes` → `recipe_ingredients`
- `dungeons` → `dungeon_stages`

## Migration
- Alembic 版本在 `app/alembic/versions/`
- 建議固定用 `python scripts/ops.py migrate` 更新 schema
