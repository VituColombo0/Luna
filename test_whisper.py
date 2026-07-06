import sounddevice as sd
import numpy as np
import tempfile
import wave
import os
from faster_whisper import WhisperModel

print("Carregando modelo Whisper 'tiny'...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")

print("\n--- TESTE DE TRANSCRIÇÃO ---")
print("Vou gravar 4 segundos. Por favor, diga a palavra mágica 'Alfred' de várias formas.")
print("Gravando em 3... 2... 1... FALE AGORA!")

# Record 4 seconds
audio = sd.rec(int(16000 * 4), samplerate=16000, channels=1, dtype='int16')
sd.wait()

print("\nGravação concluída. Transcrevendo...")

# Save to wav
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    tmp_path = tmp.name
    with wave.open(tmp, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio.tobytes())

# Transcribe
try:
    segments, info = model.transcribe(tmp_path, language="pt", beam_size=1, vad_filter=True)
    text = " ".join(seg.text.strip() for seg in segments)
    print("\n=================================")
    print(f"A IA ESCUTOU EXATAMENTE ISSO:\n'{text}'")
    print("=================================\n")
    
    # Check if any variant is in text
    variants = ["alfred", "alfredo", "alfrede", "alfret", "al fred", "alford", "elfred", "alfread", "alferd", "olfred", "alfrid", "all fred", "alfre"]
    text_lower = text.lower()
    found = [v for v in variants if v in text_lower]
    if found:
        print(f"-> Wake word ativaria com sucesso! Variantes detectadas: {found}")
    else:
        print("-> FALHA: A wake word NÃO ativaria. A palavra não foi reconhecida.")

finally:
    os.remove(tmp_path)
