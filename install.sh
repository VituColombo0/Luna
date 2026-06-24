#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Alfred — Instalador Completo (Linux)
# ═══════════════════════════════════════════════════════════
# Este script faz TUDO para você:
#   1. Instala dependências do sistema (portaudio, etc.)
#   2. Cria ambiente virtual Python
#   3. Instala pacotes Python
#   4. Instala e configura o Ollama
#   5. Baixa o modelo de IA
#   6. Gera configuração personalizada
#   7. Configura auto-start no boot
#
# Uso: bash install.sh
# ═══════════════════════════════════════════════════════════

set -e

# ─── Cores e Formatação ────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

ok()   { echo -e "  ${GREEN}✅ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; exit 1; }
info() { echo -e "  ${CYAN}ℹ  $1${NC}"; }
step() { echo -e "\n${BOLD}${BLUE}[$1/$TOTAL_STEPS] $2${NC}"; }

TOTAL_STEPS=7

# ─── Banner ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}🧠 Alfred — Instalador Automático${NC}          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${DIM}Assistente Pessoal de IA Local${NC}              ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ─── Verificar Python ─────────────────────────────────────
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &> /dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oP '3\.\d+')
        major_minor=$(echo "$version" | cut -d. -f1,2)
        if [ "$(echo "$major_minor >= 3.10" | bc -l 2>/dev/null || echo 0)" = "1" ] || \
           [[ "$major_minor" == "3.10" ]] || [[ "$major_minor" == "3.11" ]] || \
           [[ "$major_minor" == "3.12" ]] || [[ "$major_minor" == "3.13" ]]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    fail "Python 3.10+ não encontrado. Instale com:\n    sudo apt install python3.11 python3.11-venv"
fi

ok "Python encontrado: $($PYTHON_CMD --version)"

# ═══════════════════════════════════════════════════════════
# PASSO 1: Dependências do Sistema
# ═══════════════════════════════════════════════════════════
step 1 "Instalando dependências do sistema..."

# Detectar gerenciador de pacotes
if command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
    PACKAGES="portaudio19-dev python3-dev python3-venv ffmpeg"
    INSTALL_CMD="sudo apt install -y"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    PACKAGES="portaudio-devel python3-devel ffmpeg"
    INSTALL_CMD="sudo dnf install -y"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    PACKAGES="portaudio python ffmpeg"
    INSTALL_CMD="sudo pacman -S --noconfirm"
else
    warn "Gerenciador de pacotes não detectado. Instale manualmente: portaudio, ffmpeg"
    PACKAGES=""
fi

if [ -n "$PACKAGES" ]; then
    info "Usando $PKG_MANAGER para instalar: $PACKAGES"
    $INSTALL_CMD $PACKAGES 2>/dev/null || warn "Algumas dependências podem já estar instaladas"
    ok "Dependências do sistema instaladas"
fi

# ═══════════════════════════════════════════════════════════
# PASSO 2: Ambiente Virtual Python
# ═══════════════════════════════════════════════════════════
step 2 "Criando ambiente virtual Python..."

if [ -d "venv" ]; then
    info "Ambiente virtual já existe. Reutilizando."
else
    $PYTHON_CMD -m venv venv || fail "Não foi possível criar o venv. Instale: sudo apt install python3-venv"
fi

source venv/bin/activate
ok "Ambiente virtual ativado"

# Atualizar pip
pip install --upgrade pip setuptools wheel -q
ok "pip atualizado"

# ═══════════════════════════════════════════════════════════
# PASSO 3: Instalar Dependências Python
# ═══════════════════════════════════════════════════════════
step 3 "Instalando dependências Python..."

# Instalar core primeiro (obrigatórias)
info "Instalando dependências essenciais..."
pip install -r requirements-core.txt -q 2>&1 | tail -1
ok "Dependências essenciais instaladas"

# Perguntar sobre opcionais
echo ""
echo -e "${BOLD}Módulos opcionais:${NC}"
echo -e "  ${CYAN}[1]${NC} Memória de longo prazo (ChromaDB + Sentence Transformers) ~1.5GB"
echo -e "  ${CYAN}[2]${NC} Visão computacional (OpenCV + Face Recognition) ~500MB"
echo -e "  ${CYAN}[3]${NC} Instalar tudo"
echo -e "  ${CYAN}[4]${NC} Pular opcionais (pode instalar depois)"
echo ""
read -p "Escolha [1/2/3/4] (padrão: 3): " optional_choice
optional_choice=${optional_choice:-3}

case $optional_choice in
    1)
        info "Instalando módulo de memória..."
        pip install -r requirements-memory.txt -q 2>&1 | tail -1
        ok "Memória instalada"
        ;;
    2)
        info "Instalando módulo de visão..."
        pip install -r requirements-vision.txt -q 2>&1 | tail -1
        ok "Visão instalada"
        ;;
    3)
        info "Instalando todos os módulos..."
        pip install -r requirements-full.txt -q 2>&1 | tail -1
        ok "Todos os módulos instalados"
        ;;
    4)
        info "Pulando módulos opcionais."
        ;;
esac

# ═══════════════════════════════════════════════════════════
# PASSO 4: Instalar e Configurar Ollama
# ═══════════════════════════════════════════════════════════
step 4 "Configurando Ollama..."

if command -v ollama &> /dev/null; then
    ok "Ollama já instalado"
else
    info "Instalando Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh || fail "Erro ao instalar o Ollama"
    ok "Ollama instalado"
fi

# Verificar se o serviço está rodando
if ! pgrep -x "ollama" > /dev/null; then
    info "Iniciando Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# ═══════════════════════════════════════════════════════════
# PASSO 5: Baixar Modelo de IA
# ═══════════════════════════════════════════════════════════
step 5 "Baixando modelo de IA..."

