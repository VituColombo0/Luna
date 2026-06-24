"""
Speaker — Módulo de Text-to-Speech (TTS).

Suporta dois backends:
- edge-tts: Vozes neurais da Microsoft (requer internet, qualidade excelente)
- piper: Totalmente offline, leve e rápido
"""

import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path

try:
    import pygame

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


class Speaker:
    """
    Voz do Alfred — converte texto em fala.
    """

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("voice", {})
        self.logger = logger

        self.engine = self.config.get("tts_engine", "edge-tts")
        self.voice = self.config.get("tts_voice", "pt-BR-AntonioNeural")

        # Verificar disponibilidade do engine
        if self.engine == "edge-tts" and not EDGE_TTS_AVAILABLE:
            self.logger.warning(
                "edge-tts não disponível. Instale: [cyan]pip install edge-tts[/]"
            )

        self.logger.info(
            f"Speaker inicializado — engine: [cyan]{self.engine}[/], "
            f"voz: [cyan]{self.voice}[/]"
        )

        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception as e:
                self.logger.error(f"Erro ao inicializar pygame mixer: {e}")
        else:
            self.logger.warning("pygame não disponível. Instale: [cyan]pip install pygame[/]")

    def speak(self, text: str):
        """
        Converte texto em fala e reproduz.

        Args:
            text: Texto a ser falado.
        """
        if not text or not text.strip():
            return

        try:
            if self.engine == "edge-tts":
                self._speak_edge_tts(text)
            elif self.engine == "piper":
                self._speak_piper(text)
            else:
                self.logger.warning(f"Engine TTS desconhecido: {self.engine}")

        except Exception as e:
            self.logger.error(f"Erro no TTS: {e}")

    def _speak_edge_tts(self, text: str):
        """
        Usa edge-tts (Microsoft Neural TTS) para sintetizar e reproduzir voz.

        Args:
            text: Texto para sintetizar.
        """
        if not EDGE_TTS_AVAILABLE:
            self.logger.warning("edge-tts não instalado.")
            return

        async def _generate_and_play():
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ) as tmp:
                tmp_path = tmp.name

            try:
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(tmp_path)
                self._play_audio(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        # Rodar o async de forma bloqueante (thread-safe)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import threading
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(_generate_and_play())
                new_loop.close()
            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
        else:
            asyncio.run(_generate_and_play())

    def _speak_piper(self, text: str):
        """
        Usa Piper TTS (offline) para sintetizar e reproduzir voz.

        Args:
            text: Texto para sintetizar.
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Piper é chamado via CLI
            result = subprocess.run(
                ["piper", "--model", self.voice, "--output_file", tmp_path],
                input=text,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self._play_audio(tmp_path)
            else:
                self.logger.error(f"Piper erro: {result.stderr}")

        except FileNotFoundError:
            self.logger.error(
                "Piper não encontrado. Instale: [cyan]pip install piper-tts[/]"
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _play_audio(self, file_path: str):
        """
        Reproduz um arquivo de áudio usando pygame (cross-platform).

        Args:
            file_path: Caminho do arquivo de áudio.
        """
        if not PYGAME_AVAILABLE:
            self.logger.error("pygame não instalado. Não é possível reproduzir áudio.")
            return

        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            # Unload explicitly so the file can be deleted on Windows
            if hasattr(pygame.mixer.music, 'unload'):
                pygame.mixer.music.unload()
        except Exception as e:
            self.logger.error(f"Erro ao reproduzir áudio com pygame: {e}")

    @property
    def is_available(self) -> bool:
        """Verifica se o TTS está funcional."""
        if self.engine == "edge-tts":
            return EDGE_TTS_AVAILABLE
        return True  # Piper é verificado em runtime
