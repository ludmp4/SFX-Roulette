@echo off
setlocal
title SFX Roulette Installer

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "PS_INSTALL=%ROOT_DIR%\install.ps1"

echo.
echo SFX Roulette Installer
echo ======================
echo.

if not exist "%PS_INSTALL%" (
    echo Could not find install.ps1 in the SFX Roulette folder.
    echo Please run this from the extracted SFX Roulette repository.
    echo.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_INSTALL%" -PreferGitHub %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo Done.
) else (
    echo Installer failed with exit code %EXIT_CODE%.
)
echo.
pause
exit /b %EXIT_CODE%
