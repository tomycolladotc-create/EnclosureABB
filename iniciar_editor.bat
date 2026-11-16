@echo off
setlocal
cd /d "%~dp0"
rem Busca Python: lanzador "py", comando "python" (ignorando el atajo de la Tienda) o la instalacion habitual de Python 3.12.
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY python --version >nul 2>nul && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY (
  echo No se encontro Python. Instalalo desde https://www.python.org/downloads/ tildando "Add python.exe to PATH" y volve a abrir este archivo.
  pause
  exit /b 1
)
echo Usando: %PY%
%PY% -m pip install -r requirements.txt
%PY% iniciar_editor.py
if errorlevel 1 pause
