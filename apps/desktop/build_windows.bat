@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /D "%SCRIPT_DIR%"

set "VENV=.venv\Scripts"
set "PYINSTALLER=%VENV%\pyinstaller.exe"
set "PYTHON=%VENV%\python.exe"
set "SPEC=swuift_app.spec"

echo ========================================
echo  SWUIFT Windows build
echo ========================================

"%PYTHON%" build_assets.py
if errorlevel 1 exit /b 1
if defined SWUIFT_BUILD_ID (
    > BUILD_INFO echo %SWUIFT_BUILD_ID%
) else (
    > BUILD_INFO echo local
)

echo.
echo Running PyInstaller ...
"%PYINSTALLER%" "%SPEC%" --noconfirm --clean
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

echo.
echo Build complete: dist\SWUIFT\SWUIFT.exe

if defined WINDOWS_SIGN_PFX (
    if defined WINDOWS_SIGN_PASSWORD (
        echo Signing application with configured certificate ...
        signtool sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f "%WINDOWS_SIGN_PFX%" /p "%WINDOWS_SIGN_PASSWORD%" "dist\SWUIFT\SWUIFT.exe"
        if errorlevel 1 exit /b 1
    )
) else (
    echo NOTE: signing certificate is not configured; application remains unsigned.
)

if exist "swuift_setup.iss" (
    echo.
    echo Creating Windows installer with InnoSetup ...
    set "INNO_COMPILER=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if not exist "!INNO_COMPILER!" (
        set "INNO_COMPILER=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    )
    if exist "!INNO_COMPILER!" (
        "!INNO_COMPILER!" swuift_setup.iss
        if errorlevel 1 (
            echo WARNING: InnoSetup build failed.
        ) else (
            echo InnoSetup installer created in dist\
            if defined WINDOWS_SIGN_PFX (
                for %%F in ("dist\SWUIFT_Setup_*.exe") do signtool sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f "%WINDOWS_SIGN_PFX%" /p "%WINDOWS_SIGN_PASSWORD%" "%%~fF"
                if errorlevel 1 exit /b 1
            )
        )
    ) else (
        echo NOTE: InnoSetup not found, skipping installer creation.
        echo       Install InnoSetup 6 from https://jrsoftware.org/isdl.php
    )
)

echo.
echo ========================================
echo  Build finished.
echo ========================================
endlocal
