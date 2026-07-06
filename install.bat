@echo off
REM ═══════════════════════════════════════════════════════════
REM Luna — Instalador Completo (Windows)
REM ═══════════════════════════════════════════════════════════
REM Este script faz TUDO para voce:
REM   1. Instala Python se necessario (via winget)
REM   2. Cria ambiente virtual
REM   3. Instala dependencias
REM   4. Instala Ollama
REM   5. Baixa o modelo de IA (modelo-laob)
REM   6. Gera configuracao
REM   7. Configura auto-start
REM ═══════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

echo.
echo   ╔═══════════════════════════════════════════╗
echo   ║                                           ║
echo   ║   🌙  L U N A  — Instalador               ║
echo   ║   Inteligencia Local · Controle Total     ║
echo   ║                                           ║
echo   ╚═══════════════════════════════════════════╝
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"
set MODEL=modelo-laob

REM ─── Verificar Python ─────────────────────────────────────
echo [1/7] Verificando Python...

python --version >nul 2>&1
if errorlevel 1 (
    echo   ⚠  Python nao encontrado. Tentando instalar automaticamente...
    echo.

    where winget >nul 2>&1
    if not errorlevel 1 (
        echo   ℹ  Instalando Python 3.11 via winget...
        winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
        if errorlevel 1 (
            echo   ❌ Falha ao instalar Python via winget.
            echo      Baixe em: https://www.python.org/downloads/
            echo      IMPORTANTE: Marque "Add Python to PATH"
            pause
            exit /b 1
        )

        set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

        python --version >nul 2>&1
        if errorlevel 1 (
            echo   ⚠  Python instalado mas nao encontrado no PATH.
            echo      Feche e reabra o terminal e execute install.bat novamente.
            pause
            exit /b 1
        )
        echo   ✅ Python instalado com sucesso
    ) else (
        echo   ❌ winget nao disponivel.
        echo      Baixe Python em: https://www.python.org/downloads/
        echo      Marque "Add Python to PATH" durante instalacao.
        pause
        exit /b 1
    )
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   ✅ Python %PYVER% encontrado

REM ─── Ambiente Virtual ─────────────────────────────────────
echo.
echo [2/7] Criando ambiente virtual...

if exist "venv\Scripts\activate.bat" (
    venv\Scripts\python.exe --version >nul 2>&1
    if errorlevel 1 (
        echo   ⚠  Ambiente virtual corrompido. Recriando...
        rmdir /s /q venv
        python -m venv venv
        if errorlevel 1 (
            echo   ❌ Erro ao criar ambiente virtual.
            pause
            exit /b 1
        )
    ) else (
        echo   ℹ  Ambiente virtual ja existe. Reutilizando.
    )
) else (
    python -m venv venv
    if errorlevel 1 (
        echo   ❌ Erro ao criar ambiente virtual.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat
pip install --upgrade pip setuptools wheel -q >nul 2>&1
echo   ✅ Ambiente virtual ativado

REM ─── Dependencias Python ──────────────────────────────────
echo.
echo [3/7] Instalando dependencias Python...

echo   ℹ  Instalando dependencias essenciais...
pip install -r requirements-core.txt 2>&1 | findstr /V "already satisfied"
if errorlevel 1 (
    echo   ⚠  Algumas dependencias podem ter falhado. Continuando...
)
echo   ✅ Dependencias essenciais instaladas

echo   ℹ  Instalando modulos opcionais...
pip install -r requirements-full.txt 2>&1 | findstr /V "already satisfied"
echo   ✅ Todos os modulos instalados

REM ─── Ollama ───────────────────────────────────────────────
echo.
echo [4/7] Configurando Ollama...

where ollama >nul 2>&1
if errorlevel 1 (
    echo   ⚠  Ollama nao encontrado. Tentando instalar...

    where winget >nul 2>&1
    if not errorlevel 1 (
        echo   ℹ  Instalando Ollama via winget...
        winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
        if not errorlevel 1 (
            echo   ✅ Ollama instalado
            set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
        ) else (
            echo   ⚠  Falha na instalacao automatica.
            echo      Baixe em: https://ollama.com/download
            set /p dummy="Pressione Enter apos instalar o Ollama..."
        )
    ) else (
        echo   ℹ  Baixe e instale o Ollama em: https://ollama.com/download
        set /p dummy="Pressione Enter apos instalar o Ollama..."
    )
)

REM Verificar se Ollama esta rodando
tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul 2>&1
if errorlevel 1 (
    echo   ℹ  Iniciando Ollama...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
)

REM ─── Modelo de IA ─────────────────────────────────────────
echo.
echo [5/7] Baixando modelo de IA (%MODEL%)...

ollama list 2>nul | findstr /i "%MODEL%" >nul 2>&1
if errorlevel 1 (
    echo   ℹ  Baixando %MODEL%... (pode demorar)
    ollama pull %MODEL%
    if errorlevel 1 (
        echo   ❌ Erro ao baixar modelo.
        pause
        exit /b 1
    )
)
echo   ✅ Modelo %MODEL% pronto

echo   ℹ  Baixando modelo de visao (moondream)...
ollama list 2>nul | findstr /i "moondream" >nul 2>&1
if errorlevel 1 (
    ollama pull moondream
)
echo   ✅ Modelo moondream pronto

REM ─── Configuracao ─────────────────────────────────────────
echo.
echo [6/7] Configurando seu perfil...

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

REM Usar Python para gerar o config em UTF-8
venv\Scripts\python.exe _generate_config.py "%user_name%" "%nickname%" "%bio%"

echo   ✅ Configuracao salva

:skip_config

REM Garantir que as pastas de dados existem
if not exist "data\faces" mkdir "data\faces"
if not exist "data\memory" mkdir "data\memory"

REM ─── Auto-Start ───────────────────────────────────────────
echo.
echo [7/7] Configurando auto-start...
echo.
echo Iniciar Luna automaticamente com o Windows?
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
    echo python -m luna
    ) > "!STARTUP_DIR!\Luna.bat"

    echo   ✅ Auto-start configurado
    echo   ℹ  Luna vai iniciar com o Windows
)

REM ─── Verificacao Final ────────────────────────────────────
echo.
echo Verificacao final...
venv\Scripts\python.exe -c "import yaml, numpy, pygame, edge_tts, ollama, rich, psutil" 2>nul
if errorlevel 1 (
    echo   ⚠  Alguns pacotes essenciais podem estar faltando.
) else (
    echo   ✅ Todos os pacotes essenciais verificados
)

REM ─── Finalizacao ──────────────────────────────────────────
echo.
echo   ╔═══════════════════════════════════════════╗
echo   ║                                           ║
echo   ║   ✅ Instalacao concluida com sucesso!    ║
echo   ║                                           ║
echo   ╚═══════════════════════════════════════════╝
echo.
echo   Para iniciar agora, execute:
echo     start.bat
echo.
echo   Diga "Luna" e faca sua primeira pergunta!
echo.

pause
