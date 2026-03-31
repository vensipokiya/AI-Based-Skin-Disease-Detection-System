@echo off
echo ============================================
echo  DermaCare AI Backend - Starting Server...
echo ============================================
echo.

REM Change to the project ROOT (one folder above this file)
cd /d "%~dp0.."
echo Working directory: %cd%
echo.
echo Access the app at: http://127.0.0.1:8000
echo Access the AI Scanner at: http://127.0.0.1:8000/detection.html
echo.

python -m uvicorn backend.main:app --reload --port 8000 --host 0.0.0.0
pause
