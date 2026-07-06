#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Luna — Instalador Completo (Linux)
# ═══════════════════════════════════════════════════════════
# Este script faz TUDO para você:
#   1. Instala Python e dependências do sistema
#   2. Cria ambiente virtual Python
#   3. Instala pacotes Python
#   4. Instala e configura o Ollama
#   5. Baixa o modelo de IA (modelo-laob)
#   6. Gera configuração personalizada
#   7. Configura auto-start no boot
#
# Uso: bash install.sh
# ═══════════════════════════════════════════════════════════

# ─── Cores e Formatação ────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

ok()   { echo -e "  ${GREEN}✅ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; exit 1; }
info() { echo -e "  ${CYAN}ℹ  $1${NC}"; }
step() { echo -e "\n${BOLD}${MAGENTA}━━━ [$1/$TOTAL_STEPS] $2 ━━━${NC}"; }

TOTAL_STEPS=7
MODEL="modelo-laob"

# ─── Banner ────────────────────────────────────────────────
echo ""
echo -e "${MAGENTA}  ╔═══════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}  ║${NC}                                           ${MAGENTA}║${NC}"
echo -e "${MAGENTA}  ║${NC}   ${BOLD}🌙  L U N A${NC}  ${DIM}— Instalador${NC}              ${MAGENTA}║${NC}"
echo -e "${MAGENTA}  ║${NC}   ${DIM}Inteligência Local • Controle Total${NC}   ${MAGENTA}║${NC}"
echo -e "${MAGENTA}  ║${NC}                                           ${MAGENTA}║${NC}"
echo -e "${MAGENTA}  ╚═══════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ─── Detectar gerenciador de pacotes ───────────────────────
PKG_MANAGER=""
INSTALL_CMD=""
UPDATE_CMD=""

if command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
    INSTALL_CMD="sudo apt install -y"
    UPDATE_CMD="sudo apt update"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    INSTALL_CMD="sudo dnf install -y"
    UPDATE_CMD="sudo dnf check-update || true"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    INSTALL_CMD="sudo pacman -S --noconfirm"
    UPDATE_CMD="sudo pacman -Sy"
elif command -v zypper &> /dev/null; then
    PKG_MANAGER="zypper"
    INSTALL_CMD="sudo zypper install -y"
    UPDATE_CMD="sudo zypper refresh"
else
    warn "Gerenciador de pacotes não detectado. Instale as dependências manualmente."
fi

# ─── Atualizar repositórios do sistema ─────────────────────
if [ -n "$UPDATE_CMD" ]; then
    info "Atualizando lista de pacotes do sistema..."
    $UPDATE_CMD > /dev/null 2>&1 || warn "Não foi possível atualizar pacotes. Continuando..."
fi

# ═══════════════════════════════════════════════════════════
# PASSO 0: Instalar Python se necessário
# ═══════════════════════════════════════════════════════════
_install_python_if_missing() {
    local found=""
    for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" &> /dev/null; then
            local ver
            ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" = "3" ] && [ "$minor" -ge 10 ] 2>/dev/null; then
                found="$cmd"
                break
            fi
        fi
    done

    if [ -n "$found" ]; then
        echo "$found"
        return 0
    fi

    warn "Python 3.10+ não encontrado. Instalando automaticamente..."

    if [ -z "$PKG_MANAGER" ]; then
        fail "Impossível instalar Python: nenhum gerenciador de pacotes detectado.\n    Instale manualmente: https://www.python.org/downloads/"
    fi

    case $PKG_MANAGER in
        apt)
            $INSTALL_CMD python3.11 python3.11-venv python3.11-dev python3-pip 2>/dev/null \
                || $INSTALL_CMD python3 python3-venv python3-dev python3-pip 2>/dev/null \
                || fail "Não foi possível instalar Python."
            ;;
        dnf)
            $INSTALL_CMD python3.11 python3.11-devel python3-pip 2>/dev/null \
                || $INSTALL_CMD python3 python3-devel python3-pip 2>/dev/null \
                || fail "Não foi possível instalar Python."
            ;;
        pacman)
            $INSTALL_CMD python python-pip 2>/dev/null \
                || fail "Não foi possível instalar Python."
            ;;
        zypper)
            $INSTALL_CMD python311 python311-devel python3-pip 2>/dev/null \
                || $INSTALL_CMD python3 python3-devel python3-pip 2>/dev/null \
                || fail "Não foi possível instalar Python."
            ;;
    esac

    for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" &> /dev/null; then
            local ver
            ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" = "3" ] && [ "$minor" -ge 10 ] 2>/dev/null; then
                echo "$cmd"
                return 0
            fi
        fi
    done

    fail "Python 3.10+ ainda não encontrado após instalação. Instale manualmente."
}

