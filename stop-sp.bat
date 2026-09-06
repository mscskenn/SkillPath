@echo off
cd /d "%~dp0"
npx supabase stop
if errorlevel 1 pause
exit /b %errorlevel%
