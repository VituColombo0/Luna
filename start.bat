@echo off
REM ============================================
REM Alfred — Script de inicializacao (Windows)
REM ============================================
REM Duplo clique neste arquivo para iniciar o Alfred.

set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%venv
set LOG_FILE=%SCRIPT_DIR%data\alfred.log

REM Criar pasta de dados se nao existir
if not exist "%SCRIPT_DIR%data" mkdir "%SCRIPT_DIR%data"
if not exist "%SCRIPT_DIR%data\faces" mkdir "%SCRIPT_DIR%data\faces"
if not exist "%SCRIPT_DIR%data\memory" mkdir "%SCRIPT_DIR%data\memory"

REM Ativar virtualenv
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo Erro: virtualenv nao encontrado em %VENV_DIR%
    echo Execute o instalador primeiro: install.bat
    pause
    exit /b 1
)

REM Verificar se o Ollama esta rodando
tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul 2>&1
if errorlevel 1 (
    echo Iniciando Ollama em background...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
)

REM Aguardar Ollama ficar disponivel
set OLLAMA_READY=0
for /L %%i in (1,1,5) do (
    if !OLLAMA_READY!==0 (
        curl -s http://localhost:11434/api/tags >nul 2>&1
        if not errorlevel 1 (
            set OLLAMA_READY=1
        ) else (
            echo Aguardando Ollama iniciar... (tentativa %%i/5)
            timeout /t 3 /nobreak >nul
        )
    )
)

REM Iniciar o Alfred
echo [%date% %time%] Iniciando Alfred... >> "%LOG_FILE%"
cd /d "%SCRIPT_DIR%"
python -m alfred
pause
