#!/bin/bash
# ============================================
# Alfred — Instalador de auto-start (Linux)
# ============================================
# Execute este script para configurar o Alfred
# para iniciar automaticamente quando você logar.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_FILE="$SCRIPT_DIR/alfred-autostart.desktop"
AUTOSTART_DIR="$HOME/.config/autostart"
USER_NAME="$(whoami)"
HOME_DIR="$HOME"

echo "╔══════════════════════════════════════╗"
echo "║  🧠 Alfred — Instalador Auto-Start  ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Atualizar caminhos no .desktop
echo "1. Configurando caminhos..."
sed -i "s|TROCAR_PELO_SEU_USUARIO|$USER_NAME|g" "$DESKTOP_FILE"
sed -i "s|Exec=.*|Exec=$SCRIPT_DIR/start.sh|g" "$DESKTOP_FILE"

# Tornar start.sh executável
chmod +x "$SCRIPT_DIR/start.sh"

# Copiar para autostart
echo "2. Instalando no autostart..."
mkdir -p "$AUTOSTART_DIR"
cp "$DESKTOP_FILE" "$AUTOSTART_DIR/alfred.desktop"

echo "3. Verificando..."
if [ -f "$AUTOSTART_DIR/alfred.desktop" ]; then
    echo ""
    echo "✅ Auto-start configurado com sucesso!"
    echo ""
    echo "O Alfred vai iniciar automaticamente no próximo login."
    echo "Para testar agora, execute: $SCRIPT_DIR/start.sh"
    echo ""
    echo "Para remover o auto-start:"
    echo "  rm $AUTOSTART_DIR/alfred.desktop"
else
    echo "❌ Erro ao configurar auto-start."
    exit 1
fi
