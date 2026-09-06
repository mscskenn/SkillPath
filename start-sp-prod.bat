@echo off
cd /d "%~dp0"
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d --build
if errorlevel 1 pause
exit /b %errorlevel%
