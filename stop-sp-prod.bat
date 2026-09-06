@echo off
cd /d "%~dp0"
docker compose -f docker-compose.prod.yml stop
if errorlevel 1 pause
exit /b %errorlevel%
