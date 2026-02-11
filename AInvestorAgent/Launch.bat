@echo off
chcp 65001 >nul 2>&1
title AInvestorAgent - AI Investment Agent
color 0A

echo ============================================================
echo   AInvestorAgent - AI Investment Agent
echo   Starting...
echo ============================================================
echo.

:: ----------------------------------------------------------------
:: 1) Set working directory to the folder containing this .bat file
:: ----------------------------------------------------------------
cd /d "%~dp0"
echo [INFO] Working directory: %CD%
echo.

:: ----------------------------------------------------------------
:: 2) Check Python availability
:: ----------------------------------------------------------------
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo.
    echo Please install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    goto :error_exit
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo [OK] Found %PYTHON_VER%

:: ----------------------------------------------------------------
:: 3) Install Python dependencies (first run only)
:: ----------------------------------------------------------------
if not exist ".deps_installed" (
    echo.
    echo [INFO] First run - installing Python dependencies...
    echo [INFO] This may take a few minutes...
    python -m pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies!
        echo Please run manually: python -m pip install -r requirements.txt
        goto :error_exit
    )
    echo. > .deps_installed
    echo [OK] Dependencies installed successfully.
) else (
    echo [OK] Dependencies already installed.
)

:: ----------------------------------------------------------------
:: 4) Build frontend if dist/ doesn't exist
:: ----------------------------------------------------------------
if not exist "frontend\dist\index.html" (
    echo.
    echo [INFO] Frontend not built. Checking for Node.js...

    node --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Node.js not found. Frontend will not be served.
        echo [WARNING] Backend API will still work on http://127.0.0.1:8000/docs
        echo.
    ) else (
        echo [INFO] Building frontend...
        cd frontend
        if not exist "node_modules" (
            echo [INFO] Installing npm packages...
            call npm install --quiet 2>nul
        )
        call npm run build 2>nul
        cd ..
        if exist "frontend\dist\index.html" (
            echo [OK] Frontend built successfully.
        ) else (
            echo [WARNING] Frontend build failed. Backend-only mode.
        )
    )
) else (
    echo [OK] Frontend dist/ found.
)

:: ----------------------------------------------------------------
:: 5) Check if port 8000 is already in use
:: ----------------------------------------------------------------
echo.
netstat -ano 2>nul | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARNING] Port 8000 is already in use!
    echo [INFO] Attempting to stop the existing process...
    for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul

    netstat -ano 2>nul | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [ERROR] Cannot free port 8000. Please close the occupying program manually.
        goto :error_exit
    )
    echo [OK] Port 8000 freed.
)

:: ----------------------------------------------------------------
:: 6) Start the server
:: ----------------------------------------------------------------
echo.
echo ============================================================
echo   Starting AInvestorAgent server on http://127.0.0.1:8000
echo ============================================================
echo.

if exist "frontend\dist\index.html" (
    echo [INFO] Frontend: http://127.0.0.1:8000/
) else (
    echo [INFO] API Docs: http://127.0.0.1:8000/docs
)
echo [INFO] Press Ctrl+C to stop the server.
echo.

:: Run the server (this blocks until Ctrl+C)
python run.py

:: ----------------------------------------------------------------
:: 7) Server stopped
:: ----------------------------------------------------------------
echo.
echo ============================================================
echo   Server has stopped.
echo ============================================================
goto :normal_exit

:error_exit
echo.
echo ============================================================
echo   [ERROR] Startup failed. See messages above.
echo ============================================================
echo.
pause
exit /b 1

:normal_exit
echo.
pause
exit /b 0
