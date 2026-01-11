#!/bin/bash

# LifeGame Service Installer

SERVICE_NAME="lifgame.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
SOURCE_PATH="$(pwd)/lifgame.service"

echo "Installing $SERVICE_NAME from $SOURCE_PATH..."

# 1. Update the User/Group in the service file to match current user if needed
CURRENT_USER=$(whoami)
sed -i "s/User=charlie/User=$CURRENT_USER/g" lifgame.service
sed -i "s/Group=charlie/Group=$CURRENT_USER/g" lifgame.service
# Also update working directory just in case it's different
CURRENT_DIR=$(pwd)
sed -i "s|WorkingDirectory=/home/charlie/lifgame|WorkingDirectory=$CURRENT_DIR|g" lifgame.service
sed -i "s|Environment=\"PATH=/home/charlie/lifgame|Environment=\"PATH=$CURRENT_DIR|g" lifgame.service
sed -i "s|Environment=\"PYTHONPATH=/home/charlie/lifgame|Environment=\"PYTHONPATH=$CURRENT_DIR|g" lifgame.service

# 2. Check if uv is in the expected path, if not try to find it
UV_PATH=$(which uv)
if [ -z "$UV_PATH" ]; then
    echo "WARNING: 'uv' not found in PATH. Please ensure uv is installed."
else
    # Update ExecStart to use the actual uv path
    sed -i "s|ExecStart=.*|ExecStart=$UV_PATH run uvicorn app.main:app --host 0.0.0.0 --port 8000|g" lifgame.service
fi

# 3. Copy to systemd
echo "Requesting sudo permission to copy service file..."
sudo cp lifgame.service $SERVICE_PATH

# 4. Reload and Enable
echo "Reloading systemd..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo "✅ Service Started!"
echo "Check status with: sudo systemctl status $SERVICE_NAME"
echo "Check logs with: sudo journalctl -u $SERVICE_NAME -f"
