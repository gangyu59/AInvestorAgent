@echo off
chcp 65001 >nul 2>&1
title AInvestorAgent - One Click Packaging
color 0E

echo ============================================================
echo   AInvestorAgent - One Click Packaging
echo ============================================================
echo.
echo This script will:
echo   1. Build the frontend
echo   2. Package all necessary files
echo   3. Create a ready-to-deploy package
echo.

:: ----------------------------------------------------------------
:: Set working directory
:: ----------------------------------------------------------------
cd /d "%~dp0"
set "SRC=%CD%"
set "OUTDIR=%~dp0..\AInvestorAgent_Package"
echo [INFO] Source: %SRC%
echo [INFO] Output: %OUTDIR%
echo.

:: ----------------------------------------------------------------
:: Check prerequisites
:: ----------------------------------------------------------------
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    goto :error_exit
)
echo [OK] Python found.

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Node.js not found. Skipping frontend build.
    set "SKIP_FRONTEND=1"
) else (
    echo [OK] Node.js found.
    set "SKIP_FRONTEND=0"
)

:: ----------------------------------------------------------------
:: Build frontend
:: ----------------------------------------------------------------
if "%SKIP_FRONTEND%"=="0" (
    echo.
    echo [STEP 1/4] Building frontend...
    cd "%SRC%\frontend"

    if not exist "node_modules" (
        echo [INFO] Installing npm packages...
        call npm install
        if %errorlevel% neq 0 (
            echo [ERROR] npm install failed!
            goto :error_exit
        )
    )

    echo [INFO] Running npm run build...
    call npm run build
    if %errorlevel% neq 0 (
        echo [ERROR] Frontend build failed!
        goto :error_exit
    )
    cd "%SRC%"
    echo [OK] Frontend built successfully.
) else (
    echo.
    echo [STEP 1/4] Skipping frontend build (Node.js not available^)
)

:: ----------------------------------------------------------------
:: Clean and create output directory
:: ----------------------------------------------------------------
echo.
echo [STEP 2/4] Preparing output directory...

if exist "%OUTDIR%" (
    echo [INFO] Removing old package...
    rmdir /s /q "%OUTDIR%" 2>nul
)
mkdir "%OUTDIR%\AInvestorAgent" 2>nul

:: ----------------------------------------------------------------
:: Copy files
:: ----------------------------------------------------------------
echo.
echo [STEP 3/4] Copying files...

:: Backend
echo   Copying backend...
xcopy /e /i /q "%SRC%\backend" "%OUTDIR%\AInvestorAgent\backend" >nul
if %errorlevel% neq 0 echo [WARNING] backend copy had issues

:: Scripts
if exist "%SRC%\scripts" (
    echo   Copying scripts...
    xcopy /e /i /q "%SRC%\scripts" "%OUTDIR%\AInvestorAgent\scripts" >nul
)

:: Frontend dist (built files only, not source)
if exist "%SRC%\frontend\dist" (
    echo   Copying frontend dist...
    xcopy /e /i /q "%SRC%\frontend\dist" "%OUTDIR%\AInvestorAgent\frontend\dist" >nul
) else (
    echo   [WARNING] No frontend dist/ - frontend will not be available
)

:: Frontend env (needed for VITE_API_BASE)
if exist "%SRC%\frontend\.env" (
    mkdir "%OUTDIR%\AInvestorAgent\frontend" 2>nul
    copy /y "%SRC%\frontend\.env" "%OUTDIR%\AInvestorAgent\frontend\.env" >nul
)

:: Database directory
mkdir "%OUTDIR%\AInvestorAgent\db" 2>nul
if exist "%SRC%\db\AInvestorAgent.sqlite" (
    echo   Copying database...
    copy /y "%SRC%\db\AInvestorAgent.sqlite" "%OUTDIR%\AInvestorAgent\db\" >nul
)

:: Config and entry files
echo   Copying config files...
copy /y "%SRC%\run.py" "%OUTDIR%\AInvestorAgent\" >nul
copy /y "%SRC%\requirements.txt" "%OUTDIR%\AInvestorAgent\" >nul
copy /y "%SRC%\__init__.py" "%OUTDIR%\AInvestorAgent\" >nul 2>nul

:: .env (API keys - important!)
if exist "%SRC%\.env" (
    copy /y "%SRC%\.env" "%OUTDIR%\AInvestorAgent\" >nul
    echo   [OK] .env copied (contains API keys^)
) else (
    echo   [WARNING] No .env file found! API keys will be missing!
)

:: Logs directory
mkdir "%OUTDIR%\AInvestorAgent\logs" 2>nul

:: Copy Launch.bat
if exist "%SRC%\Launch.bat" (
    copy /y "%SRC%\Launch.bat" "%OUTDIR%\AInvestorAgent\" >nul
    echo   [OK] Launch.bat copied
)

:: ----------------------------------------------------------------
:: Exclude unnecessary files
:: ----------------------------------------------------------------
echo.
echo [STEP 4/4] Cleaning up...

:: Remove __pycache__, .pyc, test files, etc.
for /r "%OUTDIR%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)
for /r "%OUTDIR%" %%f in (*.pyc) do del "%%f" 2>nul
for /r "%OUTDIR%" %%f in (.coverage) do del "%%f" 2>nul

:: Remove node_modules if accidentally copied
if exist "%OUTDIR%\AInvestorAgent\frontend\node_modules" (
    rmdir /s /q "%OUTDIR%\AInvestorAgent\frontend\node_modules" 2>nul
)

:: ----------------------------------------------------------------
:: Summary
:: ----------------------------------------------------------------
echo.
echo ============================================================
echo   Packaging Complete!
echo ============================================================
echo.
echo   Output: %OUTDIR%\AInvestorAgent\
echo.
echo   To deploy:
echo     1. Compress the AInvestorAgent_Package folder
echo     2. Transfer to target PC
echo     3. Unzip
echo     4. Run AInvestorAgent\Launch.bat
echo.
echo   Prerequisites on target PC:
echo     - Python 3.8+ (with pip)
echo     - Internet access (for first-time dependency install)
echo.

:: Show package size
for /f "tokens=3" %%a in ('dir /s "%OUTDIR%" 2^>nul ^| findstr /c:"File(s)"') do (
    echo   Package size: %%a bytes
)

echo.
pause
exit /b 0

:error_exit
echo.
echo [ERROR] Packaging failed! See messages above.
echo.
cd "%SRC%"
pause
exit /b 1
