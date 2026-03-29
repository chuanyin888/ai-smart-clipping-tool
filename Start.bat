@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 goto RUNPY
where python >nul 2>nul
if %errorlevel%==0 goto RUNPYTHON
msg * "Python was not found. Please install Python 3.11 or 3.12 and enable Add Python to PATH." >nul 2>nul
exit /b 1
:RUNPY
py -3 launcher.py
exit /b %errorlevel%
:RUNPYTHON
python launcher.py
exit /b %errorlevel%
