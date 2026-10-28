#!/usr/bin/env bash
# One-click launcher for Uzhavan.AI (macOS). Double-click this file in
# Finder (or run ./start.command from a terminal). Builds and starts the full
# backend stack (Postgres+PostGIS, Redis, API, Celery worker+beat) via
# Docker Compose, then opens the interactive API docs in your browser.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/backend"

if ! command -v docker &> /dev/null; then
    echo "Docker is not installed."
    echo "Install it from https://docs.docker.com/engine/install/ and run this again."
    read -r -p "Press Enter to close..."
    exit 1
fi

echo "Checking that Docker Desktop is running..."
if ! docker info &> /dev/null; then
    echo "Docker Desktop is installed but not running yet."
    if [ -d "/Applications/Docker.app" ]; then
        echo "Starting Docker Desktop for you — this can take a minute or two..."
        open -a Docker
        engine_ready=false
        for _ in $(seq 1 60); do
            if docker info &> /dev/null; then
                engine_ready=true
                break
            fi
            sleep 2
        done
        if [ "$engine_ready" = false ]; then
            echo ""
            echo "Docker Desktop still isn't responding after 2 minutes."
            echo "Open Docker Desktop manually from the menu bar, wait for it to"
            echo "say it's running, then run this script again."
            read -r -p "Press Enter to close..."
            exit 1
        fi
        echo "Docker Desktop is up."
    else
        echo "Please start Docker Desktop yourself, then run this script again."
        read -r -p "Press Enter to close..."
        exit 1
    fi
fi

if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    echo "Docker Compose was not found (neither 'docker compose' nor 'docker-compose')."
    echo "Install Docker Desktop or the compose-plugin package and run this again."
    read -r -p "Press Enter to close..."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "First run: creating backend/.env from .env.example."
    echo "(Edit it later to add real Bhashini/Razorpay/DigiLocker API keys.)"
    cp .env.example .env
fi

echo ""
echo "Starting Uzhavan.AI (Postgres, Redis, API, Celery)..."
echo "First build can take a few minutes while Docker downloads images and"
echo "installs Python packages."
echo ""
if ! $COMPOSE up -d --build; then
    echo ""
    echo "Something went wrong starting the stack. See the output above."
    read -r -p "Press Enter to close..."
    exit 1
fi

echo ""
echo "Waiting for Postgres, Redis, the API, and the Celery worker to report"
echo "healthy (celery_beat has no meaningful health check of its own — see"
echo "the comment in docker-compose.yml — so it isn't part of this wait)."
echo ""
if $COMPOSE up -d --wait --wait-timeout 180 db redis api celery_worker; then
    echo ""
    echo "Uzhavan.AI is running."
    echo "API docs: http://localhost:8000/docs"
    if command -v open &> /dev/null; then
        open http://localhost:8000/docs &> /dev/null &
    fi
else
    echo ""
    echo "=========================================================="
    echo "The stack did NOT become healthy in time. Here's why:"
    echo "=========================================================="
    echo ""
    echo "--- api logs (last 50 lines) ---"
    $COMPOSE logs --tail=50 api
    echo ""
    echo "--- celery_worker logs (last 50 lines) ---"
    $COMPOSE logs --tail=50 celery_worker
    echo ""
    echo "--- celery_beat logs (last 30 lines) ---"
    $COMPOSE logs --tail=30 celery_beat
    echo ""
    echo "--- db logs (last 30 lines) ---"
    $COMPOSE logs --tail=30 db
    echo ""
    echo "=========================================================="
    echo "For the full picture, run from the backend/ folder:"
    echo "    $COMPOSE logs -f"
    echo "=========================================================="
    read -r -p "Press Enter to close..."
    exit 1
fi

echo ""
echo "To stop everything later, run stop.command in this folder."
read -r -p "Press Enter to close this window..."
