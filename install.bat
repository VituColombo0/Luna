@echo off
REM ═══════════════════════════════════════════════════════════
REM Alfred — Instalador Completo (Windows)
REM ═══════════════════════════════════════════════════════════
REM Este script faz TUDO para você:
REM   1. Verifica Python 3.10+
REM   2. Cria ambiente virtual
REM   3. Instala dependências
REM   4. Instala Ollama
REM   5. Baixa o modelo de IA
REM   6. Gera configuração
REM   7. Configura auto-start
REM ═══════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

echo.
echo ╔══════════════════════════════════════════════╗
echo ║  🧠 Alfred — Instalador Automatico          ║
echo ║  Assistente Pessoal de IA Local              ║
echo ╚══════════════════════════════════════════════╝
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM ─── Verificar Python ─────────────────────────────────────
echo [1/7] Verificando Python...

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python nao encontrado.
    echo Baixe em: https://www.python.org/downloads/
    echo IMPORTANTE: Marque "Add Python to PATH" durante a instalação.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo ✅ Python %PYVER% encontrado

REM ─── Ambiente Virtual ─────────────────────────────────────
echo.
echo [2/7] Criando ambiente virtual...

if exist "venv\Scripts\activate.bat" (
    echo ℹ  Ambiente virtual ja existe. Reutilizando.
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Erro ao criar ambiente virtual.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat
pip install --upgrade pip setuptools wheel -q >nul 2>&1
echo ✅ Ambiente virtual ativado

REM ─── Dependências Python ──────────────────────────────────
echo.
echo [3/7] Instalando dependencias Python...

echo ℹ  Instalando dependencias essenciais...
pip install -r requirements-core.txt -q 2>&1 | findstr /V "already satisfied"
echo ✅ Dependencias essenciais instaladas

echo.
echo Modulos opcionais:
echo   [1] Memoria de longo prazo (ChromaDB) ~1.5GB
echo   [2] Visao computacional (OpenCV) ~500MB
echo   [3] Instalar tudo
echo   [4] Pular opcionais
echo.
set /p optional_choice="Escolha [1/2/3/4] (padrao: 3): "
if "%optional_choice%"=="" set optional_choice=3

if "%optional_choice%"=="1" (
    pip install -r requirements-memory.txt -q 2>&1 | findstr /V "already satisfied"
    echo ✅ Memoria instalada
)
if "%optional_choice%"=="2" (
    pip install -r requirements-vision.txt -q 2>&1 | findstr /V "already satisfied"
    echo ✅ Visao instalada
)
if "%optional_choice%"=="3" (
    pip install -r requirements-full.txt -q 2>&1 | findstr /V "already satisfied"
    echo ✅ Todos os modulos instalados
)

REM ─── Ollama ───────────────────────────────────────────────
echo.
echo [4/7] Configurando Ollama...

where ollama >nul 2>&1
if errorlevel 1 (
    echo ℹ  Ollama nao encontrado.
    echo    Baixe e instale em: https://ollama.ai/download
    echo    Depois execute este script novamente.
    echo.
    set /p dummy="Pressione Enter apos instalar o Ollama..."
)

REM Verificar se Ollama está rodando
tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul 2>&1
if errorlevel 1 (
    echo ℹ  Iniciando Ollama...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
)

REM ─── Modelo de IA ─────────────────────────────────────────
echo.
echo [5/7] Baixando modelo de IA...
echo.
echo Escolha o modelo:
echo   [1] llama3.1   — Inteligente e versátil (8B) ^<-- Recomendado
echo   [2] llama3.2   — Equilibrado (4.7GB RAM)
echo   [3] mistral    — Potente (4.1GB RAM)
echo.
set /p model_choice="Escolha [1/2/3] (padrao: 1): "
if "%model_choice%"=="" set model_choice=1

if "%model_choice%"=="1" set MODEL=llama3.1
if "%model_choice%"=="2" set MODEL=llama3.2
if "%model_choice%"=="3" set MODEL=mistral
if not defined MODEL set MODEL=llama3.1

ollama list 2>nul | findstr /i "%MODEL%" >nul 2>&1
if errorlevel 1 (
    echo ℹ  Baixando %MODEL%... (pode demorar)
    ollama pull %MODEL%
    if errorlevel 1 (
        echo ❌ Erro ao baixar modelo.
        pause
        exit /b 1
    )
)
echo ✅ Modelo %MODEL% pronto

echo ℹ  Baixando modelo de visao (moondream)...
ollama list 2>nul | findstr /i "moondream" >nul 2>&1
if errorlevel 1 (
    ollama pull moondream
)
echo ✅ Modelo moondream pronto

REM ─── Configuração ─────────────────────────────────────────
echo.
echo [6/7] Configurando seu perfil...

if exist "config\config.yaml" (
    set /p recreate="config.yaml ja existe. Recriar? [s/N]: "
    if /i not "!recreate!"=="s" goto skip_config
)

echo.
set /p user_name="Seu nome: "
if "%user_name%"=="" set user_name=Usuario

set /p nickname="Apelido: "
if "%nickname%"=="" set nickname=%user_name%

set /p bio="Descricao sobre voce: "
if "%bio%"=="" set bio=Entusiasta de tecnologia.

echo.
echo Voz do Alfred:
echo   [1] Masculina (Antonio)
echo   [2] Feminina (Francisca)
set /p voice_choice="Escolha [1/2] (padrao: 1): "
if "%voice_choice%"=="2" (set TTS_VOICE=pt-BR-FranciscaNeural) else (set TTS_VOICE=pt-BR-AntonioNeural)

(
echo # Alfred — Configuracao Pessoal
echo # Gerado por install.bat
echo.
echo user:
echo   name: "%user_name%"
echo   nickname: "%nickname%"
echo   bio: "%bio%"
echo.
echo llm:
echo   model: "%MODEL%"
echo   vision_model: "moondream"
echo   temperature: 0.7
echo   ollama_host: "http://localhost:11434"
echo.
echo voice:
echo   stt_model: "base"
echo   stt_language: "pt"
echo   tts_engine: "edge-tts"
echo   tts_voice: "%TTS_VOICE%"
echo   wake_word: "alfred"
echo.
echo vision:
echo   enabled: true
echo   camera_index: 0
echo   face_recognition: true
echo   faces_dir: "data/faces"
echo.
echo memory:
echo   enabled: true
echo   db_path: "data/memory"
echo   max_context_items: 5
echo   auto_save: true
echo.
echo actions:
echo   enabled: true
echo   allowed_paths:
echo     - "~/Documents"
echo     - "~/Downloads"
echo     - "~/Videos"
echo     - "~/Music"
echo     - "~/Desktop"
echo   allow_browser: true
echo   allow_system_commands: false
) > config\config.yaml

echo ✅ Configuracao salva

:skip_config

REM ─── Auto-Start ───────────────────────────────────────────
echo.
echo [7/7] Configurando auto-start...
echo.
echo Iniciar Alfred automaticamente com o Windows?
echo   [1] Sim (adicionar na pasta Startup)
echo   [2] Nao
set /p autostart_choice="Escolha [1/2] (padrao: 1): "
if "%autostart_choice%"=="" set autostart_choice=1

if "%autostart_choice%"=="1" (
    set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

    (
    echo @echo off
    echo cd /d "%SCRIPT_DIR%"
    echo call venv\Scripts\activate.bat
    echo start /min "" ollama serve
    echo timeout /t 5 /nobreak ^>nul
    echo python -m alfred
    ) > "!STARTUP_DIR!\Alfred.bat"

    echo ✅ Auto-start configurado
    echo ℹ  Alfred vai iniciar com o Windows
    echo ℹ  Para remover: delete "!STARTUP_DIR!\Alfred.bat"
)

REM ─── Finalização ──────────────────────────────────────────
echo.
echo ╔══════════════════════════════════════════════╗
echo ║  ✅ Instalacao concluida com sucesso!        ║
echo ╚══════════════════════════════════════════════╝
echo.
echo   Para iniciar agora, execute:
echo     start.bat
echo.
echo   Diga "Alfred" e faca sua primeira pergunta!
echo.

pause
