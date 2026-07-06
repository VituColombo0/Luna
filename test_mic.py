import sounddevice as sd
import numpy as np

print("--- Dispositivos de Áudio Disponíveis ---")
print(sd.query_devices())
print("\n--- Dispositivo Padrão ---")
print(sd.query_devices(kind='input'))

print("\nGravando 2 segundos de áudio para testar volume...")
try:
    audio = sd.rec(int(16000 * 10), samplerate=16000, channels=1, dtype='int16')
    sd.wait()
    vol = np.abs(audio).mean()
    print(f"Volume médio detectado: {vol}")
    if vol == 0:
        print("ERRO: O volume está em 0. O microfone está mudo ou é o dispositivo errado.")
    elif vol < 100:
        print("AVISO: O volume está MUITO baixo. Fale mais perto ou aumente o ganho do microfone.")
    else:
        print("SUCESSO: Áudio detectado normalmente.")
except Exception as e:
    print(f"Erro ao gravar: {e}")
