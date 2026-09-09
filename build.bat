@echo off
setlocal enabledelayedexpansion

echo ===============================================================================
echo   CISCO HISTORICAL UNUSED PORT SCANNER - AUTOMATED BUILD ^& RELEASE SCRIPT
echo ===============================================================================

echo [1/4] Checking Python environment...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

echo [2/4] Running automated unit tests...
python -m unittest discover tests -v
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Unit tests failed! Canceling build to ensure safety.
    pause
    exit /b 1
)
echo [SUCCESS] All unit tests passed!

echo [3/4] Building standalone Windows .exe with PyInstaller...
python build_historical_scanner_exe.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo [4/4] Packaging release bundle ZIP...
if not exist release mkdir release
if exist dist\CiscoHistoricalUnusedPortScanner.exe (
    powershell -Command "Compress-Archive -Path dist\CiscoHistoricalUnusedPortScanner.exe, README.md, LICENSE, .env.example -DestinationPath release\CiscoHistoricalUnusedPortScanner-v1.0.0-win64.zip -Force"
    echo [SUCCESS] Release package created at: release\CiscoHistoricalUnusedPortScanner-v1.0.0-win64.zip
) else (
    echo [WARNING] dist\CiscoHistoricalUnusedPortScanner.exe not found!
)

echo ===============================================================================
echo   BUILD ^& PACKAGING COMPLETED SUCCESSFULLY!
echo   Executable: dist\CiscoHistoricalUnusedPortScanner.exe
echo   Release ZIP: release\CiscoHistoricalUnusedPortScanner-v1.0.0-win64.zip
echo ===============================================================================
pause