PYTHON_CMD=$(_install_python_if_missing)
ok "Python encontrado: $($PYTHON_CMD --version)"

# ═══════════════════════════════════════════════════════════
# PASSO 1: Dependências do Sistema
# ═══════════════════════════════════════════════════════════
step 1 "Instalando dependências do sistema"

if [ -n "$PKG_MANAGER" ]; then
    case $PKG_MANAGER in
        apt)
            PACKAGES="portaudio19-dev python3-dev python3-venv python3-pip ffmpeg \
                      build-essential cmake curl git libopenblas-dev libasound2-dev \
                      xdotool xclip wmctrl"
            ;;
        dnf)
            PACKAGES="portaudio-devel python3-devel python3-pip ffmpeg \
                      gcc gcc-c++ cmake curl git openblas-devel alsa-lib-devel"
            ;;
        pacman)
            PACKAGES="portaudio python python-pip ffmpeg base-devel cmake curl git openblas"
            ;;
        zypper)
            PACKAGES="portaudio-devel python3-devel python3-pip ffmpeg \
                      gcc gcc-c++ cmake curl git openblas-devel alsa-devel"
            ;;
    esac

    info "Usando $PKG_MANAGER para instalar pacotes..."
    $INSTALL_CMD $PACKAGES 2>/dev/null || warn "Algumas dependências podem já estar instaladas ou indisponíveis."
    ok "Dependências do sistema instaladas"
else
    warn "Instale manualmente: portaudio, ffmpeg, cmake, build-essential, curl, git"
fi

# ═══════════════════════════════════════════════════════════
# PASSO 2: Ambiente Virtual Python
# ═══════════════════════════════════════════════════════════
step 2 "Criando ambiente virtual Python"

if [ -d "venv" ]; then
    if [ -f "venv/bin/activate" ] && "venv/bin/python" --version &>/dev/null; then
        info "Ambiente virtual já existe e está funcional. Reutilizando."
    else
        warn "Ambiente virtual existente está corrompido. Recriando..."
        rm -rf venv
        $PYTHON_CMD -m venv venv || fail "Não foi possível criar o venv."
    fi
else
    $PYTHON_CMD -m venv venv || fail "Não foi possível criar o venv."
fi

source venv/bin/activate
ok "Ambiente virtual ativado"

pip install --upgrade pip setuptools wheel -q 2>/dev/null
if [ $? -ne 0 ]; then
    warn "Falha ao atualizar pip. Tentando continuar com a versão atual..."
else
    ok "pip atualizado"
fi

# ═══════════════════════════════════════════════════════════
# PASSO 3: Instalar Dependências Python
# ═══════════════════════════════════════════════════════════
step 3 "Instalando dependências Python"

info "Instalando dependências essenciais..."
pip install -r requirements-core.txt 2>&1 | tail -5
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    fail "Erro ao instalar dependências essenciais. Verifique os logs acima."
fi
ok "Dependências essenciais instaladas"

info "Instalando todos os módulos opcionais..."
pip install -r requirements-full.txt 2>&1 | tail -5
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    warn "Alguns módulos opcionais podem não ter sido instalados. A Luna funcionará sem eles."
else
    ok "Todos os módulos instalados"
fi

# ═══════════════════════════════════════════════════════════
# PASSO 4: Instalar e Configurar Ollama
# ═══════════════════════════════════════════════════════════
step 4 "Configurando Ollama"

