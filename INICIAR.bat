@echo off
chcp 65001 >nul
title Pastoral Ingeniería Comercial UC
echo.
echo  =====================================================
echo   PASTORAL INGENIERIA COMERCIAL UC
echo   Iniciando servidor...
echo  =====================================================
echo.
cd /d "%~dp0"
python iniciar.py
pause
