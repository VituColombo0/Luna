"""
Listener — Módulo de Speech-to-Text (STT).

Usa o Faster-Whisper para converter áudio do microfone em texto.
Suporta detecção de silêncio para saber quando o usuário parou de falar.
"""

import logging
import io
import wave
import tempfile
from pathlib import Path

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


class Listener:
    """
    Ouvinte do Alfred — captura áudio do microfone e transcreve para texto.
    """

    # Configurações de áudio
    SAMPLE_RATE = 16000
    CHANNELS = 1
    DTYPE = "int16"

    # Detecção de silêncio
    SILENCE_THRESHOLD = 500  # Amplitude mínima para considerar fala
    SILENCE_DURATION = 1.5  # Segundos de silêncio para parar
    MAX_DURATION = 30  # Duração máxima de gravação em segundos

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("voice", {})
        self.logger = logger

        self.model_size = self.config.get("stt_model", "base")
        self.language = self.config.get("stt_language", "pt")

        self.whisper_model = None

        if not SOUNDDEVICE_AVAILABLE:
            self.logger.warning(
                "sounddevice não disponível — modo de voz desativado. "
                "Instale com: [cyan]pip install sounddevice[/]"
            )

        if WHISPER_AVAILABLE:
            self._load_model()
        else:
            self.logger.warning(
                "faster-whisper não disponível. "
                "Instale com: [cyan]pip install faster-whisper[/]"
            )

    def _load_model(self):
        """Carrega o modelo Whisper na memória."""
        try:
            self.logger.info(
                f"Carregando modelo Whisper [cyan]{self.model_size}[/]..."
            )
            self.whisper_model = WhisperModel(
                self.model_size,
                device="cpu",  # CPU para não competir VRAM com o LLM
                compute_type="int8",  # Otimizado para velocidade
            )
            self.logger.info("Modelo Whisper carregado com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao carregar Whisper: {e}")
            self.whisper_model = None

    def listen(self) -> str | None:
        """
        Grava áudio do microfone até detectar silêncio e transcreve.

        Returns:
            Texto transcrito ou None se nada for detectado.
        """
        if not SOUNDDEVICE_AVAILABLE or self.whisper_model is None:
            self.logger.warning("STT não disponível.")
            return None

        try:
            audio_data = self._record_until_silence()
            if audio_data is None or len(audio_data) < self.SAMPLE_RATE:
                return None  # Gravação muito curta

            return self._transcribe(audio_data)

        except Exception as e:
            self.logger.error(f"Erro na escuta: {e}")
            return None

    def _record_until_silence(self) -> np.ndarray | None:
        """
        Grava áudio do microfone até detectar silêncio prolongado.

        Returns:
            Array numpy com os dados de áudio ou None.
        """
        frames = []
        silent_frames = 0
        frames_per_check = int(self.SAMPLE_RATE * 0.1)  # Checar a cada 100ms
        max_frames = int(self.MAX_DURATION * self.SAMPLE_RATE / frames_per_check)
        silence_limit = int(self.SILENCE_DURATION / 0.1)

        has_speech = False

        for _ in range(max_frames):
            chunk = sd.rec(
                frames_per_check,
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
            )
            sd.wait()

            amplitude = np.abs(chunk).mean()

            if amplitude > self.SILENCE_THRESHOLD:
                has_speech = True
                silent_frames = 0
                frames.append(chunk)
            else:
                if has_speech:
                    silent_frames += 1
                    frames.append(chunk)

                    if silent_frames >= silence_limit:
                        break

        if not has_speech:
            return None

        return np.concatenate(frames)

    def _transcribe(self, audio: np.ndarray) -> str | None:
        """
        Transcreve um array de áudio usando Faster-Whisper.

        Args:
            audio: Array numpy com dados de áudio (int16, 16kHz).

        Returns:
            Texto transcrito ou None.
        """
        # Salvar em arquivo WAV temporário (Whisper precisa de arquivo)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(2)  # int16 = 2 bytes
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(audio.tobytes())

        try:
            segments, info = self.whisper_model.transcribe(
                tmp_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,  # Filtro de atividade de voz
            )

            text = " ".join(seg.text.strip() for seg in segments)

            if text.strip():
                self.logger.debug(f"Transcrito: {text}")
                return text.strip()

            return None

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @property
    def is_available(self) -> bool:
        """Verifica se o STT está funcional."""
        return SOUNDDEVICE_AVAILABLE and self.whisper_model is not None
