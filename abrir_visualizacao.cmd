@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8501/_stcore/health' -UseBasicParsing -TimeoutSec 2; if ($response.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if not errorlevel 1 (
    start "" "http://localhost:8501"
    exit /b 0
)

".venv\Scripts\python.exe" -m streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=false --server.runOnSave=true
pause
