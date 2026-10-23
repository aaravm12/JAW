@echo off
cd /d "%~dp0"
py -3.12 scripts\setup.py
if errorlevel 1 (
  echo If Python 3.12 is missing, install it from python.org, then try again.
  pause
)
