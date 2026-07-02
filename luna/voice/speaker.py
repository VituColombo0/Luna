"""
Speaker — Módulo de Text-to-Speech (TTS).

Suporta dois backends:
- edge-tts: Vozes neurais da Microsoft (requer internet, qualidade excelente)
- piper: Totalmente offline, leve e rápido

Otimizado para resposta rápida:
- Cache de áudio para frases repetidas
- Async otimizado com event loop reutilizável
- Reprodução não-bloqueante quando possível
"""

import asyncio
import hashlib
import logging
import os
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
    Voz do Luna — converte texto em fala.
    
    Otimizado com cache de áudio para respostas frequentes
    e event loop reutilizável para edge-tts.
    """

    # Cache para evitar re-sintetizar frases repetidas
    MAX_CACHE_SIZE = 50

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("voice", {})
        self.logger = logger

        self.engine = self.config.get("tts_engine", "edge-tts")
        self.voice = self.config.get("tts_voice", "pt-BR-AntonioNeural")
        self.rate = self.config.get("tts_rate", "+10%")

        # Cache de áudio TTS
        self._cache_dir = Path(tempfile.gettempdir()) / "luna_tts_cache"
        self._cache_dir.mkdir(exist_ok=True)
        self._cache_keys: list[str] = []

        # Verificar disponibilidade do engine
        if self.engine == "edge-tts" and not EDGE_TTS_AVAILABLE:
            self.logger.warning(
                "edge-tts não disponível. Instale: [cyan]pip install edge-tts[/]"
            )

        self.logger.info(
            f"Speaker inicializado — engine: [cyan]{self.engine}[/], "
            f"voz: [cyan]{self.voice}[/], rate: [cyan]{self.rate}[/]"
        )

        if PYGAME_AVAILABLE:
            try:
                if not pygame.mixer.get_init():
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

    def _get_cache_path(self, text: str) -> Path:
        """Gera um caminho de cache baseado no hash do texto + voz."""
        key = f"{self.voice}:{self.rate}:{text}"
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self._cache_dir / f"{hash_key}.mp3"

    def _speak_edge_tts(self, text: str):
        """
        Usa edge-tts (Microsoft Neural TTS) para sintetizar e reproduzir voz.

        Otimizado com cache: se a mesma frase já foi sintetizada, reproduz
        direto do cache sem re-sintetizar.

        Args:
            text: Texto para sintetizar.
        """
        if not EDGE_TTS_AVAILABLE:
            self.logger.warning("edge-tts não instalado.")
            return

        # Verificar cache
        cache_path = self._get_cache_path(text)
        if cache_path.exists():
            self._play_audio(str(cache_path))
            return

        async def _generate():
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
            await communicate.save(str(cache_path))

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
                new_loop.run_until_complete(_generate())
                new_loop.close()
            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
        else:
            asyncio.run(_generate())

        # Gerenciar tamanho do cache
        self._cache_keys.append(str(cache_path))
        if len(self._cache_keys) > self.MAX_CACHE_SIZE:
            old = self._cache_keys.pop(0)
            try:
                Path(old).unlink(missing_ok=True)
            except Exception:
                pass

        # Reproduzir
        self._play_audio(str(cache_path))

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
                time.sleep(0.05)  # Poll mais rápido (50ms vs 100ms)
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
