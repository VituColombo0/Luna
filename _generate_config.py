"""
Utilitário para gerar config/config.yaml em UTF-8.

Chamado pelo install.bat no Windows para evitar problemas
de encoding do cmd.exe (que usa CP1252 por padrão).

Uso: python _generate_config.py <name> <nickname> <bio>
"""

import sys
from pathlib import Path


def main():
    if len(sys.argv) < 4:
        print("Uso: python _generate_config.py <name> <nickname> <bio>")
        sys.exit(1)

    name = sys.argv[1]
    nickname = sys.argv[2]
    bio = sys.argv[3]

    config_content = f"""# ============================================
# Luna — Configuração Pessoal
# ============================================
# Gerado automaticamente pelo instalador

# --- Seu Perfil ---
user:
  name: "{name}"
  nickname: "{nickname}"
  bio: "{bio}"

# --- Modelo de Linguagem ---
llm:
  model: "qwen2.5:1.5b"
  vision_model: "moondream"
  temperature: 0.7
  max_tokens: 200
  ollama_host: "http://localhost:11434"

# --- Voz ---
voice:
  stt_model: "base"
  stt_language: "pt"
  tts_engine: "edge-tts"
  tts_voice: "pt-BR-ThalitaMultilingualNeural"
  tts_rate: "+15%"
  wake_word: "luna"

# --- Visão ---
vision:
  enabled: true
  camera_index: 0
  face_recognition: true
  faces_dir: "data/faces"

# --- Memória (Obsidian Vault) ---
memory:
  enabled: true
  vault_path: "data/obsidian"
  max_context_items: 8
  recent_days: 3
  auto_save: true

# --- Ações ---
actions:
  enabled: true
  allowed_paths:
    - "~"
    - "~/Documents"
    - "~/Downloads"
    - "~/Videos"
    - "~/Music"
    - "~/Desktop"
  allow_browser: true
  allow_system_commands: true
"""

    config_path = Path("config/config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_content, encoding="utf-8")
    print(f"Config salvo em: {config_path}")


if __name__ == "__main__":
    main()
