@echo off
title Finance Bot — Build Setup Wizard
echo.
echo ============================================
echo  Finance Bot — gerando FinanceBotSetup.exe
echo ============================================
echo.

where python >nul 2>&1 || (
    echo [ERRO] Python nao encontrado. Instale em https://python.org
    pause & exit /b 1
)

echo Instalando dependencias de build...
pip install pyinstaller --quiet

echo.
echo Compilando wizard...
pyinstaller --onefile --windowed --name "FinanceBotSetup" --clean setup_wizard.py

if exist dist\FinanceBotSetup.exe (
    echo.
    echo ============================================
    echo  Pronto! Arquivo gerado em:
    echo  dist\FinanceBotSetup.exe
    echo ============================================
    echo.
    echo Coloque o .exe na raiz do projeto junto com
    echo as pastas backend/, dashboard/, bot/ e fly.toml
) else (
    echo.
    echo [ERRO] Build falhou. Veja o output acima.
)

pause
