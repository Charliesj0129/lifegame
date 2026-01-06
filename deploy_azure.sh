#!/bin/bash
set -e

# Configuration
REGION="eastasia"
APP_NAME="lifgame"
# Generate random suffix for uniqueness
SUFFIX=${DEPLOY_SUFFIX:-$(openssl rand -hex 4)}
RG_NAME="rg-${APP_NAME}"
ACR_NAME="${APP_NAME}acr${SUFFIX}"
ASP_NAME="asp-${APP_NAME}"
WEB_NAME="app-${APP_NAME}-${SUFFIX}"
DB_SERVER_NAME="psql-${APP_NAME}-${SUFFIX}"
DB_NAME="lifgame_db"
DB_ADMIN="lifgameadmin"
DB_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)

echo "Starting deployment with suffix: $SUFFIX"
echo "Region: $REGION"

# 1. Resource Group
echo "Creating Resource Group: $RG_NAME..."
az group create --name $RG_NAME --location $REGION

# 2. Container Registry (ACR) - Basic is cheapest
echo "Creating ACR: $ACR_NAME..."
az acr create --resource-group $RG_NAME --name $ACR_NAME --sku Basic --admin-enabled true

# 3. Build & Push Image
echo "Building Docker Image..."
# Use az acr build to build in the cloud
az acr build --registry $ACR_NAME --image ${APP_NAME}:latest .

# 4. App Service Plan - F1 (Free)
echo "Creating App Service Plan (Free Tier)..."
# Note: F1 might not support Linux in all regions/subscriptions for containers. 
# Attempt F1, fallback to B1 if failed? 
# "Azure for Students" usually supports F1.
az appservice plan create --name $ASP_NAME --resource-group $RG_NAME --sku F1 --is-linux

# 5. Create Web App
echo "Creating Web App..."
az webapp create --resource-group $RG_NAME --plan $ASP_NAME --name $WEB_NAME --deployment-container-image-name "${ACR_NAME}.azurecr.io/${APP_NAME}:latest"

# 6. PostgreSQL Flexible Server - B1ms (Cheapest burstable)
echo "Creating PostgreSQL Server (This may take a while)..."
# Tier B1ms is often free-tier eligible.
az postgres flexible-server create \
    --resource-group $RG_NAME \
    --name $DB_SERVER_NAME \
    --location $REGION \
    --admin-user $DB_ADMIN \
    --admin-password $DB_PASSWORD \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --storage-size 32 \
    --version 16 \
    --yes

echo "Creating Database: $DB_NAME..."
az postgres flexible-server db create \
     --resource-group $RG_NAME \
     --server-name $DB_SERVER_NAME \
     --database-name $DB_NAME

# 7. Configure Web App Settings
echo "Configuring Web App Settings..."

# Get ACR Credentials
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Construct Database URL
# Asyncpg driver: postgresql+asyncpg://user:pass@host:5432/dbname
DB_HOST="${DB_SERVER_NAME}.postgres.database.azure.com"
DATABASE_URL="postgresql+asyncpg://${DB_ADMIN}:${DB_PASSWORD}@${DB_HOST}:5432/${DB_NAME}"

# We need to read local .env for keys
# Using a simple grep/sed to read keys, assuming simple format
LINE_SECRET=$(grep LINE_CHANNEL_SECRET .env | cut -d '=' -f2)
LINE_TOKEN=$(grep LINE_CHANNEL_ACCESS_TOKEN .env | cut -d '=' -f2)
OR_KEY=$(grep OPENROUTER_API_KEY .env | cut -d '=' -f2)
OR_MODEL=$(grep OPENROUTER_MODEL .env | cut -d '=' -f2)

az webapp config appsettings set --resource-group $RG_NAME --name $WEB_NAME --settings \
    DATABASE_URL="$DATABASE_URL" \
    LINE_CHANNEL_SECRET="$LINE_SECRET" \
    LINE_CHANNEL_ACCESS_TOKEN="$LINE_TOKEN" \
    OPENROUTER_API_KEY="$OR_KEY" \
    OPENROUTER_MODEL="$OR_MODEL" \
    DOCKER_REGISTRY_SERVER_URL="https://${ACR_NAME}.azurecr.io" \
    DOCKER_REGISTRY_SERVER_USERNAME="$ACR_NAME" \
    DOCKER_REGISTRY_SERVER_PASSWORD="$ACR_PASSWORD" \
    WEBSITES_PORT=8000 \
    AUTO_MIGRATE=1

# 8. Allow Azure Internal Access to DB (Allow All Azure Services)
echo "Configuring DB Firewall..."
az postgres flexible-server firewall-rule create \
    --resource-group $RG_NAME \
    --name $DB_SERVER_NAME \
    --rule-name allow_azure \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0

echo "Deployment Complete!"
echo "Web URL: https://${WEB_NAME}.azurewebsites.net"
echo "Webhook URL: https://${WEB_NAME}.azurewebsites.net/callback"
echo "DB Connection: $DATABASE_URL"
