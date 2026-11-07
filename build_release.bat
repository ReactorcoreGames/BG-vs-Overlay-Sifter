@echo off
setlocal

:: ============================================================================
::  BG vs Overlay Sifter - release build
::
::  Produces  dist\BG vs Overlay Sifter\  and  dist\BG vs Overlay Sifter.zip
::
::  release_package.py refuses to pass a release holding promo.md, config.json,
::  test material or anything else that is not on its list. If this says FAILED,
::  do not upload anything from dist\.
::
::  Pass --no-pause to run it without stopping at the end.
:: ============================================================================

cd /d "%~dp0"
set PYTHON=.venv\Scripts\python.exe
set NAME=BG vs Overlay Sifter

if not exist "%PYTHON%" (
    echo BUILD FAILED - no .venv here. See "Running from source" in readme.md.
    goto :failed
)

:: A failed build must not leave the last good zip looking like its result.
if exist "dist\%NAME%.zip" move /y "dist\%NAME%.zip" "dist\%NAME% (previous build).zip" >nul

echo.
echo [1/3] Running the tests...
"%PYTHON%" -m pytest tests/ -q
if errorlevel 1 (
    echo BUILD FAILED - the tests did not pass.
    goto :failed
)

echo.
echo [2/3] Running PyInstaller...
"%PYTHON%" -m PyInstaller --noconfirm --clean build_release.spec
if errorlevel 1 (
    echo BUILD FAILED - PyInstaller returned an error.
    goto :failed
)
if not exist "dist\%NAME%\%NAME%.exe" (
    echo BUILD FAILED - no exe at "dist\%NAME%\%NAME%.exe"
    goto :failed
)

echo.
echo [3/3] Assembling, checking and zipping...
"%PYTHON%" release_package.py
if errorlevel 1 goto :failed

echo.
echo Done. Test the exe from a folder outside this project, so it cannot pick up
echo the development config.json, before uploading the zip.
echo.
if not "%~1"=="--no-pause" pause
exit /b 0

:failed
echo.
echo ************************************************************
echo  BUILD FAILED. Do not upload anything from dist\.
echo ************************************************************
echo.
if not "%~1"=="--no-pause" pause
exit /b 1
