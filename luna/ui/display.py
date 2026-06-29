"""
Display — Interface visual animada da Luna no terminal.

Mostra o estado atual da Luna com animações:
- IDLE: Logo estático com hora e data
- LISTENING: Onda pulsante indicando que está ouvindo
- THINKING: Animação de processamento
- SPEAKING: Visualizador de ondas sonoras animado
- EXECUTING: Indicador de ação sendo executada

Roda em uma thread separada para não bloquear o loop principal.
"""

import math
import os
import random
import shutil
import threading
import time
from enum import Enum, auto

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.table import Table
from datetime import datetime


class State(Enum):
    """Estados visuais da Luna."""
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()
    EXECUTING = auto()
    BOOTING = auto()


# Frames da animação de boot
BOOT_FRAMES = [
    "Inicializando núcleo...",
    "Carregando modelo de linguagem...",
    "Calibrando sistema de voz...",
    "Conectando à memória de longo prazo...",
    "Ativando módulo de visão...",
    "Verificando sistemas de ação...",
    "Todos os sistemas online.",
]

# Caracteres para o visualizador de ondas
WAVE_CHARS = "▁▂▃▄▅▆▇█"
WAVE_CHARS_THIN = "░▒▓█"


class Display:
    """
    Interface visual animada da Luna.
    Roda em uma thread separada e atualiza o terminal em tempo real.
    """

    def __init__(self, user_name: str = "Usuário"):
        self.console = Console()
        self.user_name = user_name
        self.state = State.IDLE
        self.current_text = ""          # Texto sendo exibido (fala da Luna)
        self.subtitle = ""              # Subtexto/status secundário
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._tick = 0                  # Contador de frames de animação

        # Dimensões do terminal
        self.width = min(shutil.get_terminal_size().columns, 80)

    # ─── Controle de Estado ────────────────────────────────────

    def set_state(self, state: State, text: str = "", subtitle: str = ""):
        """Muda o estado visual da Luna."""
        with self._lock:
            self.state = state
            self.current_text = text
            self.subtitle = subtitle
            self._tick = 0

    def set_speaking_text(self, text: str):
        """Atualiza o texto sendo falado (para exibir como legenda)."""
        with self._lock:
            self.current_text = text

    # ─── Renderização ──────────────────────────────────────────

    def _render_frame(self) -> Panel:
        """Renderiza um frame da animação com base no estado atual."""
        with self._lock:
            state = self.state
            text = self.current_text
            subtitle = self.subtitle
            tick = self._tick
            self._tick += 1

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d/%m/%Y")

        if state == State.BOOTING:
            content = self._render_boot(tick)
        elif state == State.IDLE:
            content = self._render_idle(tick, time_str, date_str)
        elif state == State.LISTENING:
            content = self._render_listening(tick)
        elif state == State.THINKING:
            content = self._render_thinking(tick)
        elif state == State.SPEAKING:
            content = self._render_speaking(tick, text)
        elif state == State.EXECUTING:
            content = self._render_executing(tick, text)
        else:
            content = Text("...")

        # Definir cor da borda por estado
        border_colors = {
            State.IDLE: "bright_blue",
            State.LISTENING: "bright_green",
            State.THINKING: "bright_yellow",
            State.SPEAKING: "bright_cyan",
            State.EXECUTING: "bright_magenta",
            State.BOOTING: "bright_blue",
        }

        state_labels = {
            State.IDLE: "⏳ Aguardando",
            State.LISTENING: "🎤 Ouvindo",
            State.THINKING: "🧠 Pensando",
            State.SPEAKING: "🔊 Falando",
            State.EXECUTING: "⚡ Executando",
            State.BOOTING: "🔄 Iniciando",
        }

        return Panel(
            Align.center(content),
            title=f"[bold]Luna[/] — {state_labels.get(state, '')}",
            subtitle=f"[dim]{time_str} • {date_str}[/]",
            border_style=border_colors.get(state, "white"),
            width=self.width,
            padding=(1, 2),
        )

    def _render_boot(self, tick: int) -> Text:
        """Animação de boot sequencial."""
        lines = Text()
        step = min(tick // 8, len(BOOT_FRAMES) - 1)

        for i, frame in enumerate(BOOT_FRAMES):
            if i < step:
                lines.append(f"  ✅ {frame}\n", style="green")
            elif i == step:
                # Animação de loading no passo atual
                spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                char = spinner[tick % len(spinner)]
                lines.append(f"  {char} {frame}\n", style="bold yellow")
            else:
                lines.append(f"  ○ {frame}\n", style="dim")

        return lines

    def _render_idle(self, tick: int, time_str: str, date_str: str) -> Text:
        """Estado ocioso com logo e hora."""
        # Pulso suave no logo
        pulse_chars = ["◉", "◎", "○", "◎"]
        pulse = pulse_chars[tick % len(pulse_chars)]

        content = Text()
        content.append(f"\n  {pulse} ", style="bright_blue")
        content.append("Luna", style="bold bright_white")
        content.append(" está pronto\n\n", style="dim")
        content.append(f'  Diga "Luna" ou digite para começar\n', style="dim italic")

        return content

    def _render_listening(self, tick: int) -> Text:
        """Visualizador de ondas pulsantes ao ouvir."""
        content = Text()
        content.append("\n")

        # Gerar onda pulsante centralizada
        bar_count = 20
        center = bar_count // 2
        wave_line = ""

        for i in range(bar_count):
            dist = abs(i - center)
            # Onda que pulsa do centro para fora
            phase = (tick * 0.3) - dist * 0.4
            amplitude = max(0, math.sin(phase) * 0.8 + 0.2)
            bar_idx = int(amplitude * (len(WAVE_CHARS) - 1))
            wave_line += WAVE_CHARS[bar_idx]

        content.append(f"  {wave_line}\n", style="bold bright_green")
        content.append("\n  Ouvindo...\n", style="green")

        return content

    def _render_thinking(self, tick: int) -> Text:
        """Animação de pensamento com pontos girando."""
        content = Text()
        content.append("\n")

        # Animação de rede neural / sinapses
        brain_frames = [
            "  ○ ─ ○ ─ ● ─ ○ ─ ○",
            "  ○ ─ ● ─ ○ ─ ○ ─ ○",
            "  ● ─ ○ ─ ○ ─ ○ ─ ●",
            "  ○ ─ ○ ─ ○ ─ ● ─ ○",
            "  ○ ─ ○ ─ ● ─ ○ ─ ○",
        ]

        frame = brain_frames[tick % len(brain_frames)]
        content.append(f"{frame}\n", style="bold bright_yellow")

        dots = "." * ((tick % 3) + 1)
        content.append(f"\n  Processando{dots}\n", style="yellow")

        return content

    def _render_speaking(self, tick: int, text: str) -> Text:
        """Visualizador de ondas sonoras + legenda do que está falando."""
        content = Text()
        content.append("\n")

        # Equalizer animado
        bar_count = 30
        eq_line = ""
        for i in range(bar_count):
            # Ondas semi-aleatórias que mudam a cada tick
            val = (
                math.sin(tick * 0.5 + i * 0.7) * 0.3
                + math.sin(tick * 0.3 + i * 1.3) * 0.3
                + random.random() * 0.4
            )
            val = max(0.05, min(1.0, val))
            bar_idx = int(val * (len(WAVE_CHARS) - 1))
            eq_line += WAVE_CHARS[bar_idx]

        content.append(f"  {eq_line}\n", style="bold bright_cyan")

        # Legenda do que está falando (truncada para caber)
        if text:
            max_len = self.width - 10
            display_text = text[:max_len] + "..." if len(text) > max_len else text
            content.append(f"\n  💬 {display_text}\n", style="white")

        return content

    def _render_executing(self, tick: int, text: str) -> Text:
        """Animação de execução de ação."""
        content = Text()
        content.append("\n")

        spinner = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        char = spinner[tick % len(spinner)]

        content.append(f"  {char} ", style="bold bright_magenta")
        content.append("Executando ação...\n", style="bright_magenta")

        if text:
            content.append(f"\n  → {text}\n", style="dim")

        return content

    # ─── Thread de Animação ────────────────────────────────────

    def start(self):
        """Inicia a thread de animação em background."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._animation_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Para a animação."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _animation_loop(self):
        """Loop de animação que roda em background."""
        try:
            with Live(
                self._render_frame(),
                console=self.console,
                refresh_per_second=10,
                transient=True,
            ) as live:
                while self._running:
                    live.update(self._render_frame())
                    time.sleep(0.1)
        except Exception:
            pass  # Terminal pode fechar durante a animação

    # ─── Boot Sequence ─────────────────────────────────────────

    def play_boot_sequence(self):
        """
        Reproduz a sequência de boot com animação.
        Bloqueia até terminar.
        """
        self.set_state(State.BOOTING)

        total_frames = len(BOOT_FRAMES) * 8 + 16  # ~frames para completar

        try:
            with Live(
                self._render_frame(),
                console=self.console,
                refresh_per_second=10,
            ) as live:
                for _ in range(total_frames):
                    live.update(self._render_frame())
                    time.sleep(0.1)
        except Exception:
            pass

        self.set_state(State.IDLE)
