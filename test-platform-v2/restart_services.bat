@echo off
echo Killing old processes...
taskkill /F /IM node.exe 2>nul
taskkill /F /PID 10092 2>nul
echo.
echo Starting backend on port 8003...
cd /d F:\CamelTv\test-platform-v2\backend
start "Backend-8003" /MIN cmd /c "uvicorn app.main:app --reload --port 8003 --host 0.0.0.0"
timeout /t 5 /nobreak >nul
echo.
echo Starting frontend on port 5173 (proxy to 8003)...
cd /d F:\CamelTv\test-platform-v2\frontend
start "Frontend-5173" /MIN cmd /c "npx vite --port 5173 --host"
echo.
echo Done! Backend: http://localhost:8003, Frontend: http://localhost:5173
pause
