#!/bin/bash
# ============================================
# Alfred — Script de inicialização (Linux)
# ============================================
# Este script inicia o Alfred automaticamente.
# Usado pelo systemd para auto-start no boot.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOG_FILE="$SCRIPT_DIR/data/alfred.log"

# Criar pasta de logs se não existir
mkdir -p "$(dirname "$LOG_FILE")"

# Ativar virtualenv
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "Erro: virtualenv não encontrado em $VENV_DIR"
    echo "Execute: python3 -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# Verificar se o Ollama está rodando, senão iniciar
if ! pgrep -x "ollama" > /dev/null; then
    echo "Iniciando Ollama em background..."
    ollama serve > /dev/null 2>&1 &
    sleep 3  # Esperar o Ollama iniciar
fi

# Iniciar o Alfred
echo "[$(date)] Iniciando Alfred..." >> "$LOG_FILE"
cd "$SCRIPT_DIR"
python -m alfred 2>&1 | tee -a "$LOG_FILE"
