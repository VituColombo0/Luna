#!/bin/bash
# ============================================
# Luna — Script de Inicialização (Linux)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "🌙 Luna — Assistente Pessoal de IA"
echo "===================================="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Execute install.sh primeiro."
    exit 1
fi

# Verificar ambiente virtual
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Ambiente virtual ativado"
else
    echo "⚠️  Ambiente virtual não encontrado. Usando Python global."
fi

# Verificar se Ollama está rodando
if command -v ollama &> /dev/null; then
    if ! pgrep -x "ollama" > /dev/null 2>&1; then
        echo "🔄 Iniciando Ollama em background..."
        nohup ollama serve > /dev/null 2>&1 &
        sleep 2
    fi
    echo "✅ Ollama está rodando"
else
    echo "⚠️  Ollama não encontrado. Instale em: https://ollama.com"
fi

# Modo headless (sem terminal visível)
if [ "$1" = "--headless" ] || [ "$1" = "--no-console" ]; then
    echo "🔇 Iniciando em modo headless (background)..."
    nohup python3 -m luna --headless > /tmp/luna.log 2>&1 &
    LUNA_PID=$!
    echo "   PID: $LUNA_PID"
    echo "   Log: /tmp/luna.log"
    echo "   Para parar: kill $LUNA_PID"
    exit 0
fi

echo ""
echo "🚀 Iniciando Luna..."
echo ""
python3 -m luna "$@"
