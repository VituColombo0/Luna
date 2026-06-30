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

    # Verificar se o config existe
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "config.yaml"
    )

    if not os.path.exists(config_path):
        console.print(
            "[bold red]Erro:[/] Arquivo de configuração não encontrado.\n"
            "Copie [cyan]config/config.example.yaml[/] para [cyan]config/config.yaml[/] "
            "e edite com suas informações."
        )
        sys.exit(1)

    try:
        config = load_config()
    except FileNotFoundError:
        console.print(
            "[bold red]Erro:[/] Arquivo de configuração não encontrado.\n"
            "Copie [cyan]config/config.example.yaml[/] para [cyan]config/config.yaml[/] "
            "e edite com suas informações."
        )
        sys.exit(1)

    # --- Primeiro uso: configuração interativa ---
    user_name = config.get("user", {}).get("name", "")
    user_nickname = config.get("user", {}).get("nickname", "")

    if not user_name or not user_nickname:
        config = _run_first_use_setup(config, config_path)

    user_display = config.get("user", {}).get("nickname", "Usuário")
    console.print(f"[dim]Olá, [bold]{user_display}[/bold]. Inicializando sistemas...[/]\n")

    orchestrator = Orchestrator(config, logger)

    try:
        orchestrator.run()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Luna desligando... Até mais![/]")
        orchestrator.shutdown()
        sys.exit(0)


def _run_first_use_setup(config: dict, config_path: str) -> dict:
    """
    Fluxo de configuração interativa para o primeiro uso.

    Pede nome, apelido e bio do usuário, e salva no config.yaml.

    Args:
        config: Configuração atual (com campos vazios).
        config_path: Caminho do arquivo config.yaml.

    Returns:
        Configuração atualizada com os dados do usuário.
    """
    import yaml

    console.print("[bold cyan]╔══════════════════════════════════════════════╗[/]")
    console.print("[bold cyan]║[/]  [bold white]🎉 Bem-vindo! Configuração Inicial[/]      [bold cyan]║[/]")
    console.print("[bold cyan]╚══════════════════════════════════════════════╝[/]")
    console.print("")
    console.print("[white]Vamos configurar a Luna para você.[/]")
    console.print("[dim]Responda algumas perguntas rápidas para personalizar sua experiência.[/]")
    console.print("")

    # Perguntar nome
    name = console.input("[bold green]📛 Qual é o seu nome completo?[/] ").strip()
    if not name:
        name = "Usuário"

    # Perguntar apelido
    nickname = console.input(
        f"[bold green]💬 Como quer que eu te chame?[/] [dim](ex: {name.split()[0]})[/] "
    ).strip()
    if not nickname:
        nickname = name.split()[0] if name != "Usuário" else "Usuário"

    # Perguntar bio
    bio = console.input(
        "[bold green]📝 Conte um pouco sobre você[/] [dim](opcional, enter para pular)[/] "
    ).strip()
    if not bio:
        bio = ""

    # Atualizar config
    if "user" not in config:
        config["user"] = {}
    config["user"]["name"] = name
    config["user"]["nickname"] = nickname
    config["user"]["bio"] = bio

    # Salvar config atualizado
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        console.print(f"\n[green]✅ Configuração salva![/]")
    except Exception as e:
        console.print(f"\n[yellow]⚠️ Não foi possível salvar: {e}[/]")

    console.print(f"[dim]Prazer em conhecê-lo, {nickname}![/]\n")

    return config


if __name__ == "__main__":
    main()
