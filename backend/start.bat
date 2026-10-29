@echo off
setlocal enabledelayedexpansion
REM One-click launcher for Uzhavan.AI (Windows). Builds and starts the
REM full backend stack (Postgres+PostGIS, Redis, API, Celery) via Docker
REM Compose, then opens the interactive API docs in your browser.

set "BACKEND_DIR=%~dp0"
cd /d "%BACKEND_DIR%"

where docker >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop is not installed or not on PATH.
    echo Install it from https://www.docker.com/products/docker-desktop/ and run this again.
    pause
    exit /b 1
)

echo Checking that Docker Desktop is running...
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop is installed but the engine isn't running yet.
    set "DOCKER_EXE=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    if exist "!DOCKER_EXE!" (
        echo Starting Docker Desktop for you — this can take a minute or two...
        start "" "!DOCKER_EXE!"
    ) else (
        echo Could not find Docker Desktop automatically.
        echo Please start it yourself from the Start menu, then run this script again.
        pause
        exit /b 1
    )
    set "ENGINE_READY=0"
    for /l %%i in (1,1,60) do (
        docker info >nul 2>&1
        if not errorlevel 1 (
            set "ENGINE_READY=1"
            goto :engineready
        )
        timeout /t 2 /nobreak >nul
    )
    :engineready
    if "!ENGINE_READY!"=="0" (
        echo.
        echo Docker Desktop still isn't responding after 2 minutes.
        echo Open Docker Desktop manually and wait for the whale icon in the
        echo system tray to stop animating [that means the engine is up],
        echo then run this script again.
        pause
        exit /b 1
    )
    echo Docker Desktop is up.
)

docker compose version >nul 2>&1
if errorlevel 1 (
    where docker-compose >nul 2>&1
    if errorlevel 1 (
        echo Docker Compose was not found.
        echo Install Docker Desktop and run this again.
        pause
        exit /b 1
    ) else (
        set "COMPOSE=docker-compose"
    )
) else (
    set "COMPOSE=docker compose"
)

if not exist "%BACKEND_DIR%.env" (
    echo First run: creating backend\.env from .env.example.
    echo [Edit it later to add real Bhashini/Razorpay/DigiLocker API keys.]
    copy "%BACKEND_DIR%.env.example" "%BACKEND_DIR%.env" >nul
)

echo.
echo Starting Uzhavan.AI (Postgres, Redis, API, Celery)...
echo First build can take a few minutes while Docker downloads images and
echo installs Python packages.
echo.
%COMPOSE% up -d --build
if errorlevel 1 (
    echo.
    echo Something went wrong starting the stack. See the output above.
    pause
    exit /b 1
)

echo.
echo Waiting for Postgres, Redis, the API, and the Celery worker to report
echo healthy [celery_beat has no meaningful health check of its own — see
echo the comment in docker-compose.yml — so it isn't part of this wait].
echo.
%COMPOSE% up -d --wait --wait-timeout 180 db redis api celery_worker
if errorlevel 1 (
    echo.
    echo ==========================================================
    echo The stack did NOT become healthy in time. Here's why:
    echo ==========================================================
    echo.
    echo --- api logs [last 50 lines] ---
    %COMPOSE% logs --tail=50 api
    echo.
    echo --- celery_worker logs [last 50 lines] ---
    %COMPOSE% logs --tail=50 celery_worker
    echo.
    echo --- celery_beat logs [last 30 lines] ---
    %COMPOSE% logs --tail=30 celery_beat
    echo.
    echo --- db logs [last 30 lines] ---
    %COMPOSE% logs --tail=30 db
    echo.
    echo ==========================================================
    echo For the full picture, run from the backend folder:
    echo     %COMPOSE% logs -f
    echo ==========================================================
    pause
    exit /b 1
)

echo.
echo Uzhavan.AI is running.
echo API docs: http://localhost:8000/docs
echo Fallback: http://127.0.0.1:8000/docs
start "" "http://127.0.0.1:8000/docs"

echo.
echo To stop everything later, run stop.bat in this folder.
pause
