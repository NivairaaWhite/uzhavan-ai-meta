#!/usr/bin/env bash
# Stops the Uzhavan.AI stack (macOS). Double-click in Finder, or run
# Data in the Postgres and Redis volumes is preserved (docker compose
# down, not down -v) so restarting picks up right where you left off.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/backend"

if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    echo "Docker Compose was not found — nothing to stop."
    read -r -p "Press Enter to close..."
    exit 1
fi

echo "Stopping Uzhavan.AI..."
$COMPOSE down

echo "Stopped. Your data is preserved for next time you run start.sh."
read -r -p "Press Enter to close this window..."
