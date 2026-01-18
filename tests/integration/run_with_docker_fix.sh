#!/bin/bash
# Create a temporary directory for docker config
export DOCKER_CONFIG=$(mktemp -d)
echo '{"credsStore": ""}' > $DOCKER_CONFIG/config.json

# Run the test
uv run pytest tests/integration/test_db_integration.py

# Cleanup
rm -rf $DOCKER_CONFIG
