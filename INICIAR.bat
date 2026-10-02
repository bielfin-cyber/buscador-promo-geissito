@echo off
setlocal
cd /d "%~dp0"
title Buscador Promo do Geissito
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1"
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar. Veja a mensagem acima.
  pause
)

