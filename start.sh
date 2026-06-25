#!/bin/bash
# ============================================
# Alfred — Script de inicialização (Linux)
# ============================================
# Este script inicia o Alfred automaticamente.
# Usado pelo autostart e systemd para rodar no boot.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOG_DIR="$SCRIPT_DIR/data"
LOG_FILE="$LOG_DIR/alfred.log"

# Criar pasta de logs e dados se não existirem
mkdir -p "$LOG_DIR"
mkdir -p "$SCRIPT_DIR/data/faces"
mkdir -p "$SCRIPT_DIR/data/memory"

# Ativar virtualenv
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "Erro: virtualenv não encontrado em $VENV_DIR"
    echo "Execute o instalador primeiro: bash install.sh"
    exit 1
fi

# Garantir que PulseAudio está disponível (para áudio no autostart)
if [ -z "$PULSE_SERVER" ]; then
    export PULSE_SERVER="unix:/run/user/$(id -u)/pulse/native"
fi

# Verificar se o Ollama está rodando, senão iniciar
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "[$(date)] Iniciando Ollama em background..." >> "$LOG_FILE"
    ollama serve > /dev/null 2>&1 &
    sleep 5  # Dar mais tempo para o Ollama iniciar completamente
fi

# Aguardar Ollama ficar disponível
for i in 1 2 3 4 5; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        break
    fi
    echo "[$(date)] Aguardando Ollama iniciar... (tentativa $i/5)" >> "$LOG_FILE"
    sleep 3
done

# Iniciar o Alfred
echo "[$(date)] Iniciando Alfred..." >> "$LOG_FILE"
cd "$SCRIPT_DIR"
python -m alfred 2>&1 | tee -a "$LOG_FILE"
