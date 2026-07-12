@echo off
REM === 3D Model Generator — Local Dev Start ===
REM Starts backend (port 8000) and frontend (port 3000)

cd /d C:\Users\49176\3d-model-generator

REM Start backend in background
echo Starting backend on port 8000...
start "3D Backend" cmd /c "set PYTHONPATH= && set PYTHONHOME= && .venv\Scripts\python.exe -m uvicorn scripts.api:app --host 0.0.0.0 --port 8000"

REM Start frontend
echo Starting frontend on port 3000...
cd frontend
call npm run dev