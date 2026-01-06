#!/bin/bash
set -e

APP_NAME="lifgame"
RG_NAME="rg-${APP_NAME}"

echo "🔍 Searching for existing Web App in Resource Group '$RG_NAME'..."

# Hardcoded for stability
WEB_NAME="app-lifgame-955ea735"
ACR_NAME="lifgameacr955ea735"

echo "✅ Target Web App: $WEB_NAME"
echo "✅ Target ACR: $ACR_NAME"

echo "🚀 Building and Pushing Docker Image..."
az acr build --registry $ACR_NAME --image ${APP_NAME}:latest .

echo "♻️ Restarting Web App..."
az webapp restart --name $WEB_NAME --resource-group $RG_NAME

echo "✅ Deployment Updated!"
echo "Web URL: https://${WEB_NAME}.azurewebsites.net"
