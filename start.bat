@echo off
REM ============================================
REM Alfred — Script de inicialização (Windows)
REM ============================================
REM Duplo clique neste arquivo para iniciar o Alfred.

set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%venv
set LOG_FILE=%SCRIPT_DIR%data\alfred.log

REM Criar pasta de dados se não existir
if not exist "%SCRIPT_DIR%data" mkdir "%SCRIPT_DIR%data"

REM Ativar virtualenv
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo Erro: virtualenv nao encontrado em %VENV_DIR%
    echo Execute o instalador primeiro: install.bat
    pause
    exit /b 1
)

REM Verificar se o Ollama está rodando
tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul 2>&1
if errorlevel 1 (
    echo Iniciando Ollama em background...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
)

REM Iniciar o Alfred
echo [%date% %time%] Iniciando Alfred... >> "%LOG_FILE%"
cd /d "%SCRIPT_DIR%"
python -m alfred
pause
