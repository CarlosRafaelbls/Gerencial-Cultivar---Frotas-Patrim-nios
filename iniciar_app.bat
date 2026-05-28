@echo off
cd /d "C:\Users\Carlos Rafael\OneDrive\Área de Trabalho\controle_ferramentas"

start "" cmd /k python app.py

timeout /t 3 >nul

start http://127.0.0.1:5000