@echo off
REM ============================================
REM Luna — Script de Inicialização (Windows)
REM ============================================

cd /d "%~dp0"

echo.
echo 🌙 Luna — Assistente Pessoal de IA
echo ====================================

REM Verificar Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado. Execute install.bat primeiro.
    pause
    exit /b 1
)

REM Ativar venv se existir
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✅ Ambiente virtual ativado
) else (
    echo ⚠️  Ambiente virtual não encontrado.
)

REM Verificar Ollama
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama encontrado
) else (
    echo ⚠️  Ollama não encontrado. Instale em: https://ollama.com
)

REM Modo headless (sem janela do terminal)
if "%1"=="--headless" (
    echo 🔇 Iniciando em modo headless...
    start /B pythonw -m luna --headless
    echo    Luna iniciada em background.
    timeout /t 3
    exit /b 0
)

echo.
echo 🚀 Iniciando Luna...
echo.
python -m luna %*

if %errorlevel% neq 0 (
    echo.
    echo ❌ Erro ao iniciar Luna.
    pause
)
