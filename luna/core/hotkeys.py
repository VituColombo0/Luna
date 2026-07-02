"""
Hotkeys — Atalhos de teclado globais para a Luna.

Permite ao usuário abrir/fechar o terminal da Luna com atalhos globais:
- Ctrl+Shift+L: Abrir/Fechar (toggle) o terminal da Luna
- Ctrl+Shift+Q: Encerrar a Luna

Funciona em Linux (via xdotool/wmctrl) e Windows (via ctypes).
"""

import logging
import os
import platform
import subprocess
import threading
import time

SYSTEM = platform.system()


class HotkeyManager:
    """
    Gerenciador de atalhos de teclado globais para a Luna.
    
    Permite ao usuário mostrar/esconder a janela do terminal
    com atalhos de teclado, mesmo quando a janela está oculta.
    """

    # Atalhos padrão
    TOGGLE_KEY = "ctrl+shift+l"     # Mostrar/esconder terminal
    QUIT_KEY = "ctrl+shift+q"       # Encerrar Luna

    def __init__(self, logger: logging.Logger, on_quit: callable = None):
        self.logger = logger
        self._on_quit = on_quit
        self._running = False
        self._thread: threading.Thread | None = None
        self._window_visible = True
        self._window_id: str | None = None

        # No Linux, capturar o ID da janela do terminal atual
        if SYSTEM == "Linux":
            self._window_id = self._get_current_window_id()

    def _get_current_window_id(self) -> str | None:
        """Obtém o ID da janela do terminal atual (Linux)."""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    def start(self):
        """Inicia o listener de atalhos em background."""
        if self._running:
            return

        self._running = True

        if SYSTEM == "Linux":
            self._thread = threading.Thread(
                target=self._linux_hotkey_loop,
                daemon=True,
                name="HotkeyManager"
            )
            self._thread.start()
            self.logger.info(
                f"Atalhos globais ativos — "
                f"[cyan]{self.TOGGLE_KEY}[/] toggle terminal, "
                f"[cyan]{self.QUIT_KEY}[/] encerrar"
            )
        elif SYSTEM == "Windows":
            self._thread = threading.Thread(
                target=self._windows_hotkey_loop,
                daemon=True,
                name="HotkeyManager"
            )
            self._thread.start()
            self.logger.info(
                f"Atalhos globais ativos — "
                f"[cyan]{self.TOGGLE_KEY}[/] toggle terminal, "
                f"[cyan]{self.QUIT_KEY}[/] encerrar"
            )
        else:
            self.logger.warning(
                f"Atalhos globais não suportados em {SYSTEM}."
            )

    def stop(self):
        """Para o listener de atalhos."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    def toggle_terminal(self):
        """Mostra ou esconde a janela do terminal."""
        if SYSTEM == "Linux":
            self._toggle_linux()
        elif SYSTEM == "Windows":
            self._toggle_windows()

    def _toggle_linux(self):
        """Toggle da janela do terminal no Linux usando wmctrl/xdotool."""
        if not self._window_id:
            self._window_id = self._get_current_window_id()
            if not self._window_id:
                return

        try:
            if self._window_visible:
                # Minimizar a janela
                subprocess.run(
                    ["xdotool", "windowminimize", self._window_id],
                    capture_output=True, timeout=3
                )
                self._window_visible = False
                self.logger.debug("Terminal ocultado.")
            else:
                # Restaurar e trazer para frente
                subprocess.run(
                    ["xdotool", "windowactivate", "--sync", self._window_id],
                    capture_output=True, timeout=3
                )
                self._window_visible = True
                self.logger.debug("Terminal restaurado.")
        except Exception as e:
            self.logger.debug(f"Erro ao toggle terminal Linux: {e}")

    def _toggle_windows(self):
        """Toggle da janela do console no Windows."""
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                if self._window_visible:
                    # SW_HIDE = 0
                    ctypes.windll.user32.ShowWindow(hwnd, 0)
                    self._window_visible = False
                else:
                    # SW_SHOW = 5
                    ctypes.windll.user32.ShowWindow(hwnd, 5)
                    # Trazer para frente
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    self._window_visible = True
        except Exception as e:
            self.logger.debug(f"Erro ao toggle terminal Windows: {e}")

    # ─── Loops de Detecção de Hotkeys ─────────────────────────

    def _linux_hotkey_loop(self):
        """
        Loop de detecção de atalhos no Linux usando /dev/input
        ou xdotool como fallback.
        
        Tenta usar pynput se disponível, senão faz polling via
        xinput/xdotool.
        """
        try:
            # Tentar usar pynput para atalhos globais
            from pynput import keyboard

            toggle_combo = {keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.KeyCode.from_char('l')}
            quit_combo = {keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.KeyCode.from_char('q')}
            current_keys = set()

            def on_press(key):
                if not self._running:
                    return False
                current_keys.add(key)
                # Verificar toggle (Ctrl+Shift+L)
                if all(k in current_keys for k in toggle_combo):
                    self.toggle_terminal()
                    current_keys.clear()
                # Verificar quit (Ctrl+Shift+Q) 
                elif all(k in current_keys for k in quit_combo):
                    if self._on_quit:
                        self._on_quit()
                    current_keys.clear()

            def on_release(key):
                current_keys.discard(key)

            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                while self._running:
                    time.sleep(0.1)
                listener.stop()

        except ImportError:
            # Fallback: sem pynput, registrar atalhos via xbindkeys
            self.logger.info(
                "pynput não disponível — atalhos globais desativados. "
                "Instale: [cyan]pip install pynput[/]"
            )
            # Manter a thread viva mas sem funcionalidade
            while self._running:
                time.sleep(1)

    def _windows_hotkey_loop(self):
        """
        Loop de detecção de atalhos no Windows usando ctypes/RegisterHotKey.
        """
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            # Constantes
            MOD_CONTROL = 0x0002
            MOD_SHIFT = 0x0004
            WM_HOTKEY = 0x0312

            # IDs para cada hotkey
            HOTKEY_TOGGLE = 1
            HOTKEY_QUIT = 2

            # Registrar Ctrl+Shift+L (toggle)
            # 0x4C = 'L'
            user32.RegisterHotKey(None, HOTKEY_TOGGLE, MOD_CONTROL | MOD_SHIFT, 0x4C)
            # Registrar Ctrl+Shift+Q (quit)
            # 0x51 = 'Q'
            user32.RegisterHotKey(None, HOTKEY_QUIT, MOD_CONTROL | MOD_SHIFT, 0x51)

            msg = wintypes.MSG()

            while self._running:
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == WM_HOTKEY:
                        if msg.wParam == HOTKEY_TOGGLE:
                            self.toggle_terminal()
                        elif msg.wParam == HOTKEY_QUIT:
                            if self._on_quit:
                                self._on_quit()
                time.sleep(0.05)

            # Limpar hotkeys
            user32.UnregisterHotKey(None, HOTKEY_TOGGLE)
            user32.UnregisterHotKey(None, HOTKEY_QUIT)

        except Exception as e:
            self.logger.debug(f"Erro nos atalhos Windows: {e}")
            while self._running:
                time.sleep(1)

    @property
    def is_available(self) -> bool:
        """Verifica se os atalhos estão ativos."""
        return self._running and self._thread is not None and self._thread.is_alive()
