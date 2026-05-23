@echo off
title Finance Bot — Build

:: Muda para a raiz do projeto (pasta pai de tools/)
cd /d "%~dp0.."

echo.
echo ============================================
echo  Finance Bot — Build dos executaveis
echo ============================================
echo.

where python >nul 2>&1 || (
    echo [ERRO] Python nao encontrado. Instale em https://python.org
    pause ^& exit /b 1
)

echo Instalando dependencias de build...
pip install pyinstaller pillow truststore --quiet

echo Removendo pathlib legado ^(incompativel com PyInstaller^)...
pip uninstall pathlib -y >nul 2>&1

echo Gerando icone...
python tools\generate_icon.py
if not exist assets\icon.ico (
    echo [AVISO] Icone nao gerado — build sem icone customizado.
)

echo.
echo [1/2] Compilando FinanceBotSetup.exe ...
pyinstaller --onefile --windowed --uac-admin --name "FinanceBotSetup" --clean --icon assets\icon.ico --add-data "assets;assets" wizard\setup_wizard.py
if not exist dist\FinanceBotSetup.exe (
    echo [ERRO] Build do wizard falhou. Veja o output acima.
    pause ^& exit /b 1
)

echo.
echo [2/2] Compilando FinanceBotUpdate.exe ...
pyinstaller --onefile --windowed --uac-admin --name "FinanceBotUpdate" --clean --icon assets\icon.ico wizard\updater.py
if not exist dist\FinanceBotUpdate.exe (
    echo [ERRO] Build do updater falhou. Veja o output acima.
    pause ^& exit /b 1
)

echo.
echo ============================================
echo  Pronto! Arquivos gerados em dist\:
echo    FinanceBotSetup.exe
echo    FinanceBotUpdate.exe
echo ============================================
echo.
echo Publique ambos como assets na GitHub Release correspondente.
