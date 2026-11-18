@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11+ and retry.
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo npm was not found. Install Node.js 22+ and retry.
  pause
  exit /b 1
)
if not exist "backend\venv\Scripts\python.exe" (
  echo Preparing Python environment...
  py -3 -m venv backend\venv
  if errorlevel 1 exit /b 1
)
backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 exit /b 1
cd frontend
if not exist node_modules (
  call npm ci
  if errorlevel 1 exit /b 1
)
echo Starting JARVIS. Ollama should be running separately.
call npm run electron:dev