echo ""
echo -e "${BOLD}Escolha o modelo:${NC}"
echo -e "  ${CYAN}[1]${NC} phi3       — Leve e rápido (2.3GB RAM) ${GREEN}← Recomendado${NC}"
echo -e "  ${CYAN}[2]${NC} llama3.2   — Equilibrado (4.7GB RAM)"
echo -e "  ${CYAN}[3]${NC} mistral    — Potente (4.1GB RAM)"
echo -e "  ${CYAN}[4]${NC} gemma2     — Google, bom em PT-BR (5.4GB RAM)"
echo ""
read -p "Escolha [1/2/3/4] (padrão: 1): " model_choice
model_choice=${model_choice:-1}

case $model_choice in
    1) MODEL="phi3" ;;
    2) MODEL="llama3.2" ;;
    3) MODEL="mistral" ;;
    4) MODEL="gemma2" ;;
    *) MODEL="phi3" ;;
esac

# Verificar se o modelo já existe
if ollama list 2>/dev/null | grep -q "$MODEL"; then
    ok "Modelo $MODEL já baixado"
else
    info "Baixando $MODEL... (isso pode demorar)"
    ollama pull "$MODEL" || fail "Erro ao baixar o modelo $MODEL"
    ok "Modelo $MODEL baixado"
fi

# ═══════════════════════════════════════════════════════════
# PASSO 6: Configuração Personalizada
# ═══════════════════════════════════════════════════════════
step 6 "Configurando seu perfil..."

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

    echo ""
    echo -e "${BOLD}Voz do Alfred:${NC}"
    echo -e "  ${CYAN}[1]${NC} Masculina (Antonio) ${GREEN}← Padrão${NC}"
    echo -e "  ${CYAN}[2]${NC} Feminina (Francisca)"
    read -p "Escolha [1/2] (padrão: 1): " voice_choice
    voice_choice=${voice_choice:-1}

    if [ "$voice_choice" = "2" ]; then
        TTS_VOICE="pt-BR-FranciscaNeural"
    else
        TTS_VOICE="pt-BR-AntonioNeural"
    fi

    # Gerar config.yaml
    cat > config/config.yaml << YAML
# ============================================
# Alfred — Configuração Pessoal
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
  ollama_host: "http://localhost:11434"

# --- Voz ---
voice:
  stt_model: "base"
  stt_language: "pt"
  tts_engine: "edge-tts"
  tts_voice: "$TTS_VOICE"
  wake_word: "alfred"

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
    - "~/Documents"
    - "~/Downloads"
    - "~/Videos"
    - "~/Music"
    - "~/Desktop"
  allow_browser: true
  allow_system_commands: false
YAML

    ok "Configuração salva em config/config.yaml"
fi

# ═══════════════════════════════════════════════════════════
# PASSO 7: Auto-Start
# ═══════════════════════════════════════════════════════════
step 7 "Configurando auto-start..."

echo ""
echo -e "${BOLD}Iniciar Alfred automaticamente no boot?${NC}"
echo -e "  ${CYAN}[1]${NC} Sim, via autostart do desktop ${GREEN}← Recomendado${NC}"
echo -e "  ${CYAN}[2]${NC} Sim, via systemd (headless/servidor)"
echo -e "  ${CYAN}[3]${NC} Não configurar agora"
echo ""
read -p "Escolha [1/2/3] (padrão: 1): " autostart_choice
autostart_choice=${autostart_choice:-1}

case $autostart_choice in
    1)
        # Auto-start via desktop entry
        AUTOSTART_DIR="$HOME/.config/autostart"
        mkdir -p "$AUTOSTART_DIR"

        cat > "$AUTOSTART_DIR/alfred.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=Alfred - Assistente de IA
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
        info "Alfred vai iniciar automaticamente no próximo login"
        info "Para remover: rm $AUTOSTART_DIR/alfred.desktop"
        ;;
    2)
        # Auto-start via systemd (user service)
        SYSTEMD_DIR="$HOME/.config/systemd/user"
        mkdir -p "$SYSTEMD_DIR"

        cat > "$SYSTEMD_DIR/alfred.service" << SERVICE
[Unit]
Description=Alfred - Assistente Pessoal de IA
After=network.target sound.target
Wants=pulseaudio.service

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStartPre=/bin/bash -c 'pgrep ollama || ollama serve &'
ExecStartPre=/bin/sleep 3
ExecStart=$SCRIPT_DIR/venv/bin/python -m alfred
Restart=on-failure
RestartSec=10
Environment=DISPLAY=:0
Environment=PULSE_SERVER=unix:/run/user/%U/pulse/native

[Install]
WantedBy=default.target
SERVICE

        systemctl --user daemon-reload
        systemctl --user enable alfred.service
        ok "Serviço systemd configurado"
        info "Iniciar agora: systemctl --user start alfred"
        info "Ver logs: journalctl --user -u alfred -f"
        ;;
    3)
        info "Auto-start não configurado. Você pode executar manualmente:"
        info "  cd $SCRIPT_DIR && ./start.sh"
        ;;
esac

# ═══════════════════════════════════════════════════════════
# Finalização
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}✅ Instalação concluída com sucesso!${NC}        ${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Para iniciar agora:"
echo -e "    ${CYAN}cd $SCRIPT_DIR && ./start.sh${NC}"
echo ""
echo -e "  Ou diretamente:"
echo -e "    ${CYAN}cd $SCRIPT_DIR && source venv/bin/activate && python -m alfred${NC}"
echo ""
echo -e "  ${DIM}Diga \"Alfred\" e faça sua primeira pergunta! 🎤${NC}"
echo ""
