"""
Utilitário para gerar config/config.yaml em UTF-8.

Chamado pelo install.bat no Windows para evitar problemas
de encoding do cmd.exe (que usa CP1252 por padrão).

Uso: python _generate_config.py <name> <nickname> <bio> <model> <tts_voice>
"""

import sys
from pathlib import Path


def main():
    if len(sys.argv) < 6:
        print("Uso: python _generate_config.py <name> <nickname> <bio> <model> <tts_voice>")
        sys.exit(1)

    name = sys.argv[1]
    nickname = sys.argv[2]
    bio = sys.argv[3]
    model = sys.argv[4]
    tts_voice = sys.argv[5]

    config_content = f"""# ============================================
# Alfred — Configuração Pessoal
# ============================================
# Gerado automaticamente por install.bat

# --- Seu Perfil ---
user:
  name: "{name}"
  nickname: "{nickname}"
  bio: "{bio}"

# --- Modelo de Linguagem ---
llm:
  model: "{model}"
  vision_model: "moondream"
  temperature: 0.7
  ollama_host: "http://localhost:11434"

# --- Voz ---
voice:
  stt_model: "base"
  stt_language: "pt"
  tts_engine: "edge-tts"
  tts_voice: "{tts_voice}"
  wake_word: "alfred"

# --- Visão ---
vision:
  enabled: true
  camera_index: 0
  face_recognition: true
  faces_dir: "data/faces"

# --- Memória ---
memory:
  enabled: true
  db_path: "data/memory"
  max_context_items: 5
  auto_save: true

# --- Ações ---
actions:
  enabled: true
  allowed_paths:
    - "~/Documents"
    - "~/Downloads"
    - "~/Videos"
    - "~/Music"
    - "~/Desktop"
  allow_browser: true
  allow_system_commands: false
"""

    config_path = Path("config/config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_content, encoding="utf-8")
    print(f"Config salvo em: {config_path}")


if __name__ == "__main__":
    main()
