import time
import logging
from luna.utils.logger import setup_logger
from luna.voice.wake_word import WakeWordDetector

def on_wake_word(command):
    print(f"\n🔔 WAKE WORD DETECTADA! Comando recebido: '{command}'")
    print("⏳ Voltando a ouvir silenciosamente... (Diga 'Luna' de novo!)\n")

print("Inicializando detector de Wake Word para teste...")
logger = setup_logger()

# Configuração simulada da Luna
config = {
    "voice": {
        "wake_word": "luna", 
        "stt_language": "pt"
    }
}

detector = WakeWordDetector(config, logger)

while True:
    if detector.is_available:
        detector.start(callback=on_wake_word)
        print("\n🎤 Diga 'Luna' (ou 'Luna, que horas são?') para testar.")
        print("🛑 Pressione Ctrl+C para encerrar o teste.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nEncerrando detector...")
            detector.stop()
            print("Teste finalizado.")
    else:
        print("\n❌ ERRO: O detector de wake word não está disponível.")
        print("Certifique-se de que os pacotes 'sounddevice' e 'faster-whisper' estão instalados.")
