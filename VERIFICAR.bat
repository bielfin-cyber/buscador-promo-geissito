@echo off
setlocal
cd /d "%~dp0"
title Verificacao - Promo do Geissito
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0verificar.ps1"
pause

