@echo off
setlocal

rem Run from the project folder (same place as main.py) - double-click
rem or "build.bat" from a console.
rem
rem This file is plain ASCII on purpose (no Cyrillic anywhere, not even
rem in comments): cmd.exe's own batch parser can misread UTF-8 bytes as
rem command separators, which showed up as "'...' is not recognized as
rem an internal or external command" for random word fragments. Keeping
rem this file ASCII-only sidesteps that category of bug entirely.
rem
rem IMPORTANT: old build\ and dist\ are deleted below before every
rem build. Without that, PyInstaller can cache old copies of bundled
rem files (like web\index.html) in build\ and not notice the source
rem changed - the exe gets rebuilt but still runs the old code inside.

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

if exist "sounds" goto :sounds_ok
echo WARNING: no "sounds" folder next to this script.
echo Copy soft, sharp, deep (and custom, if you have it) here before
echo building - see README.md.
pause
exit /b 1

:sounds_ok
echo Installing/updating dependencies...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :build_error

echo.
echo Building exe from scratch (this can take a minute or two)...
python -m PyInstaller --clean --noconfirm --windowed --name "Mouse Sound FX" --add-data "web;web" --add-data "sounds;sounds" --collect-submodules webview --collect-submodules clr_loader --collect-submodules pythonnet --hidden-import pynput.mouse._win32 --hidden-import pynput.keyboard._win32 main.py
if errorlevel 1 goto :build_error

echo.
echo Done! The program is here: dist\Mouse Sound FX\Mouse Sound FX.exe
echo To run it or share it with someone, you need the WHOLE
echo "dist\Mouse Sound FX" folder, not just the .exe by itself - the
echo files it needs sit right next to it.
pause
exit /b 0

:build_error
echo.
echo Build failed - see the error messages above.
pause
exit /b 1
