"""
Sounds — Gerador de sons de feedback para o Alfred.

Gera sons programaticamente usando numpy + pygame.
Não precisa de arquivos de áudio externos.

Sons:
- activation: "Beep" curto quando wake word é detectada
- deactivation: Tom descendente ao voltar pro idle
- error: Tom de erro
"""

import io
import math
import struct
import tempfile
import wave
from pathlib import Path

import numpy as np

try:
    import pygame

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


def _generate_tone(
    frequency: float,
    duration: float,
    sample_rate: int = 44100,
    volume: float = 0.3,
    fade_ms: float = 10,
) -> np.ndarray:
    """
    Gera uma onda senoidal com fade-in/fade-out suave.

    Args:
        frequency: Frequência em Hz.
        duration: Duração em segundos.
        sample_rate: Taxa de amostragem.
        volume: Volume (0.0 a 1.0).
        fade_ms: Duração do fade em milissegundos.

    Returns:
        Array numpy com os samples.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave_data = np.sin(2 * np.pi * frequency * t) * volume

    # Fade in/out para evitar clicks
    fade_samples = int(sample_rate * fade_ms / 1000)
    if fade_samples > 0 and len(wave_data) > fade_samples * 2:
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        wave_data[:fade_samples] *= fade_in
        wave_data[-fade_samples:] *= fade_out

    return wave_data


def _to_wav_bytes(samples: np.ndarray, sample_rate: int = 44100) -> bytes:
    """
    Converte array numpy em bytes WAV.

    Args:
        samples: Array de samples (float -1 a 1).
        sample_rate: Taxa de amostragem.

    Returns:
        Bytes do arquivo WAV.
    """
    # Converter para int16
    int_samples = np.int16(samples * 32767)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int_samples.tobytes())

    return buffer.getvalue()


def generate_activation_sound() -> bytes:
    """
    Gera o som de ativação — dois tons ascendentes curtos.
    Similar ao som da Alexa ao ser ativada.

    Returns:
        Bytes do arquivo WAV.
    """
    sr = 44100
    # Tom 1: Dó (523 Hz) por 80ms
    tone1 = _generate_tone(523, 0.08, sr, volume=0.25)
    # Pausa curta (20ms)
    pause = np.zeros(int(sr * 0.02))
    # Tom 2: Mi (659 Hz) por 100ms (mais alto e longo)
    tone2 = _generate_tone(659, 0.10, sr, volume=0.3)

    combined = np.concatenate([tone1, pause, tone2])
    return _to_wav_bytes(combined, sr)


def generate_deactivation_sound() -> bytes:
    """
    Gera o som de desativação — tom descendente curto.

    Returns:
        Bytes do arquivo WAV.
    """
    sr = 44100
    tone1 = _generate_tone(659, 0.06, sr, volume=0.2)
    pause = np.zeros(int(sr * 0.015))
    tone2 = _generate_tone(523, 0.08, sr, volume=0.15)

    combined = np.concatenate([tone1, pause, tone2])
    return _to_wav_bytes(combined, sr)


def generate_error_sound() -> bytes:
    """
    Gera o som de erro — tom baixo e curto.

    Returns:
        Bytes do arquivo WAV.
    """
    sr = 44100
    tone = _generate_tone(220, 0.15, sr, volume=0.25)
    return _to_wav_bytes(tone, sr)


class SoundPlayer:
    """
    Player de sons de feedback.
    Pré-gera os sons na inicialização para resposta instantânea.
    """

    def __init__(self):
        self._sounds: dict[str, bytes] = {}
        self._initialized = False

        if not PYGAME_AVAILABLE:
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self._initialized = True
        except Exception:
            return

        # Pré-gerar todos os sons
        self._sounds = {
            "activation": generate_activation_sound(),
            "deactivation": generate_deactivation_sound(),
            "error": generate_error_sound(),
        }

    def play(self, sound_name: str):
        """
        Reproduz um som de feedback.

        Args:
            sound_name: Nome do som ("activation", "deactivation", "error").
        """
        if not self._initialized or sound_name not in self._sounds:
            return

        try:
            wav_data = self._sounds[sound_name]
            sound_io = io.BytesIO(wav_data)
            sound = pygame.mixer.Sound(sound_io)
            sound.play()
            # Esperar o som terminar (são todos < 300ms)
            pygame.time.wait(int(sound.get_length() * 1000) + 50)
        except Exception:
            pass  # Sons são não-críticos

    @property
    def is_available(self) -> bool:
        """Verifica se o player está funcional."""
        return self._initialized
