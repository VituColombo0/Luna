"""
Orchestrator — O coração do Alfred.

Gerencia o loop principal e a comunicação entre todos os módulos:
Brain (LLM), Voice (STT/TTS), Vision (câmera), Memory (ChromaDB),
Actions (OS), Display (animações visuais).
"""

import logging
import time

from rich.panel import Panel

from alfred.brain.brain import Brain
from alfred.voice.listener import Listener
from alfred.voice.speaker import Speaker
from alfred.memory.memory_manager import MemoryManager
from alfred.actions.action_executor import ActionExecutor
from alfred.ui.display import Display, State
from alfred.utils.logger import console


class Orchestrator:
    """
    Orquestrador principal que roda o loop de vida do Alfred.
    """

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.running = False

        user_name = config.get("user", {}).get("nickname", "Usuário")

        # --- Inicializar display visual primeiro ---
        self.display = Display(user_name=user_name)

        # --- Inicializar módulos ---
        self.logger.info("Inicializando [bold]Brain[/] (LLM)...")
        self.brain = Brain(config, logger)

        self.logger.info("Inicializando [bold]Listener[/] (STT)...")
        self.listener = Listener(config, logger)

        self.logger.info("Inicializando [bold]Speaker[/] (TTS)...")
        self.speaker = Speaker(config, logger)

        self.logger.info("Inicializando [bold]Memory[/] (ChromaDB)...")
        self.memory = MemoryManager(config, logger)

        self.logger.info("Inicializando [bold]Actions[/] (OS Control)...")
        self.actions = ActionExecutor(config, logger)

    def run(self):
        """
        Loop principal do Alfred.

        Fluxo:
        1. Sequência de boot animada
        2. Verificar conexão com Ollama
        3. Esperar input do usuário (voz ou texto)
        4. Buscar memórias relevantes
        5. Enviar pro LLM (Brain)
        6. Executar ação se necessário
        7. Falar a resposta com visualização
        8. Salvar na memória
        """
        # Sequência de boot cinematográfica
        self.display.play_boot_sequence()

        # Verificar conexão com o Ollama
        if not self.brain.check_connection():
            console.print(
                Panel(
                    "[bold red]Não foi possível conectar ao Ollama.[/]\n\n"
                    "Certifique-se de que:\n"
                    "1. O Ollama está instalado: [cyan]https://ollama.ai[/]\n"
                    "2. O serviço está rodando: [cyan]ollama serve[/]\n"
                    "3. O modelo está baixado: [cyan]ollama pull phi3[/]",
                    title="⚠️  Erro de Conexão",
                    border_style="red",
                )
            )
            return

        self.running = True
        user_name = self.config.get("user", {}).get("nickname", "Usuário")
        wake_word = self.config.get("voice", {}).get("wake_word", "alfred")

        console.print(
            Panel(
                f"[bold green]Todos os sistemas online![/]\n\n"
                f"Modo de entrada: [cyan]texto[/] (digite) ou [cyan]voz[/] (fale '{wake_word}')\n"
                f"Comandos especiais:\n"
                f"  [dim]/sair[/]   — Desligar o Alfred\n"
                f"  [dim]/limpar[/] — Limpar histórico de conversa\n"
                f"  [dim]/voz[/]    — Alternar modo de entrada para voz\n"
                f"  [dim]/texto[/]  — Alternar modo de entrada para texto\n"
                f"  [dim]/status[/] — Ver status dos módulos",
                title="✅ Alfred Pronto",
                border_style="green",
            )
        )

        # Saudação com animação
        greeting = self._build_greeting(user_name)
        self._speak_with_display(greeting)

        input_mode = "text"  # Começa em modo texto para facilitar testes

        while self.running:
            try:
                # --- Capturar input ---
                if input_mode == "text":
                    user_input = console.input(f"\n[bold green]{user_name}:[/] ")
                else:
                    # Mostrar animação de escuta
                    self.display.set_state(State.LISTENING)
                    self.display.start()

                    user_input = self.listener.listen()

                    self.display.stop()

                    if user_input:
                        console.print(
                            f"[bold green]{user_name}:[/] {user_input}"
                        )

                if not user_input or not user_input.strip():
                    continue

                user_input = user_input.strip()

                # --- Comandos especiais ---
                if user_input.lower() == "/sair":
                    self._speak_with_display(f"Até mais, {user_name}! Desligando sistemas.")
                    break
                elif user_input.lower() == "/limpar":
                    self.brain.clear_history()
                    console.print("[dim]Histórico limpo.[/]")
                    continue
                elif user_input.lower() == "/voz":
                    input_mode = "voice"
                    console.print("[dim]Modo de entrada: 🎤 voz[/]")
                    continue
                elif user_input.lower() == "/texto":
                    input_mode = "text"
                    console.print("[dim]Modo de entrada: ⌨️  texto[/]")
                    continue
                elif user_input.lower() == "/status":
                    self._show_status()
                    continue

                # --- Mostrar animação de pensamento ---
                self.display.set_state(State.THINKING)
                self.display.start()

                # --- Buscar memórias relevantes ---
                memory_context = self.memory.recall(user_input)

                # --- Pensar (LLM) ---
                result = self.brain.think(
                    user_message=user_input,
                    memory_context=memory_context,
                )

                self.display.stop()

                response_text = result["text"]
                action = result["action"]

                # --- Executar ação se houver ---
                if action:
                    self.display.set_state(
                        State.EXECUTING,
                        text=f"{action.get('action', '?')}",
                    )
                    self.display.start()

                    action_result = self.actions.execute(action)

                    self.display.stop()

                    if action_result:
                        console.print(f"[dim]⚡ {action_result}[/]")

                # --- Falar a resposta com animação ---
                self._speak_with_display(response_text)

                # --- Salvar na memória ---
                self.memory.remember(
                    user_message=user_input,
                    assistant_response=response_text,
                )

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Erro no loop principal: {e}")
                self.display.stop()
                time.sleep(0.5)

    def _speak_with_display(self, text: str):
        """
        Fala um texto enquanto mostra a animação de speaking.

        Args:
            text: Texto para falar e exibir.
        """
        console.print(f"\n[bold blue]Alfred:[/] {text}")

        # Iniciar animação de fala
        self.display.set_state(State.SPEAKING, text=text)
        self.display.start()

        # Falar (bloqueante)
        self.speaker.speak(text)

        # Parar animação
        self.display.stop()

    def _build_greeting(self, user_name: str) -> str:
        """
        Constrói a saudação baseada no horário do dia.

        Args:
            user_name: Nome do usuário.

        Returns:
            Saudação personalizada.
        """
        from datetime import datetime

        hour = datetime.now().hour

        if 5 <= hour < 12:
            period = "Bom dia"
        elif 12 <= hour < 18:
            period = "Boa tarde"
        elif 18 <= hour < 23:
            period = "Boa noite"
        else:
            period = "Ainda acordado"

        return f"{period}, {user_name}! Todos os sistemas estão online. Como posso ajudar?"

    def _show_status(self):
        """Exibe o status de todos os módulos."""
        from rich.table import Table

        table = Table(title="Status dos Módulos", border_style="bright_blue")
        table.add_column("Módulo", style="bold")
        table.add_column("Status")
        table.add_column("Detalhe", style="dim")

        # Brain
        brain_ok = self.brain.check_connection()
        table.add_row(
            "🧠 Brain (LLM)",
            "[green]Online[/]" if brain_ok else "[red]Offline[/]",
            f"Modelo: {self.brain.model}",
        )

        # Listener
        table.add_row(
            "🎤 Listener (STT)",
            "[green]Pronto[/]" if self.listener.is_available else "[yellow]Indisponível[/]",
            f"Modelo: {self.listener.model_size}",
        )

        # Speaker
        table.add_row(
            "🔊 Speaker (TTS)",
            "[green]Pronto[/]" if self.speaker.is_available else "[yellow]Indisponível[/]",
            f"Engine: {self.speaker.engine}",
        )

        # Memory
        mem_stats = self.memory.get_stats()
        table.add_row(
            "📚 Memory",
            "[green]Ativo[/]" if mem_stats["enabled"] else "[yellow]Desativado[/]",
            f"{mem_stats['count']} memórias",
        )

        # Actions
        table.add_row(
            "⚡ Actions",
            "[green]Ativo[/]" if self.actions.enabled else "[yellow]Desativado[/]",
            f"{len(self.actions.allowed_paths)} pastas permitidas",
        )

        console.print(table)

    def shutdown(self):
        """Desliga o Alfred de forma limpa."""
        self.running = False
        self.display.stop()
        self.logger.info("Alfred desligado.")
