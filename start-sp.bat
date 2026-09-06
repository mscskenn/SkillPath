@echo off
cd /d "%~dp0"
docker compose up -d
if errorlevel 1 pause
exit /b %errorlevel%
