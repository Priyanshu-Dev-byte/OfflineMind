@echo off
REM OfflineMind Launcher
if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" -m streamlit run "%~dp0app\main.py"
) else (
    python -m streamlit run app\main.py
)
pause
