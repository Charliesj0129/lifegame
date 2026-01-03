#!/bin/bash
# Configuration
# Replace these after DB creation
DB_HOST="psql-lifgame-955ea735-sea.postgres.database.azure.com"
DB_USER="famousmole3"
DB_PASS="hgQoVwZV638IyTf4Z32TXQ"
DB_NAME="postgres"
# CLI usually generates "azureuser" or similar?
# I'll check the log output.

RG_NAME="rg-lifgame"
WEB_NAME="app-lifgame-955ea735"
ACR_NAME="lifgameacr955ea735"

# Get ACR Credentials
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Read .env
LINE_SECRET=$(grep LINE_CHANNEL_SECRET .env | cut -d '=' -f2)
LINE_TOKEN=$(grep LINE_CHANNEL_ACCESS_TOKEN .env | cut -d '=' -f2)
OR_KEY=$(grep OPENROUTER_API_KEY .env | cut -d '=' -f2)
OR_MODEL=$(grep OPENROUTER_MODEL .env | cut -d '=' -f2)

DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASS}@${DB_HOST}:5432/${DB_NAME}"

echo "Configuring Web App..."
az webapp config appsettings set --resource-group $RG_NAME --name $WEB_NAME --settings \
    DATABASE_URL="$DATABASE_URL" \
    LINE_CHANNEL_SECRET="$LINE_SECRET" \
    LINE_CHANNEL_ACCESS_TOKEN="$LINE_TOKEN" \
    OPENROUTER_API_KEY="$OR_KEY" \
    OPENROUTER_MODEL="$OR_MODEL" \
    DOCKER_REGISTRY_SERVER_URL="https://${ACR_NAME}.azurecr.io" \
    DOCKER_REGISTRY_SERVER_USERNAME="$ACR_NAME" \
    DOCKER_REGISTRY_SERVER_PASSWORD="$ACR_PASSWORD" \
    WEBSITES_PORT=8000
