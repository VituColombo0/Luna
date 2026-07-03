"""
Orchestrator — O coração da Luna.

Gerencia o loop principal e a comunicação entre todos os módulos:
Brain (LLM), Voice (STT/TTS), Vision (câmera), Memory (ChromaDB),
Actions (OS), Display (animações visuais), Hotkeys (atalhos globais).

Modo Alexa:
- Luna fica ouvindo em background (wake word detection)
- Quando detecta "Luna", emite um beep e ativa escuta
- Grava o comando, processa, responde e volta pro idle

Atalhos Globais:
- Ctrl+Shift+L — Abrir/fechar terminal da Luna
- Ctrl+Shift+Q — Encerrar a Luna
"""

import logging
import threading
import time

from rich.panel import Panel

from luna.brain.brain import Brain
from luna.voice.listener import Listener
from luna.voice.speaker import Speaker
from luna.voice.wake_word import WakeWordDetector
from luna.voice.sounds import SoundPlayer
from luna.voice.calibration import VoiceCalibrator
from luna.memory.memory_manager import MemoryManager
from luna.actions.action_executor import ActionExecutor
from luna.vision.vision_module import VisionModule
from luna.ui.display import Display, State
from luna.core.hotkeys import HotkeyManager
from luna.utils.logger import console


class Orchestrator:
    """
    Orquestrador principal que roda o loop de vida da Luna.

    Suporta dois modos de operação:
    - voice (padrão): Wake word detection contínuo estilo Alexa
    - text: Input por terminal (fallback/debug)
    """

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.running = False
        self._processing = False
        self._processing_lock = threading.Lock()

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
        # Carregar perfil de voz se existir
        self.calibrator = VoiceCalibrator(logger)
        self._voice_profile = self.calibrator.load_profile()
        self.wake_word = WakeWordDetector(config, logger, voice_profile=self._voice_profile)

        self.logger.info("Inicializando [bold]Sound Player[/]...")
        self.sounds = SoundPlayer()

        self.logger.info("Inicializando [bold]Memory[/] (ChromaDB)...")
        self.memory = MemoryManager(config, logger)

        self.logger.info("Inicializando [bold]Actions[/] (OS Control)...")
        self.actions = ActionExecutor(config, logger)

        self.logger.info("Inicializando [bold]Vision[/] (Câmera/Face)...")
        self.vision = VisionModule(config, logger)

        # --- Inicializar atalhos globais ---
        self.logger.info("Inicializando [bold]Hotkeys[/] (Atalhos Globais)...")
        self.hotkeys = HotkeyManager(logger, on_quit=self._quit_signal)

    def _quit_signal(self):
        """Callback chamado pelo atalho Ctrl+Shift+Q."""
        self.running = False
        console.print("\n[bold yellow]🔑 Atalho de encerramento detectado. Luna desligando...[/]")

    def run(self):
        """
        Loop principal da Luna.

        Fluxo (modo Alexa):
        1. Sequência de boot animada
        2. Verificar conexão com Ollama
        3. Iniciar wake word detection em background
        4. Quando detectar "Luna":
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
                    f"3. O modelo está baixado: [cyan]ollama pull {self.brain.model}[/]",
                    title="⚠️  Erro de Conexão",
                    border_style="red",
                )
            )
            return

        self.running = True
        user_name = self.config.get("user", {}).get("nickname", "Usuário")
        wake_word = self.config.get("voice", {}).get("wake_word", "luna")

        # --- Iniciar atalhos globais ---
        self.hotkeys.start()

        # --- Calibração de voz no primeiro uso ---
        if self.calibrator.needs_calibration():
            voice_available_for_cal = (
                self.wake_word.is_available or self.listener.is_available
            )
            if voice_available_for_cal:
                self._run_calibration(wake_word)

        # Determinar modo de operação
        voice_available = self.wake_word.is_available and self.listener.is_available

        self.mode = "voice" if voice_available else "text"

        if self.mode == "text":
            console.print(
                "[yellow]⚠ Sistema de voz indisponível. "
                "Usando modo texto como fallback.[/]\n"
            )

        while self.running:
            if self.mode == "voice":
                self._run_voice_mode(user_name, wake_word)
            else:
                self._run_text_mode(user_name, wake_word)

    def _run_voice_mode(self, user_name: str, wake_word: str):
        """
        Modo Alexa — Wake word detection + voz.

        A Luna fica ouvindo em background e responde quando chamado.
        Mantém também o input por texto ativo para comandos especiais.
        """
        console.print(
            Panel(
                f"[bold bright_green]✨ Todos os sistemas online![/]\n\n"
                f"  🎙️  Modo: [bold bright_cyan]Voz (estilo Alexa)[/]\n"
                f'     Diga "[bold bright_magenta]{wake_word}[/]" seguido do seu comando\n\n'
                f"  ⌨️  Comandos:\n"
                f"     [dim]/sair[/]   — Desligar   [dim]/limpar[/] — Resetar\n"
                f"     [dim]/texto[/]  — Modo texto  [dim]/status[/] — Módulos\n\n"
                f"  🔑 [dim]Ctrl+Shift+L[/] Mostrar  •  [dim]Ctrl+Shift+Q[/] Encerrar",
                title="[bold bright_white]🌙 Luna[/]",
                border_style="bright_magenta",
                padding=(1, 2),
            )
        )

        # Saudação com animação
        greeting = self._build_greeting(user_name)
        self._speak_with_display(greeting)


        # Iniciar wake word detection em background
        self.wake_word.start(callback=self._on_wake_word_detected)

        # Loop principal — processa comandos de texto enquanto wake word roda em bg
        while self.running:
            try:
                user_input = console.input(
                    f"\n[bold bright_magenta]❯[/] "
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
                    self.mode = "text"
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
                    # Apenas disse "Luna" sem comando
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
                f"[bold bright_green]✨ Todos os sistemas online![/]\n\n"
                f"  ⌨️  Modo: [bold bright_cyan]Texto[/]\n\n"
                f"  Comandos:\n"
                f"     [dim]/sair[/]   — Desligar   [dim]/limpar[/] — Resetar\n"
                f"     [dim]/voz[/]    — Modo voz   [dim]/status[/] — Módulos\n\n"
                f"  🔑 [dim]Ctrl+Shift+L[/] Mostrar  •  [dim]Ctrl+Shift+Q[/] Encerrar",
                title="[bold bright_white]🌙 Luna[/]",
                border_style="bright_magenta",
                padding=(1, 2),
            )
        )

        # Saudação
        greeting = self._build_greeting(user_name)
        self._speak_with_display(greeting)

        while self.running:
            try:
                user_input = console.input(f"\n[bold bright_magenta]❯[/] ")

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
                        self.mode = "voice"
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

        Integra visão (câmera + reconhecimento facial), memória de longo prazo
        e execução de ações no PC.

        Args:
            user_input: O comando do usuário.
            user_name: Nome do usuário para exibição.
        """
        # --- Mostrar animação de pensamento ---
        self.display.set_state(State.THINKING)
        self.display.start()

        # --- Identificação Visual ---
        image_path = None
        vision_context = ""
        identified_person = user_name

        if self.vision.is_available:
            # Sempre tentar identificar quem está falando
            if self.vision.face_rec_enabled:
                identified_name = self.vision.identify_face()
                if identified_name:
                    identified_person = identified_name
                    self.logger.info(
                        f"Usuário identificado pela câmera: [cyan]{identified_name}[/]"
                    )

                    # Buscar info do membro no Membros.txt
                    member_info = self.vision.get_member_info(identified_name)
                    if member_info:
                        vision_context = (
                            f"PESSOA IDENTIFICADA PELA CÂMERA: {identified_name}\n"
                            f"INFO: {member_info[:300]}"
                        )

            # Checar se o usuário pediu para olhar/ver/analisar algo
            vision_triggers = [
                "veja", "olha", "olhe", "vendo", "visão", "câmera", "camera",
                "imagem", "rosto", "enxerga", "enxergando", "vê", "observa",
                "identifica", "quem sou", "quem eu sou", "quem está",
                "o que você vê", "o que vê", "me vendo", "quem é", "reconhece",
                "olhando", "foto", "visual", "mostre", "analise"
            ]
            if any(trigger in user_input.lower() for trigger in vision_triggers):
                self.logger.info("Intenção de visão detectada. Capturando imagem...")
                image_path = self.vision.capture_for_analysis()

                # Adicionar descrição da cena ao contexto
                if image_path:
                    scene_desc = self.vision.describe_scene(
                        image_path=image_path,
                        question=user_input,
                    )
                    if scene_desc:
                        vision_context += f"\nDESCRIÇÃO DA CÂMERA: {scene_desc}"

        # Adicionar contexto dos membros (se disponível)
        members_context = ""
        if self.vision.is_available:
            members_context = self.vision.get_all_members_context()

        # --- Buscar memórias relevantes ---
        memory_context = self.memory.recall(user_input)

        # Combinar contextos
        full_context = ""
        if memory_context:
            full_context += f"MEMÓRIAS RELEVANTES:\n{memory_context}\n\n"
        if vision_context:
            full_context += f"{vision_context}\n\n"
        if members_context:
            full_context += f"{members_context}\n"

        # --- Pensar (LLM) ---
        result = self.brain.think(
            user_message=f"[{identified_person} falando]: {user_input}",
            memory_context=full_context,
            image_path=image_path,
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

        # --- Salvar na memória com o nome correto ---
        self.memory.remember(
            user_message=user_input,
            assistant_response=response_text,
            user_name=identified_person,
        )

    def _speak_with_display(self, text: str):
        """
        Fala um texto enquanto mostra a animação de speaking.

        Args:
            text: Texto para falar e exibir.
        """
        console.print(f"\n  [bold bright_magenta]🌙 Luna:[/] {text}")

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

        table = Table(
            title="[bold bright_white]🌙 Status dos Módulos[/]",
            border_style="bright_magenta",
            title_style="bold",
        )
        table.add_column("Módulo", style="bold bright_white")
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
            f'Palavra: "{self.wake_word.wake_word}"',
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

        # Hotkeys
        table.add_row(
            "🔑 Hotkeys",
            "[green]Ativo[/]" if self.hotkeys.is_available else "[yellow]Indisponível[/]",
            "Ctrl+Shift+L/Q",
        )

        console.print(table)

        # Vision
        vision_status = "[green]Ativo[/]" if self.vision.is_available else "[yellow]Desativado[/]"
        vision_detail = ""
        if self.vision.is_available:
            faces_count = len(set(self.vision.known_names)) if self.vision.known_names else 0
            members_count = len(self.vision.members_info)
            vision_detail = f"{faces_count} rostos, {members_count} membros"
        else:
            vision_detail = "opencv/face_recognition não instalado"

        table2 = Table(
            title="[bold bright_white]👁️  Visão & Memória[/]",
            border_style="bright_magenta",
            title_style="bold",
        )
        table2.add_column("Módulo", style="bold bright_white")
        table2.add_column("Status")
        table2.add_column("Detalhe", style="dim")

        table2.add_row("👁️  Vision", vision_status, vision_detail)

        mem_stats = self.memory.get_stats()
        table2.add_row(
            "📚 Memory",
            "[green]Ativo[/]" if mem_stats["enabled"] else "[yellow]Desativado[/]",
            f"{mem_stats['count']} memórias salvas",
        )

        # Listar membros conhecidos
        if self.vision.is_available and self.vision.members_info:
            for name in self.vision.members_info:
                has_face = name in self.vision.known_names or any(
                    n.lower() in name.lower() or name.lower() in n.lower()
                    for n in self.vision.known_names
                )
                face_icon = "🟢" if has_face else "🟡"
                table2.add_row(
                    f"   {face_icon} {name}",
                    "[green]Reconhecível[/]" if has_face else "[yellow]Sem foto[/]",
                    "Face + info carregados" if has_face else "Adicione fotos em data/faces/",
                )

        console.print(table2)

    def _run_calibration(self, wake_word: str):
        """
        Executa a calibração de voz interativa.

        Pausa o wake word detector se estiver rodando,
        roda a calibração, e reinicializa o detector com
        o novo perfil.
        """
        # Pausar wake word durante calibração
        was_running = self.wake_word._running
        if was_running:
            self.wake_word.stop()

        # Deletar perfil antigo se existir (para recalibração)
        self.calibrator.delete_profile()

        # Rodar calibração interativa
        profile = self.calibrator.run_calibration(wake_word, console=console)

        if profile:
            # Reinicializar o WakeWordDetector com o novo perfil
            self._voice_profile = profile
            self.wake_word = WakeWordDetector(
                self.config, self.logger, voice_profile=profile
            )
            self.logger.info(
                f"Wake word recalibrado — threshold: [cyan]{profile.get('optimal_threshold')}[/]"
            )

    def shutdown(self):
        """Desliga a Luna de forma limpa."""
        self.running = False
        self.hotkeys.stop()
        self.wake_word.stop()
        self.display.stop()
        self.logger.info("Luna desligada.")
