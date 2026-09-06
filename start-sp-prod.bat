@echo off
cd /d "%~dp0"
npx supabase status >nul 2>&1
if errorlevel 1 (
    echo Supabase local stack is not running. Start it first with: npx supabase start
    pause
    exit /b 1
)
docker compose -f docker-compose.prod.yml down -v
if errorlevel 1 (
    pause
    exit /b %errorlevel%
)
docker compose -f docker-compose.prod.yml up -d --build
if errorlevel 1 pause
exit /b %errorlevel%
