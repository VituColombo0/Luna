"""
Orchestrator — O coração do Alfred.

Gerencia o loop principal e a comunicação entre todos os módulos:
Brain (LLM), Voice (STT/TTS), Vision (câmera), Memory (ChromaDB),
Actions (OS), Display (animações visuais).

Modo Alexa:
- Alfred fica ouvindo em background (wake word detection)
- Quando detecta "Alfred", emite um beep e ativa escuta
- Grava o comando, processa, responde e volta pro idle
"""

import logging
import time

from rich.panel import Panel

from alfred.brain.brain import Brain
from alfred.voice.listener import Listener
from alfred.voice.speaker import Speaker
from alfred.voice.wake_word import WakeWordDetector
from alfred.voice.sounds import SoundPlayer
from alfred.memory.memory_manager import MemoryManager
from alfred.actions.action_executor import ActionExecutor
from alfred.ui.display import Display, State
from alfred.utils.logger import console


class Orchestrator:
    """
    Orquestrador principal que roda o loop de vida do Alfred.

    Suporta dois modos de operação:
    - voice (padrão): Wake word detection contínuo estilo Alexa
    - text: Input por terminal (fallback/debug)
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

        self.logger.info("Inicializando [bold]Wake Word Detector[/]...")
        self.wake_word = WakeWordDetector(config, logger)

        self.logger.info("Inicializando [bold]Sound Player[/]...")
        self.sounds = SoundPlayer()

        self.logger.info("Inicializando [bold]Memory[/] (ChromaDB)...")
        self.memory = MemoryManager(config, logger)

        self.logger.info("Inicializando [bold]Actions[/] (OS Control)...")
        self.actions = ActionExecutor(config, logger)

    def run(self):
        """
        Loop principal do Alfred.

        Fluxo (modo Alexa):
        1. Sequência de boot animada
        2. Verificar conexão com Ollama
        3. Iniciar wake word detection em background
        4. Quando detectar "Alfred":
           a. Beep de confirmação
           b. Gravar comando (Listener)
           c. Buscar memórias relevantes
           d. Enviar pro LLM (Brain)
           e. Executar ação se necessário
           f. Falar resposta com TTS
           g. Salvar na memória
           h. Voltar ao idle (ouvir novamente)
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

        # Determinar modo de operação
        voice_available = self.wake_word.is_available and self.listener.is_available

        if voice_available:
            self._run_voice_mode(user_name, wake_word)
        else:
            console.print(
                "[yellow]⚠ Sistema de voz indisponível. "
                "Usando modo texto como fallback.[/]\n"
            )
            self._run_text_mode(user_name, wake_word)

    def _run_voice_mode(self, user_name: str, wake_word: str):
        """
        Modo Alexa — Wake word detection + voz.

        O Alfred fica ouvindo em background e responde quando chamado.
        Mantém também o input por texto ativo para comandos especiais.
        """
        console.print(
            Panel(
                f"[bold green]Todos os sistemas online![/]\n\n"
                f"🎤 Modo: [bold cyan]Voz (estilo Alexa)[/]\n"
                f'   Diga "[bold]{wake_word}[/]" seguido do seu comando\n'
                f"   Exemplo: \"{wake_word}, que horas são?\"\n\n"
                f"⌨️  Comandos de texto (terminal):\n"
                f"  [dim]/sair[/]   — Desligar o Alfred\n"
                f"  [dim]/limpar[/] — Limpar histórico de conversa\n"
                f"  [dim]/texto[/]  — Mudar para modo texto\n"
                f"  [dim]/status[/] — Ver status dos módulos",
                title="✅ Alfred Pronto",
                border_style="green",
            )
        )

        # Saudação com animação
        greeting = self._build_greeting(user_name)
        self._speak_with_display(greeting)

        # Flag para controlar processamento de wake word
        import threading
        self._processing = False
        self._processing_lock = threading.Lock()

        # Iniciar wake word detection em background
        self.wake_word.start(callback=self._on_wake_word_detected)

        # Loop principal — processa comandos de texto enquanto wake word roda em bg
        while self.running:
            try:
                user_input = console.input(
                    f"\n[dim](ouvindo... digite comando ou /sair)[/] "
                )

                if not user_input or not user_input.strip():
                    continue

                user_input = user_input.strip()

                # Comandos especiais
                if user_input.lower() == "/sair":
                    self._speak_with_display(
                        f"Até mais, {user_name}! Desligando sistemas."
                    )
                    break
                elif user_input.lower() == "/limpar":
                    self.brain.clear_history()
                    console.print("[dim]Histórico limpo.[/]")
                    continue
                elif user_input.lower() == "/texto":
                    self.wake_word.stop()
                    console.print("[dim]Wake word desativado. Modo texto.[/]")
                    self._run_text_mode(user_name, self.config.get("voice", {}).get("wake_word", "alfred"))
                    return
                elif user_input.lower() == "/status":
                    self._show_status()
                    continue
                else:
                    # Processar como comando de texto
                    self._process_command(user_input, user_name)

            except KeyboardInterrupt:
                break
            except EOFError:
                # Modo sem terminal interativo (daemon)
                # Apenas espera — wake word cuida de tudo
                try:
                    while self.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    break

        # Cleanup
        self.wake_word.stop()

    def _on_wake_word_detected(self, initial_command: str):
        """
        Callback chamado quando a wake word é detectada.

        Args:
            initial_command: Texto após a wake word (pode estar vazio).
        """
        import threading

        # Evitar processamento duplo
        with self._processing_lock:
            if self._processing:
                return
            self._processing = True

        try:
            user_name = self.config.get("user", {}).get("nickname", "Usuário")

            # Pausar wake word durante processamento
            self.wake_word.pause()

            # 🔔 Beep de confirmação
            self.sounds.play("activation")

            # Se já veio um comando junto com a wake word, usar ele
            if initial_command and len(initial_command) > 3:
                user_input = initial_command
                console.print(f"\n[bold green]{user_name}:[/] {user_input}")
            else:
                # Gravar comando completo
                console.print(
                    "\n[bold bright_green]🎤 Ouvindo comando...[/]"
                )
                self.display.set_state(State.LISTENING)
                self.display.start()

                user_input = self.listener.listen()

                self.display.stop()

                if not user_input or not user_input.strip():
                    # Apenas disse "Alfred" sem comando
                    self.sounds.play("deactivation")
                    console.print("[dim]Nenhum comando detectado.[/]")
                    self.wake_word.resume()
                    return

                console.print(f"\n[bold green]{user_name}:[/] {user_input}")

            # Processar o comando
            self._process_command(user_input, user_name)

            # Som de volta ao idle
            self.sounds.play("deactivation")

        except Exception as e:
            self.logger.error(f"Erro ao processar wake word: {e}")
            self.sounds.play("error")
        finally:
            # Retomar wake word detection
            self.wake_word.resume()
            with self._processing_lock:
                self._processing = False

    def _run_text_mode(self, user_name: str, wake_word: str):
        """
        Modo texto — Input pelo terminal (fallback/debug).
        """
        console.print(
            Panel(
                f"[bold green]Todos os sistemas online![/]\n\n"
                f"⌨️  Modo: [bold cyan]Texto[/]\n"
                f"Comandos especiais:\n"
                f"  [dim]/sair[/]   — Desligar o Alfred\n"
                f"  [dim]/limpar[/] — Limpar histórico de conversa\n"
                f"  [dim]/voz[/]    — Mudar para modo voz\n"
                f"  [dim]/status[/] — Ver status dos módulos",
                title="✅ Alfred Pronto",
                border_style="green",
            )
        )

        # Saudação
        greeting = self._build_greeting(user_name)
        self._speak_with_display(greeting)

        while self.running:
            try:
                user_input = console.input(f"\n[bold green]{user_name}:[/] ")

                if not user_input or not user_input.strip():
                    continue

                user_input = user_input.strip()

                # Comandos especiais
                if user_input.lower() == "/sair":
                    self._speak_with_display(
                        f"Até mais, {user_name}! Desligando sistemas."
                    )
                    break
                elif user_input.lower() == "/limpar":
                    self.brain.clear_history()
                    console.print("[dim]Histórico limpo.[/]")
                    continue
                elif user_input.lower() == "/voz":
                    if self.wake_word.is_available:
                        console.print("[dim]Ativando modo voz...[/]")
                        self._run_voice_mode(user_name, wake_word)
                        return
                    else:
                        console.print(
                            "[yellow]Sistema de voz indisponível.[/]"
                        )
                    continue
                elif user_input.lower() == "/status":
                    self._show_status()
                    continue

                # Processar comando
                self._process_command(user_input, user_name)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Erro no loop principal: {e}")
                self.display.stop()
                time.sleep(0.5)

    def _process_command(self, user_input: str, user_name: str):
        """
        Processa um comando do usuário (vindo de voz ou texto).

        Args:
            user_input: O comando do usuário.
            user_name: Nome do usuário para exibição.
        """
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

    def _speak_with_display(self, text: str):
        """
        Fala um texto enquanto mostra a animação de speaking.

        Args:
            text: Texto para falar e exibir.
        """
        console.print(f"\n[bold blue]Alfred:[/] {text}")

        # Pausar wake word durante fala (evitar auto-ativação)
        if hasattr(self, 'wake_word') and self.wake_word.is_available:
            self.wake_word.pause()

        # Iniciar animação de fala
        self.display.set_state(State.SPEAKING, text=text)
        self.display.start()

        # Falar (bloqueante)
        self.speaker.speak(text)

        # Parar animação
        self.display.stop()

        # Retomar wake word
        if hasattr(self, 'wake_word') and self.wake_word.is_available:
            self.wake_word.resume()

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

        # Wake Word
        table.add_row(
            "👂 Wake Word",
            "[green]Ativo[/]" if self.wake_word.is_available else "[yellow]Indisponível[/]",
            f"Palavra: \"{self.wake_word.wake_word}\"",
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

        # Sounds
        table.add_row(
            "🔔 Sons de Feedback",
            "[green]Ativo[/]" if self.sounds.is_available else "[yellow]Indisponível[/]",
            "Beeps de confirmação",
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
        self.wake_word.stop()
        self.display.stop()
        self.logger.info("Alfred desligado.")