if ! command -v curl &> /dev/null; then
    warn "curl não encontrado. Tentando instalar..."
    if [ -n "$INSTALL_CMD" ]; then
        $INSTALL_CMD curl 2>/dev/null || fail "Não foi possível instalar curl."
    else
        fail "curl é necessário para instalar o Ollama. Instale manualmente."
    fi
fi

if command -v ollama &> /dev/null; then
    ok "Ollama já instalado"
else
    info "Instalando Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh || fail "Erro ao instalar o Ollama"
    ok "Ollama instalado"
fi

# Verificar se o serviço está rodando
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    info "Iniciando Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 5
fi

# Verificar se o Ollama está respondendo
OLLAMA_OK=false
for i in 1 2 3 4 5; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        OLLAMA_OK=true
        break
    fi
    info "Aguardando Ollama iniciar... (tentativa $i/5)"
    sleep 3
done

if [ "$OLLAMA_OK" = false ]; then
    warn "Ollama não está respondendo. Pode ser necessário iniciar manualmente: ollama serve"
fi

# ═══════════════════════════════════════════════════════════
# PASSO 5: Baixar Modelo de IA
# ═══════════════════════════════════════════════════════════
step 5 "Baixando modelo de IA ($MODEL)"

# Verificar se o modelo já existe
if ollama list 2>/dev/null | grep -q "$MODEL"; then
    ok "Modelo $MODEL já baixado"
else
    info "Baixando $MODEL... (isso pode demorar)"
    ollama pull "$MODEL" || fail "Erro ao baixar o modelo $MODEL"
    ok "Modelo $MODEL baixado"
fi

if ollama list 2>/dev/null | grep -q "moondream"; then
    ok "Modelo moondream já baixado"
else
    info "Baixando modelo de visão moondream..."
    ollama pull "moondream" || warn "Erro ao baixar moondream. A visão pode não funcionar."
    ok "Modelo moondream baixado"
fi

# ═══════════════════════════════════════════════════════════
# PASSO 6: Configuração Personalizada
# ═══════════════════════════════════════════════════════════
step 6 "Configurando seu perfil"

mkdir -p config

if [ -f "config/config.yaml" ]; then
    echo ""
    read -p "config.yaml já existe. Recriar? [s/N]: " recreate
    recreate=${recreate:-N}
    if [[ ! "$recreate" =~ ^[sS]$ ]]; then
        info "Mantendo configuração existente."
    fi
fi

if [ ! -f "config/config.yaml" ] || [[ "$recreate" =~ ^[sS]$ ]]; then
    echo ""
    read -p "Seu nome: " user_name
    user_name=${user_name:-"Usuário"}

    read -p "Como quer ser chamado (apelido): " nickname
    nickname=${nickname:-$user_name}

    read -p "Uma breve descrição sobre você: " bio
    bio=${bio:-"Entusiasta de tecnologia."}

    # Gerar config.yaml
    cat > config/config.yaml << YAML
# ============================================
# Luna — Configuração Pessoal
# ============================================
# Gerado automaticamente por install.sh

# --- Seu Perfil ---
user:
  name: "$user_name"
  nickname: "$nickname"
  bio: "$bio"

# --- Modelo de Linguagem ---
llm:
  model: "$MODEL"
  vision_model: "moondream"
  temperature: 0.7
  max_tokens: 200
  ollama_host: "http://localhost:11434"

# --- Voz ---
voice:
  stt_model: "base"
  stt_language: "pt"
  tts_engine: "edge-tts"
  tts_voice: "pt-BR-ThalitaMultilingualNeural"
  tts_rate: "+15%"
  wake_word: "luna"

# --- Visão ---
vision:
  enabled: true
  camera_index: 0
  face_recognition: true
  faces_dir: "data/faces"

# --- Memória ---
memory:
  enabled: true
  db_path: "data/memory"
  max_context_items: 5
  auto_save: true

# --- Ações ---
actions:
  enabled: true
  allowed_paths:
    - "~"
    - "~/Documents"
    - "~/Downloads"
    - "~/Videos"
    - "~/Music"
    - "~/Desktop"
  allow_browser: true
  allow_system_commands: true
