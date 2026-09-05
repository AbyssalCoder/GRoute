@echo off
setlocal
set "ROOT=%~dp0"

start "Antartica Backend" powershell.exe -NoLogo -NoExit -ExecutionPolicy Bypass -File "%ROOT%start_backend.ps1"
start "Antartica Frontend" powershell.exe -NoLogo -NoExit -ExecutionPolicy Bypass -File "%ROOT%start_frontend.ps1"

endlocal
