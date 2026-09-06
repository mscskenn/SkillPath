@echo off
cd /d "%~dp0"
npx supabase start
if errorlevel 1 pause
exit /b %errorlevel%