YAML

    ok "Configuração salva em config/config.yaml"
fi

# Garantir que as pastas de dados existem
mkdir -p data/faces data/memory

# ═══════════════════════════════════════════════════════════
# PASSO 7: Auto-Start
# ═══════════════════════════════════════════════════════════
step 7 "Configurando auto-start"

echo ""
echo -e "${BOLD}Iniciar Luna automaticamente no boot?${NC}"
echo -e "  ${CYAN}[1]${NC} Sim, via autostart do desktop ${GREEN}← Recomendado${NC}"
echo -e "  ${CYAN}[2]${NC} Sim, via systemd (headless/servidor)"
echo -e "  ${CYAN}[3]${NC} Não configurar agora"
echo ""
read -p "Escolha [1/2/3] (padrão: 1): " autostart_choice
autostart_choice=${autostart_choice:-1}

case $autostart_choice in
    1)
        AUTOSTART_DIR="$HOME/.config/autostart"
        mkdir -p "$AUTOSTART_DIR"

        cat > "$AUTOSTART_DIR/luna.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=Luna - Assistente Pessoal de IA
Comment=Assistente pessoal de IA local
Exec=$SCRIPT_DIR/start.sh
Terminal=false
Icon=utilities-terminal
Categories=Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=10
DESKTOP

        chmod +x "$SCRIPT_DIR/start.sh"
        ok "Auto-start configurado (desktop)"
        info "Luna vai iniciar automaticamente no próximo login"
        ;;
    2)
        SYSTEMD_DIR="$HOME/.config/systemd/user"
        mkdir -p "$SYSTEMD_DIR"

        cat > "$SYSTEMD_DIR/luna.service" << SERVICE
[Unit]
Description=Luna - Assistente Pessoal de IA
After=network.target sound.target
Wants=pulseaudio.service

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStartPre=/bin/bash -c 'pgrep ollama || ollama serve &'
ExecStartPre=/bin/sleep 3
ExecStart=$SCRIPT_DIR/venv/bin/python -m luna
Restart=on-failure
RestartSec=10
Environment=DISPLAY=:0
Environment=PULSE_SERVER=unix:/run/user/%U/pulse/native

[Install]
WantedBy=default.target
SERVICE

        systemctl --user daemon-reload
        systemctl --user enable luna.service
        ok "Serviço systemd configurado"
        info "Iniciar agora: systemctl --user start luna"
        ;;
    3)
        info "Auto-start não configurado. Execute manualmente: ./start.sh"
        ;;
esac

# ═══════════════════════════════════════════════════════════
# Verificação Final
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}Verificação final...${NC}"

IMPORT_ERRORS=""
for pkg in yaml numpy pygame sounddevice edge_tts ollama rich psutil faster_whisper pynput; do
    if ! venv/bin/python -c "import $pkg" 2>/dev/null; then
        IMPORT_ERRORS="$IMPORT_ERRORS $pkg"
    fi
done

if [ -n "$IMPORT_ERRORS" ]; then
    warn "Pacotes não importados:$IMPORT_ERRORS"
    info "Módulos opcionais. A Luna funcionará sem eles."
else
    ok "Todos os pacotes essenciais verificados"
fi

# ═══════════════════════════════════════════════════════════
# Finalização
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${MAGENTA}  ╔═══════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}  ║${NC}                                           ${MAGENTA}║${NC}"
echo -e "${MAGENTA}  ║${NC}   ${BOLD}✅ Instalação concluída com sucesso!${NC}    ${MAGENTA}║${NC}"
echo -e "${MAGENTA}  ║${NC}                                           ${MAGENTA}║${NC}"
echo -e "${MAGENTA}  ╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Para iniciar agora:"
echo -e "    ${CYAN}cd $SCRIPT_DIR && ./start.sh${NC}"
echo ""
echo -e "  ${DIM}Diga \"Luna\" e faça sua primeira pergunta! 🎤${NC}"
echo ""
