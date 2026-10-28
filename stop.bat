@echo off
setlocal enabledelayedexpansion
REM Stops the Uzhavan.AI stack started by start.bat. Data in the Postgres
REM and Redis volumes is preserved (docker compose down, not down -v).

set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%backend\docker-compose.yml" (
    set "BACKEND_DIR=%SCRIPT_DIR%backend"
) else (
    set "BACKEND_DIR=%SCRIPT_DIR%"
)

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
