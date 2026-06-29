"""
Luna — Ponto de entrada principal.
Uso: python -m luna

Suporta execução sem terminal visível (modo daemon).
"""

import sys
import os
import platform

from luna.core.orchestrator import Orchestrator
from luna.utils.config import load_config
from luna.utils.logger import setup_logger, console


def hide_console_window():
    """
    Esconde a janela do console/terminal no Windows.
    No Linux, o processo pode ser iniciado sem terminal via .desktop ou systemd.
    """
    if platform.system() == "Windows":
        try:
            import ctypes
            # Obtém o handle da janela do console
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                # SW_HIDE = 0
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass  # Se falhar, continua com terminal visível


def main():
    """Inicializa e executa a Luna."""
    # Verificar flag --no-console para esconder terminal
    headless = "--no-console" in sys.argv or "--headless" in sys.argv
    if headless:
        hide_console_window()

    console.print("\n[bold magenta]╔══════════════════════════════════════╗[/]")
    console.print("[bold magenta]║[/]   [bold white]🌙 Luna — Assistente Pessoal[/]       [bold magenta]║[/]")
    console.print("[bold magenta]╚══════════════════════════════════════╝[/]\n")

    logger = setup_logger()

    try:
        config = load_config()
    except FileNotFoundError:
        console.print(
            "[bold red]Erro:[/] Arquivo de configuração não encontrado.\n"
            "Copie [cyan]config/config.example.yaml[/] para [cyan]config/config.yaml[/] "
            "e edite com suas informações."
        )
        sys.exit(1)

    user_name = config.get("user", {}).get("nickname", "Usuário")
    console.print(f"[dim]Olá, [bold]{user_name}[/bold]. Inicializando sistemas...[/]\n")

    orchestrator = Orchestrator(config, logger)

    try:
        orchestrator.run()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Luna desligando... Até mais![/]")
        orchestrator.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
