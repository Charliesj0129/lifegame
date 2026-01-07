#!/bin/bash
# scripts/update_keys.sh
set -e

APP_NAME="app-lifgame-955ea735"
RG_NAME="rg-lifgame"

echo "Updating App Settings for $APP_NAME..."

# Read from .env
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

LINE_SECRET=$(grep LINE_CHANNEL_SECRET .env | cut -d '=' -f2 | tr -d ' \r\n"')
LINE_TOKEN=$(grep LINE_CHANNEL_ACCESS_TOKEN .env | cut -d '=' -f2 | tr -d ' \r\n"')
OPENROUTER_KEY=$(grep OPENROUTER_API_KEY .env | cut -d '=' -f2 | tr -d ' \r\n"')

if [ -z "$LINE_SECRET" ] || [ -z "$LINE_TOKEN" ]; then
    echo "Error: LINE credentials missing in .env"
    exit 1
fi

echo "Setting LINE_CHANNEL_SECRET..."
echo "Setting LINE_CHANNEL_ACCESS_TOKEN..."

az webapp config appsettings set --resource-group $RG_NAME --name $APP_NAME --settings \
    LINE_CHANNEL_SECRET="$LINE_SECRET" \
    LINE_CHANNEL_ACCESS_TOKEN="$LINE_TOKEN" \
    OPENROUTER_API_KEY="$OPENROUTER_KEY"

echo "✅ Keys Updated! App will restart automatically."
