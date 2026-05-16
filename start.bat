@echo off
cd /d "%~dp0dashboard"
start /b "" powershell -NoProfile -WindowStyle Hidden -Command "do { Start-Sleep 1 } until ((Test-NetConnection localhost -Port 3000 -WarningAction SilentlyContinue).TcpTestSucceeded); Start-Process 'http://localhost:3000'"
npm run dev
