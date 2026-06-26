@echo off
set "PYTHONPATH=%~dp0.venv\Lib\site-packages;%PYTHONPATH%"
python "%~dp0file_sort.py"
