@echo off
REM ═══════════════════════════════════════════════════════════
REM Alfred — Instalador Completo (Windows)
REM ═══════════════════════════════════════════════════════════
REM Este script faz TUDO para voce:
REM   1. Instala Python se necessario (via winget)
REM   2. Cria ambiente virtual
REM   3. Instala dependencias
REM   4. Instala Ollama
REM   5. Baixa o modelo de IA
REM   6. Gera configuracao
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
    echo ⚠  Python nao encontrado. Tentando instalar automaticamente...
    echo.

    REM Tentar via winget (Windows 10+)
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo ℹ  Instalando Python 3.11 via winget...
        winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
        if errorlevel 1 (
            echo ❌ Falha ao instalar Python via winget.
            goto :manual_python
        )

        REM Atualizar PATH para encontrar o Python recem-instalado
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

        python --version >nul 2>&1
        if errorlevel 1 (
            echo ⚠  Python instalado mas nao encontrado no PATH.
            echo    Feche e reabra o terminal e execute install.bat novamente.
            pause
            exit /b 1
        )
        echo ✅ Python instalado com sucesso
    ) else (
        :manual_python
        echo ❌ winget nao disponivel para instalacao automatica.
        echo.
        echo    Baixe Python manualmente em: https://www.python.org/downloads/
        echo    IMPORTANTE: Marque "Add Python to PATH" durante a instalacao.
        echo.
        echo    Apos instalar, execute este script novamente.
        pause
        exit /b 1
    )
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo ✅ Python %PYVER% encontrado

REM ─── Ambiente Virtual ─────────────────────────────────────
echo.
echo [2/7] Criando ambiente virtual...

if exist "venv\Scripts\activate.bat" (
    REM Verificar se o venv funciona
    venv\Scripts\python.exe --version >nul 2>&1
    if errorlevel 1 (
        echo ⚠  Ambiente virtual corrompido. Recriando...
        rmdir /s /q venv
        python -m venv venv
        if errorlevel 1 (
            echo ❌ Erro ao criar ambiente virtual.
            pause
            exit /b 1
        )
    ) else (
        echo ℹ  Ambiente virtual ja existe. Reutilizando.
    )
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

REM ─── Dependencias Python ──────────────────────────────────
echo.
echo [3/7] Instalando dependencias Python...

echo ℹ  Instalando dependencias essenciais...
pip install -r requirements-core.txt 2>&1 | findstr /V "already satisfied"
if errorlevel 1 (
    echo ⚠  Algumas dependencias podem ter falhado. Continuando...
)
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
    pip install -r requirements-memory.txt 2>&1 | findstr /V "already satisfied"
    echo ✅ Memoria instalada
)
if "%optional_choice%"=="2" (
    pip install -r requirements-vision.txt 2>&1 | findstr /V "already satisfied"
    echo ✅ Visao instalada
)
if "%optional_choice%"=="3" (
    pip install -r requirements-full.txt 2>&1 | findstr /V "already satisfied"
    echo ✅ Todos os modulos instalados
)

REM ─── Ollama ───────────────────────────────────────────────
echo.
echo [4/7] Configurando Ollama...

where ollama >nul 2>&1
if errorlevel 1 (
    echo ⚠  Ollama nao encontrado. Tentando instalar...
    echo.

    REM Tentar via winget
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo ℹ  Instalando Ollama via winget...
        winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
        if not errorlevel 1 (
            echo ✅ Ollama instalado
            REM Atualizar PATH
            set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
        ) else (
            echo ⚠  Falha na instalacao automatica.
            echo    Baixe em: https://ollama.com/download
            echo    Depois execute este script novamente.
            echo.
            set /p dummy="Pressione Enter apos instalar o Ollama..."
        )
    ) else (
        echo ℹ  Baixe e instale o Ollama em: https://ollama.com/download
        echo    Depois execute este script novamente.
        echo.
        set /p dummy="Pressione Enter apos instalar o Ollama..."
    )
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
echo   [1] llama3.1   — Inteligente e versatil (8B) ^<-- Recomendado
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

REM Garantir que o diretório config existe
if not exist "config" mkdir config

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

REM Usar Python para gerar o config em UTF-8 (evita problemas de encoding do cmd)
venv\Scripts\python.exe _generate_config.py "%user_name%" "%nickname%" "%bio%" "%MODEL%" "%TTS_VOICE%"

echo ✅ Configuracao salva

:skip_config

REM Garantir que as pastas de dados existem
if not exist "data\faces" mkdir "data\faces"
if not exist "data\memory" mkdir "data\memory"

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

REM ─── Verificação Final ────────────────────────────────────
echo.
echo Verificacao final...
venv\Scripts\python.exe -c "import yaml, numpy, pygame, edge_tts, ollama, rich, psutil" 2>nul
if errorlevel 1 (
    echo ⚠  Alguns pacotes essenciais podem estar faltando.
    echo    O Alfred tentara funcionar sem eles.
) else (
    echo ✅ Todos os pacotes essenciais verificados
)

REM ─── Finalizacao ──────────────────────────────────────────
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
