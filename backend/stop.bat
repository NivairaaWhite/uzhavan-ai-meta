@echo off
setlocal enabledelayedexpansion
REM Stops the Uzhavan.AI stack started by start.bat. Data in the Postgres
REM and Redis volumes is preserved (docker compose down, not down -v).

set "BACKEND_DIR=%~dp0"
cd /d "%BACKEND_DIR%"

docker compose version >nul 2>&1
if errorlevel 1 (
    where docker-compose >nul 2>&1
    if errorlevel 1 (
        echo Docker Compose was not found — nothing to stop.
        pause
        exit /b 1
    ) else (
        set "COMPOSE=docker-compose"
    )
) else (
    set "COMPOSE=docker compose"
)

echo Stopping Uzhavan.AI...
%COMPOSE% down

echo Stopped. Your data is preserved for next time you run start.bat.
pause
