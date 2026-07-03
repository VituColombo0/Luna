"""
Display — Interface visual premium da Luna no terminal.

Mostra o estado atual da Luna com animações ricas:
- IDLE: Logo estilizado com pulso neon e relógio
- LISTENING: Onda sonora pulsante com gradiente
- THINKING: Constelação neural animada
- SPEAKING: Equalizer com visualização de ondas
- EXECUTING: Barra de progresso com spinner premium
- BOOTING: Sequência cinematográfica com barra de progresso

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
from rich.layout import Layout
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
    ("Inicializando núcleo quântico", "core"),
    ("Carregando modelo de linguagem", "brain"),
    ("Calibrando sistema de voz", "voice"),
    ("Sincronizando memória de longo prazo", "memory"),
    ("Ativando módulo de visão", "vision"),
    ("Conectando módulos de ação", "actions"),
    ("Estabelecendo atalhos globais", "hotkeys"),
    ("Todos os sistemas operacionais", "done"),
]

# Logo da Luna em ASCII art
LUNA_LOGO = [
    "  ██╗     ██╗   ██╗███╗   ██╗ █████╗ ",
    "  ██║     ██║   ██║████╗  ██║██╔══██╗",
    "  ██║     ██║   ██║██╔██╗ ██║███████║",
    "  ██║     ██║   ██║██║╚██╗██║██╔══██║",
    "  ███████╗╚██████╔╝██║ ╚████║██║  ██║",
    "  ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝",
]

LUNA_LOGO_MINI = "🌙 L U N A"

# Caracteres para visualizações
WAVE_CHARS = "▁▂▃▄▅▆▇█"
BLOCK_CHARS = "░▒▓█"
BRAILLE_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
ORBIT_CHARS = ["◐", "◓", "◑", "◒"]
DOT_PULSE = ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"]

# Paleta de cores gradientes (escuro -> claro)
GRADIENT_PURPLE = ["#3d0066", "#6600aa", "#8800cc", "#aa33ff", "#cc66ff", "#dd99ff"]
GRADIENT_CYAN = ["#003344", "#006688", "#0099cc", "#33bbee", "#66ddff", "#99eeff"]
GRADIENT_PINK = ["#660033", "#990066", "#cc0088", "#ff33aa", "#ff66cc", "#ff99dd"]


class Display:
    """
    Interface visual premium da Luna.
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
        day_name = now.strftime("%A")

        # Traduzir dia da semana
        day_translate = {
            "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
            "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        day_pt = day_translate.get(day_name, day_name)

        if state == State.BOOTING:
            content = self._render_boot(tick)
        elif state == State.IDLE:
            content = self._render_idle(tick, time_str, date_str, day_pt)
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

        # Definir cor da borda por estado (cores premium)
        border_colors = {
            State.IDLE: "bright_magenta",
            State.LISTENING: "#33ff99",
            State.THINKING: "#ffaa33",
            State.SPEAKING: "#33ccff",
            State.EXECUTING: "#ff33aa",
            State.BOOTING: "#aa33ff",
        }

        state_icons = {
            State.IDLE: "🌙",
            State.LISTENING: "🎙️",
            State.THINKING: "🧠",
            State.SPEAKING: "🔊",
            State.EXECUTING: "⚡",
            State.BOOTING: "🚀",
        }

        state_labels = {
            State.IDLE: "Aguardando",
            State.LISTENING: "Ouvindo",
            State.THINKING: "Processando",
            State.SPEAKING: "Falando",
            State.EXECUTING: "Executando",
            State.BOOTING: "Iniciando",
        }

        icon = state_icons.get(state, "")
        label = state_labels.get(state, "")

        return Panel(
            Align.center(content),
            title=f"[bold bright_white]{icon} Luna[/] [dim]—[/] [italic]{label}[/]",
            subtitle=f"[dim]{day_pt} • {time_str} • {date_str}[/]",
            border_style=border_colors.get(state, "white"),
            width=self.width,
            padding=(1, 2),
        )

    def _render_boot(self, tick: int) -> Text:
        """Animação de boot cinematográfica com barra de progresso."""
        lines = Text()
        step = min(tick // 6, len(BOOT_FRAMES) - 1)
        progress = min(tick / (len(BOOT_FRAMES) * 6 + 10), 1.0)

        # Logo compacto
        lines.append("\n")
        lines.append("        🌙 L U N A  —  Boot Sequence\n", style="bold bright_magenta")
        lines.append("        ─────────────────────────────\n\n", style="dim magenta")

        for i, (frame_text, module) in enumerate(BOOT_FRAMES):
            if i < step:
                lines.append(f"    ● {frame_text}\n", style="green")
            elif i == step:
                char = BRAILLE_SPINNER[tick % len(BRAILLE_SPINNER)]
                lines.append(f"    {char} ", style="bold bright_yellow")
                lines.append(f"{frame_text}\n", style="bold yellow")
            else:
                lines.append(f"    ○ {frame_text}\n", style="dim")

        # Barra de progresso
        lines.append("\n")
        bar_width = self.width - 16
        filled = int(progress * bar_width)
        bar = "━" * filled + "╸" + "─" * max(0, bar_width - filled - 1)
        pct = int(progress * 100)
        lines.append(f"    ", style="")
        lines.append(bar[:filled], style="bold bright_magenta")
        if filled < bar_width:
            lines.append("╸", style="bold bright_white")
            lines.append(bar[filled + 1:], style="dim")
        lines.append(f" {pct}%\n", style="bold bright_white")

        return lines

    def _render_idle(self, tick: int, time_str: str, date_str: str, day_pt: str) -> Text:
        """Estado ocioso premium com logo e indicador de pulso."""
        content = Text()

        # Pulso animado do logo
        pulse_styles = [
            "bold bright_magenta", "bold magenta",
            "bold bright_blue", "bold magenta",
        ]
        style = pulse_styles[tick % len(pulse_styles)]

        content.append("\n")

        # Logo minimalista com pulso
        orbit = ORBIT_CHARS[tick % len(ORBIT_CHARS)]
        content.append(f"           {orbit} ", style=style)
        content.append("L U N A", style="bold bright_white")
        content.append(f" {orbit}\n\n", style=style)

        # Linha decorativa
        line_chars = "═" * 32
        content.append(f"      {line_chars}\n", style="dim magenta")

        # Status
        content.append("\n")
        content.append("       Pronta para ajudar, ", style="dim")
        content.append(f"{self.user_name}", style="bold bright_cyan")
        content.append(".\n", style="dim")

        # Dica
        content.append('       Diga "', style="dim italic")
        content.append("Luna", style="bold bright_magenta italic")
        content.append('" ou digite um comando\n\n', style="dim italic")

        # Wave decorativa idle (sutil)
        wave_width = 32
        wave_line = ""
        for i in range(wave_width):
            val = math.sin(tick * 0.15 + i * 0.3) * 0.3 + 0.35
            val = max(0.0, min(1.0, val))
            idx = int(val * (len(WAVE_CHARS) - 1))
            wave_line += WAVE_CHARS[idx]
        content.append(f"      {wave_line}\n", style="dim magenta")

        return content

    def _render_listening(self, tick: int) -> Text:
        """Visualizador de ondas pulsantes neon ao ouvir."""
        content = Text()
        content.append("\n")

        # Ícone pulsante
        pulse_icons = ["◉", "◎", "●", "◎"]
        icon = pulse_icons[tick % len(pulse_icons)]
        content.append(f"           {icon} ", style="bold #33ff99")
        content.append("Escutando", style="bold bright_green")
        content.append(f" {icon}\n\n", style="bold #33ff99")

        # Onda principal — 3 linhas para efeito 3D
        bar_count = 36
        center = bar_count // 2

        for row in range(3):
            wave_line = "    "
            for i in range(bar_count):
                dist = abs(i - center)
                phase = (tick * 0.4) - dist * 0.35 + row * 0.5
                amplitude = max(0, math.sin(phase) * 0.7 + 0.3) * (1.0 - row * 0.25)
                bar_idx = int(amplitude * (len(WAVE_CHARS) - 1))
                wave_line += WAVE_CHARS[bar_idx]

            row_styles = ["bold #33ff99", "bold #22cc77", "dim green"]
            content.append(f"{wave_line}\n", style=row_styles[row])

        content.append("\n")

        return content

    def _render_thinking(self, tick: int) -> Text:
        """Animação de processamento neural premium."""
        content = Text()
        content.append("\n")

        # Spinner orbital
        spinner = BRAILLE_SPINNER[tick % len(BRAILLE_SPINNER)]
        content.append(f"           {spinner} ", style="bold bright_yellow")
        content.append("Processando", style="bold #ffaa33")
        dots = "." * ((tick % 4) + 1)
        content.append(f"{dots}\n\n", style="bold #ffaa33")

        # Rede neural animada (constelação)
        nodes = ["◆", "◇", "●", "○", "◈", "◉"]
        connectors = [" ─ ", " ╌ ", " ═ ", " ┈ "]

        for row in range(3):
            line = "     "
            for col in range(5):
                phase = tick * 0.4 + row * 1.2 + col * 0.8
                is_active = math.sin(phase) > 0.0
                if is_active:
                    node = nodes[(tick + row + col) % len(nodes)]
                    line += node
                else:
                    line += "·"

                if col < 4:
                    conn_idx = (tick + row + col) % len(connectors)
                    conn_active = math.sin(phase + 0.5) > 0.2
                    if conn_active:
                        line += connectors[conn_idx]
                    else:
                        line += " · "

            style = "bold #ffaa33" if row == 1 else "dim yellow"
            content.append(f"{line}\n", style=style)

        content.append("\n")

        # Barra de progresso indeterminada
        bar_width = 36
        pos = tick % (bar_width * 2)
        if pos >= bar_width:
            pos = bar_width * 2 - pos

        bar_line = "     "
        for i in range(bar_width):
            dist = abs(i - pos)
            if dist == 0:
                bar_line += "█"
            elif dist <= 2:
                bar_line += "▓"
            elif dist <= 4:
                bar_line += "▒"
            elif dist <= 6:
                bar_line += "░"
            else:
                bar_line += "─"

        content.append(f"{bar_line}\n", style="bold #ffaa33")

        return content

    def _render_speaking(self, tick: int, text: str) -> Text:
        """Equalizer premium com gradiente + legenda."""
        content = Text()
        content.append("\n")

        # Header
        content.append("           🔊 ", style="bold")
        content.append("Falando", style="bold bright_cyan")
        content.append("\n\n", style="")

        # Equalizer de 2 linhas com efeito espelho
        bar_count = 38

        # Linha superior (invertida)
        eq_top = "   "
        eq_bot = "   "
        for i in range(bar_count):
            val = (
                math.sin(tick * 0.6 + i * 0.8) * 0.25
                + math.sin(tick * 0.35 + i * 1.5) * 0.25
                + random.random() * 0.5
            )
            val = max(0.05, min(1.0, val))
            bar_idx = int(val * (len(WAVE_CHARS) - 1))
            eq_top += WAVE_CHARS[len(WAVE_CHARS) - 1 - bar_idx]
            eq_bot += WAVE_CHARS[bar_idx]

        content.append(f"{eq_top}\n", style="dim cyan")
        content.append(f"{eq_bot}\n", style="bold bright_cyan")

        # Legenda do que está falando
        if text:
            content.append("\n")
            max_len = self.width - 14
            display_text = text[:max_len] + "…" if len(text) > max_len else text
            content.append(f"   💬 ", style="dim")
            content.append(f"{display_text}\n", style="italic bright_white")

        return content

    def _render_executing(self, tick: int, text: str) -> Text:
        """Animação de execução de ação com estilo premium."""
        content = Text()
        content.append("\n")

        # Spinner com ícone
        spinner = BRAILLE_SPINNER[tick % len(BRAILLE_SPINNER)]
        content.append(f"           {spinner} ", style="bold #ff33aa")
        content.append("Executando ação", style="bold bright_magenta")
        content.append("\n\n", style="")

        # Barra de progresso pulsante
        bar_width = 36
        pulse = (math.sin(tick * 0.3) + 1) / 2  # 0..1
        filled = int(pulse * bar_width)

        bar_line = "     "
        for i in range(bar_width):
            if i < filled:
                bar_line += "█"
            else:
                bar_line += "░"

        content.append(f"{bar_line}\n", style="bold #ff33aa")

        if text:
            content.append(f"\n     ⚡ ", style="bold bright_yellow")
            content.append(f"{text}\n", style="bright_white")

        content.append("\n")

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
                refresh_per_second=12,
                transient=True,
            ) as live:
                while self._running:
                    live.update(self._render_frame())
                    time.sleep(0.083)  # ~12 FPS
        except Exception:
            pass  # Terminal pode fechar durante a animação

    # ─── Boot Sequence ─────────────────────────────────────────

    def play_boot_sequence(self):
        """
        Reproduz a sequência de boot com animação premium.
        Bloqueia até terminar.
        """
        self.set_state(State.BOOTING)

        total_frames = len(BOOT_FRAMES) * 6 + 16

        try:
            with Live(
                self._render_frame(),
                console=self.console,
                refresh_per_second=12,
            ) as live:
                for _ in range(total_frames):
                    live.update(self._render_frame())
                    time.sleep(0.083)
        except Exception:
            pass

        self.set_state(State.IDLE)
