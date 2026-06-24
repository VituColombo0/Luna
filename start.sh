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

# Criar pasta de logs se não existir
mkdir -p "$LOG_DIR"

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
    sleep 3
fi

# Iniciar o Alfred
echo "[$(date)] Iniciando Alfred..." >> "$LOG_FILE"
cd "$SCRIPT_DIR"
python -m alfred 2>&1 | tee -a "$LOG_FILE"
