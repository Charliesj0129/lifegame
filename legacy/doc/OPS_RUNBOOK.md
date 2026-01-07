# Ops Runbook

## 必要環境變數
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `DATABASE_URL`
- `OPENROUTER_API_KEY` 或 `GOOGLE_API_KEY`
- `OPENROUTER_MODEL` / `GEMINI_MODEL`
- `WEBSITES_PORT=8000`
- `AUTO_MIGRATE=1`（Azure 建議）

## 可選環境變數
- `ENABLE_LATENCY_LOGS=1`：開啟 AI 延遲紀錄（debug 用）
- `ENABLE_LOADING_ANIMATION=1`：開啟 LINE Loading 動畫

## Migration
```bash
python scripts/ops.py migrate
```

## Rich Menu
```bash
python scripts/ops.py rich-menus
# 或
python scripts/update_rich_menu.py
```

## Azure 部署（容器）
```bash
az acr build --registry <acr> --image lifgame:<tag> .
az webapp config container set --name <app> --resource-group <rg> \
  --container-image-name <acr>.azurecr.io/lifgame:<tag> \
  --container-registry-url https://<acr>.azurecr.io
az webapp restart --name <app> --resource-group <rg>
```

## Smoke Tests
```bash
curl -sS https://<app>.azurewebsites.net/health
curl -i -sS --http1.1 -X POST https://<app>.azurewebsites.net/callback -d '{}'
```

## 常見問題
- `/callback` 卡住：先確認 HTTP/1.1；未帶簽章會回 400（正常）。
- Migration 找不到 revision：檢查 `app/alembic/versions` 是否已包含所有版本。
- Rich Menu 不更新：刪舊 menu 後重新建立並設為 default。
