"""
WakeWordDetector — Detecção contínua de wake word para a Luna.

Funciona como a Alexa: fica ouvindo em background 24/7 com baixo uso de CPU.
Quando detecta a palavra "Luna", emite um beep e ativa o modo de escuta.

Estratégia:
1. Captura áudio continuamente em chunks curtos (1-2 segundos)
2. Usa VAD (Voice Activity Detection) baseado em energia para ignorar silêncio
3. Quando detecta fala, transcreve o chunk com Whisper (modelo tiny = rápido)
4. Se a transcrição contém a wake word, ativa o callback

Isso é 100% offline e não precisa de serviços externos.
"""

import logging
import threading
import time
from typing import Callable

import numpy as np

try:
    import sounddevice as sd

    SOUNDDEVICE_AVAILABLE = True
except (ImportError, OSError):
    SOUNDDEVICE_AVAILABLE = False

try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


class WakeWordDetector:
    """
    Detector de wake word que roda em background.

    Usa Whisper tiny para transcrever chunks curtos de áudio
    e procura a wake word na transcrição.
    """

    # Configurações de áudio
    SAMPLE_RATE = 16000
    CHANNELS = 1
    DTYPE = "int16"

    # Detecção de atividade de voz
    ENERGY_THRESHOLD = 50            # Limiar de energia para considerar fala (baixo para captar mais)
    CHUNK_DURATION = 2.5             # Duração do chunk em segundos
    SILENCE_SKIP_DURATION = 0.3      # Duração para checar silêncio antes de gravar

    def __init__(self, config: dict, logger: logging.Logger, voice_profile: dict | None = None):
        self.config = config.get("voice", {})
        self.logger = logger
        self._voice_profile = voice_profile

        self.wake_word = self.config.get("wake_word", "luna").lower()
        # Variações comuns do wake word (erros de transcrição do Whisper)
        self.wake_word_variants = self._build_variants(self.wake_word)

        # Incorporar variantes descobertas durante a calibração
        if voice_profile and voice_profile.get("confirmed_variants"):
            for variant in voice_profile["confirmed_variants"]:
                v_lower = variant.lower().strip()
                if v_lower and v_lower not in self.wake_word_variants:
                    self.wake_word_variants.append(v_lower)
            self.logger.info(
                f"Perfil de voz carregado — {len(voice_profile['confirmed_variants'])} "
                f"variantes confirmadas adicionadas."
            )

        self._running = False
        self._thread: threading.Thread | None = None
        self._callback: Callable | None = None
        self._paused = False
        self._lock = threading.Lock()

        # Modelo Whisper dedicado para wake word (tiny = mais rápido)
        self._whisper_model = None
        self._language = self.config.get("stt_language", "pt")

        if not SOUNDDEVICE_AVAILABLE:
            self.logger.warning(
                "sounddevice não disponível — wake word desativado."
            )
            return

        if WHISPER_AVAILABLE:
            self._load_model()
        else:
            self.logger.warning(
                "faster-whisper não disponível — wake word desativado."
            )

        # Usar threshold do perfil de voz se disponível, senão auto-calibrar
        if voice_profile and voice_profile.get("optimal_threshold"):
            self.ENERGY_THRESHOLD = voice_profile["optimal_threshold"]
            self.logger.info(
                f"Threshold do perfil de voz: [cyan]{self.ENERGY_THRESHOLD}[/]"
            )
        elif SOUNDDEVICE_AVAILABLE:
            self._calibrate_noise_floor()

    def _calibrate_noise_floor(self):
        """
        Mede o nível de ruído ambiente por ~1 segundo e ajusta
        o ENERGY_THRESHOLD para ficar ligeiramente acima disso.
        Evita que o mic fique 'surdo' em ambientes muito silenciosos
        ou disparando em ambientes ruidosos.
        """
        try:
            samples = int(self.SAMPLE_RATE * 1.0)
            noise_sample = sd.rec(
                samples,
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
            )
            sd.wait()
            noise_level = np.abs(noise_sample).mean()

            # Threshold = ruído ambiente + margem de 50%
            calibrated = max(int(noise_level * 1.3), 25)  # mínimo de 25
            self.ENERGY_THRESHOLD = calibrated
            self.logger.info(
                f"Ruído ambiente: [cyan]{noise_level:.0f}[/] → "
                f"threshold calibrado: [cyan]{calibrated}[/]"
            )
        except Exception as e:
            self.logger.debug(f"Não foi possível calibrar microfone: {e}")

    def _build_variants(self, wake_word: str) -> list[str]:
        """
        Constrói variações da wake word para lidar com erros
        comuns de transcrição do Whisper.

        Args:
            wake_word: Palavra de ativação configurada.

        Returns:
            Lista de variações possíveis.
        """
        variants = [wake_word]

        if wake_word == "luna":
            variants.extend([
                "luna", "luana", "luná", "luna.",
                "lu na", "louna", "lona",
                "lunna", "lúna", "luna!", "lunah",
                "luuna", "luna,", "lun", "luna?",
            ])

        return list(set(v.lower() for v in variants))

    def _load_model(self):
        """Carrega o modelo Whisper tiny para detecção rápida."""
        try:
            self.logger.info(
                "Carregando modelo Whisper [cyan]tiny[/] para wake word..."
            )

            # Auto-detectar dispositivo: CUDA se disponível, senão CPU
            device = "cpu"
            compute_type = "int8"

            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
            except ImportError:
                try:
                    import ctypes
                    ctypes.cdll.LoadLibrary("libcudart.so")
                    device = "cuda"
                    compute_type = "float16"
                except (OSError, Exception):
                    pass  # Usar CPU

            self._whisper_model = WhisperModel(
                "tiny",
                device=device,
                compute_type=compute_type,
            )
            self.logger.info(
                f"Wake word detector pronto (device=[cyan]{device}[/])."
            )
        except Exception as e:
            self.logger.error(f"Erro ao carregar Whisper para wake word: {e}")
            # Fallback para CPU
            if "cuda" in str(e).lower() or "gpu" in str(e).lower():
                try:
                    self._whisper_model = WhisperModel(
                        "tiny", device="cpu", compute_type="int8"
                    )
                    self.logger.info("Wake word detector pronto (CPU fallback).")
                    return
                except Exception:
                    pass
            self._whisper_model = None

    def start(self, callback: Callable):
        """
        Inicia a detecção de wake word em background.

        Args:
            callback: Função chamada quando a wake word é detectada.
                      Recebe o texto completo do chunk transcrito.
        """
        if not self.is_available:
            self.logger.warning("Wake word detector não disponível.")
            return

        if getattr(self, '_running', False) and self._thread is not None:
            self.logger.warning("Wake word detector já está rodando.")
            return

        self._callback = callback
        self._running = True
        self._paused = False
        self._thread = threading.Thread(
            target=self._detection_loop,
            daemon=True,
            name="WakeWordDetector",
        )
        self._thread.start()
        self.logger.info(
            f'Wake word ativo — aguardando "[bold]{self.wake_word}[/]"'
        )

    def stop(self):
        """Para a detecção de wake word."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def pause(self):
        """Pausa temporariamente a detecção (durante fala da Luna)."""
        with self._lock:
            self._paused = True

    def resume(self):
        """Retoma a detecção após pausa."""
        with self._lock:
            self._paused = False

    def _detection_loop(self):
        """
        Loop principal de detecção em background.

        1. Captura chunks curtos de áudio
        2. Verifica se há atividade de voz (energia acima do limiar)
        3. Se sim, transcreve e procura a wake word
        4. Se encontrou, chama o callback
        """
        import tempfile
        import wave
        from pathlib import Path

        chunk_samples = int(self.SAMPLE_RATE * self.CHUNK_DURATION)
        check_samples = int(self.SAMPLE_RATE * self.SILENCE_SKIP_DURATION)

        while self._running:
            try:
                # Verificar se está pausado
                with self._lock:
                    is_paused = self._paused
                
                if is_paused:
                    time.sleep(0.1)
                    continue

                # Primeiro: checar rapidamente se há som
                quick_check = sd.rec(
                    check_samples,
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    dtype=self.DTYPE,
                )
                sd.wait()

                energy = np.abs(quick_check).mean()

                if energy < self.ENERGY_THRESHOLD:
                    # Silêncio — pular, não gastar CPU transcrevendo
                    time.sleep(0.05)
                    continue

                # Tem som! Gravar chunk completo
                chunk = sd.rec(
                    chunk_samples,
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    dtype=self.DTYPE,
                )
                sd.wait()

                # Transcrever com Whisper
                text = self._transcribe_chunk(chunk)

                if text and self._contains_wake_word(text):
                    self.logger.info(
                        f'Wake word detectada: "[bold green]{text}[/]"'
                    )
                    if self._callback:
                        # Extrair o comando após a wake word (se houver)
                        command = self._extract_command(text)
                        self._callback(command)

            except Exception as e:
                if self._running:
                    self.logger.debug(f"Erro no wake word loop: {e}")
                    time.sleep(0.5)

    def _transcribe_chunk(self, audio: np.ndarray) -> str | None:
        """
        Transcreve um chunk de áudio rapidamente.

        Args:
            audio: Array numpy com dados de áudio.

        Returns:
            Texto transcrito ou None.
        """
        if self._whisper_model is None:
            return None

        import tempfile
        import wave
        from pathlib import Path

        # Salvar em WAV temporário
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(audio.tobytes())

        try:
            segments, _ = self._whisper_model.transcribe(
                tmp_path,
                language=self._language,
                beam_size=1,       # Beam 1 = mais rápido
                vad_filter=True,
            )

            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip() if text.strip() else None

        except Exception:
            return None
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _contains_wake_word(self, text: str) -> bool:
        """
        Verifica se o texto contém a wake word ou variações.

        Args:
            text: Texto transcrito.

        Returns:
            True se contém a wake word.
        """
        text_lower = text.lower()
        return any(variant in text_lower for variant in self.wake_word_variants)

    def _extract_command(self, text: str) -> str:
        """
        Extrai o comando após a wake word.

        Exemplo:
            "Luna, que horas são?" → "que horas são?"
            "Luna" → "" (sem comando, apenas ativação)

        Args:
            text: Texto completo transcrito.

        Returns:
            Comando extraído ou string vazia.
        """
        text_lower = text.lower()

        # Encontrar a posição da wake word
        for variant in sorted(self.wake_word_variants, key=len, reverse=True):
            pos = text_lower.find(variant)
            if pos >= 0:
                after = text[pos + len(variant):]
                # Limpar pontuação e espaços iniciais
                after = after.lstrip(" ,.:;!?-")
                return after.strip()

        return ""

    @property
    def is_available(self) -> bool:
        """Verifica se o detector está funcional."""
        return SOUNDDEVICE_AVAILABLE and self._whisper_model is not None
