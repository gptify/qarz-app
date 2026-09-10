@echo off
title Qarz App TMA Server
cd /d "%~dp0"
echo ============================================================
echo  Qarz App - Telegram Mini App ishga tushirilmoqda...
echo  Manzil: http://localhost:8085
echo ============================================================
python serve_tma.py
pause
