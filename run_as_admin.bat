@echo off
:: MacroBoard - Auto install & run as Administrator
:: Double-click this file to launch MacroBoard

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [MacroBoard] Installing dependencies...
pip install keyboard pyautogui pillow --quiet

echo [MacroBoard] Starting...
python "%~dp0macro_keyboard.py"
pause
