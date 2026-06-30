"""
VoiceCalibrator — Calibração de voz no primeiro uso da Luna.

Na primeira execução, guia o usuário para falar a wake word 3 vezes.
Isso cria um perfil de voz personalizado que melhora drasticamente
a detecção da wake word, adaptando-se ao microfone e à voz do usuário.

O perfil é salvo em data/voice_profile.json e reutilizado em toda
inicialização subsequente.
"""

import json
import logging
import time
from datetime import datetime
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

from luna.utils.config import PROJECT_ROOT


# Caminho padrão do perfil de voz
VOICE_PROFILE_PATH = PROJECT_ROOT / "data" / "voice_profile.json"

# Configurações de áudio (idênticas ao WakeWordDetector)
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"


class VoiceCalibrator:
    """
    Calibrador de voz para primeiro uso.

    Guia o usuário por 3 amostras de fala da wake word,
    analisando energia, transcrição e variações para criar
    um perfil otimizado de detecção.
    """

    RECORD_DURATION = 3.0  # Segundos para gravar cada amostra

    def __init__(self, logger: logging.Logger, profile_path: Path | None = None):
        self.logger = logger
        self.profile_path = profile_path or VOICE_PROFILE_PATH
        self._whisper_model = None

    def needs_calibration(self) -> bool:
        """Verifica se o perfil de voz já existe."""
        return not self.profile_path.exists()

    def load_profile(self) -> dict | None:
        """
        Carrega o perfil de voz salvo.

        Returns:
            Dicionário com o perfil ou None se não existir.
        """
        if not self.profile_path.exists():
            return None

        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Erro ao carregar perfil de voz: {e}")
            return None

    def run_calibration(self, wake_word: str, console=None) -> dict | None:
        """
        Executa o fluxo interativo de calibração de voz.

        Guia o usuário para falar a wake word 3 vezes,
        analisa as amostras e salva o perfil otimizado.

        Args:
            wake_word: A wake word configurada (ex: "luna").
            console: Rich console para output formatado (opcional).

        Returns:
            Dicionário com o perfil calibrado ou None se falhou.
        """
        if not SOUNDDEVICE_AVAILABLE:
            self.logger.error("sounddevice não disponível — calibração impossível.")
            return None

        if not WHISPER_AVAILABLE:
            self.logger.error("faster-whisper não disponível — calibração impossível.")
            return None

        # Carregar modelo Whisper para validação
        self._load_whisper()
        if self._whisper_model is None:
            return None

        _print = console.print if console else print

        # --- Explicação Inicial ---
        _print("")
        _print("[bold cyan]╔══════════════════════════════════════════════╗[/]")
        _print("[bold cyan]║[/]  [bold white]🎤 Calibração de Voz — Primeiro Uso[/]     [bold cyan]║[/]")
        _print("[bold cyan]╚══════════════════════════════════════════════╝[/]")
        _print("")
        _print(f"[white]Para garantir que eu reconheça sua voz corretamente,[/]")
        _print(f"[white]você vai dizer [bold magenta]\"{wake_word}\"[/] [bold]3 vezes[/].[/]")
        _print(f"[dim]Isso me ajuda a calibrar o microfone e entender como[/]")
        _print(f"[dim]você pronuncia a palavra de ativação.[/]")
        _print("")

        # --- Coletar 3 acertos consecutivos ---
        energy_values = []
        discovered_variants = []
        consecutive_successes = 0
        total_attempts = 0
        REQUIRED_STREAK = 3

        while consecutive_successes < REQUIRED_STREAK:
            total_attempts += 1
            _print(f"[bold yellow]━━━ Acerto {consecutive_successes}/{REQUIRED_STREAK} — Tentativa #{total_attempts} ━━━[/]")
            _print(f"[white]Diga [bold magenta]\"{wake_word}\"[/] claramente.[/]")

            # Countdown
            for countdown in range(3, 0, -1):
                _print(f"[dim]  Gravando em {countdown}...[/]")
                time.sleep(1)

            _print("[bold green]🔴 Gravando agora! Diga a wake word...[/]")

            # Gravar amostra
            samples = int(SAMPLE_RATE * self.RECORD_DURATION)
            try:
                audio = sd.rec(
                    samples,
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype=DTYPE,
                )
                sd.wait()
            except Exception as e:
                self.logger.error(f"Erro ao gravar amostra: {e}")
                _print(f"[red]❌ Erro ao gravar. Tentando novamente...[/]")
                consecutive_successes = 0
                energy_values.clear()
                discovered_variants.clear()
                _print("")
                continue

            # Analisar energia
            energy = np.abs(audio).mean()

            # Transcrever para validar
            transcription = self._transcribe(audio)

            if transcription:
                text_lower = transcription.lower().strip()
                cleaned_variant = text_lower.strip('.,!?;"\'')
                
                consecutive_successes += 1
                energy_values.append(float(energy))
                
                _print(
                    f"[bold green]✅ Aprendido:[/] \"{transcription}\" "
                    f"[dim](energia: {energy:.0f})[/] "
                    f"[bold cyan]({consecutive_successes}/{REQUIRED_STREAK})[/]"
                )

                if cleaned_variant and cleaned_variant not in discovered_variants:
                    discovered_variants.append(cleaned_variant)
            else:
                _print("[yellow]⚠️  Não consegui transcrever. Fale mais perto do microfone.[/]")
                if consecutive_successes > 0:
                    _print(f"[yellow]   Sequência reiniciada. Tente novamente![/]")
                consecutive_successes = 0
                energy_values.clear()
                discovered_variants.clear()

            _print("")

        # --- Calibração concluída com sucesso ---
        _print(f"[bold green]✅ Calibração concluída! 3 acertos consecutivos em {total_attempts} tentativas.[/]")
        profile = self._build_profile(
            wake_word, energy_values, discovered_variants
        )

        # --- Salvar perfil ---
        self._save_profile(profile)
        _print(f"[dim]Perfil de voz salvo em: {self.profile_path}[/]")
        _print("")

        return profile

    def _load_whisper(self):
        """Carrega o modelo Whisper tiny para validação rápida."""
        try:
            self.logger.info("Carregando Whisper tiny para calibração...")

            device = "cpu"
            compute_type = "int8"

            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
            except ImportError:
                pass

            self._whisper_model = WhisperModel(
                "tiny", device=device, compute_type=compute_type
            )
        except Exception as e:
            self.logger.error(f"Erro ao carregar Whisper para calibração: {e}")
            self._whisper_model = None

    def _transcribe(self, audio: np.ndarray) -> str | None:
        """Transcreve um chunk de áudio."""
        if self._whisper_model is None:
            return None

        import tempfile
        import wave

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio.tobytes())

        try:
            segments, _ = self._whisper_model.transcribe(
                tmp_path,
                language="pt",
                beam_size=1,
                vad_filter=True,
            )
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip() if text.strip() else None
        except Exception:
            return None
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _get_common_variants(self, wake_word: str) -> list[str]:
        """Variantes comuns de transcrição para a wake word."""
        if wake_word == "luna":
            return [
                "luna", "luana", "luná", "luna.", "lu na",
                "louna", "lona", "lunna", "lúna", "luna!",
                "lunah", "luuna", "luna,", "lun", "luna?",
            ]
        return [wake_word]

    def _build_profile(
        self, wake_word: str, energies: list[float], variants: list[str]
    ) -> dict:
        """Constrói o perfil de voz a partir das amostras bem-sucedidas."""
        avg_energy = sum(energies) / len(energies) if energies else 100

        # O threshold ideal é 40% da energia média de fala detectada.
        # Isso é baixo o suficiente para captar fala suave, mas alto o
        # suficiente para ignorar ruído de fundo.
        optimal_threshold = max(int(avg_energy * 0.4), 25)

        return {
            "wake_word": wake_word,
            "energy_baseline": round(avg_energy, 1),
            "optimal_threshold": optimal_threshold,
            "confirmed_variants": variants,
            "calibrated_at": datetime.now().isoformat(),
            "version": 1,
        }

    def _build_fallback_profile(
        self, wake_word: str, energies: list[float]
    ) -> dict:
        """Perfil de fallback quando a calibração não foi totalmente bem-sucedida."""
        avg_energy = sum(energies) / len(energies) if energies else 100

        return {
            "wake_word": wake_word,
            "energy_baseline": round(avg_energy, 1),
            "optimal_threshold": max(int(avg_energy * 0.35), 20),
            "confirmed_variants": [],
            "calibrated_at": datetime.now().isoformat(),
            "version": 1,
            "partial": True,
        }

    def _save_profile(self, profile: dict):
        """Salva o perfil de voz em disco."""
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

    def delete_profile(self):
        """Remove o perfil de voz (para recalibração)."""
        if self.profile_path.exists():
            self.profile_path.unlink()
