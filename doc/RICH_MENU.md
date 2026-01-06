# Rich Menu 操作面板

## 版面（4x3）
- 第 1 列：狀態｜任務｜背包｜商店
- 第 2 列：合成｜首領｜攻擊｜簽到
- 第 3 列：重新生成｜全部接受｜略過 Viper｜指令

## 相關檔案
- 圖片：`assets/rich_menu.jpg`
- 產生工具：`scripts/generate_rich_menu.py`
- 更新工具：`scripts/update_rich_menu.py`
- Rich menu ID：`data/rich_menus.json`

## 更新流程
1. 更新圖片（或重新產生）
2. 執行 `python scripts/update_rich_menu.py`
3. 重新進入聊天室確認新面板
