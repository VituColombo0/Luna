"""
Alfred — Ponto de entrada principal.
Uso: python -m alfred
"""

import sys
from alfred.core.orchestrator import Orchestrator
from alfred.utils.config import load_config
from alfred.utils.logger import setup_logger, console


def main():
    """Inicializa e executa o Alfred."""
    console.print("\n[bold cyan]╔══════════════════════════════════════╗[/]")
    console.print("[bold cyan]║[/]   [bold white]🧠 Alfred — Assistente Pessoal[/]     [bold cyan]║[/]")
    console.print("[bold cyan]╚══════════════════════════════════════╝[/]\n")

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
        console.print("\n[bold yellow]Alfred desligando... Até mais![/]")
        orchestrator.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
