# 🌙 Luna — Assistente Pessoal de IA Local

Luna é uma assistente pessoal de IA que roda **100% localmente** no seu computador.
Ela ouve, entende, fala e **controla seu PC** — tudo sem depender da nuvem.

---

## ✨ Funcionalidades

### 🎤 Interação por Voz
- **Wake word**: Diga "Luna" para ativar (estilo Alexa)
- **Speech-to-Text**: Transcrição local via Faster-Whisper
- **Text-to-Speech**: Voz natural em PT-BR via Edge-TTS
- **Calibração adaptativa**: Calibra o microfone na primeira execução

### 🧠 Inteligência
- **LLM local ultra-rápido**: Qwen 2.5 1.5B via Ollama (~1s de resposta)
- **Respostas curtas**: Otimizado para respostas de 1-2 frases por voz
- **Memória de longo prazo**: ChromaDB com busca semântica
- **Contexto personalizado**: Luna conhece e lembra de você

### 🖥️ Controle Total do Computador
| Ação | Exemplo |
|------|---------|
| **Abrir sites** | "Luna, abre o Google" |
| **Abrir apps** | "Abre o Spotify" |
| **Pesquisar na web** | "Pesquisa sobre IA" |
| **Executar comandos** | "Roda 'ls -la' no terminal" |
| **Controlar volume** | "Aumenta o volume" |
| **Screenshots** | "Tira um screenshot" |
| **Clipboard** | "Copia isso para a clipboard" |
| **Brilho** | "Diminui o brilho" |
| **Timer** | "Timer de 5 minutos" |
| **Rede** | "Qual meu IP?" |
| **Energia** | "Desliga o computador" |
| **Processos** | "Mata o processo do Chrome" |
| **Teclado** | "Ctrl+C" |
| **Arquivos** | "Lê o arquivo ~/notas.txt" |

### 🔑 Atalhos Globais
| Atalho | Ação |
|--------|------|
| `Ctrl+Shift+L` | Abrir/fechar terminal |
| `Ctrl+Shift+Q` | Encerrar a Luna |

### 👁️ Visão (Opcional)
- Reconhecimento facial
- Análise de imagens

---

## 🚀 Instalação Rápida

### Linux
```bash
chmod +x install.sh
./install.sh
```

### Windows
```
install.bat
```

O instalador configura **tudo automaticamente**:
- Python + dependências
- Ollama + modelo qwen2.5:1.5b
- Perfil do usuário
- Auto-start no boot

---

## ▶️ Como Usar

```bash
# Linux
./start.sh

# Windows
start.bat

# Modo headless (sem terminal)
./start.sh --headless
```

---

## 📁 Estrutura

```
luna/
├── __main__.py          # Ponto de entrada
├── core/
│   ├── orchestrator.py  # Orquestrador principal
│   └── hotkeys.py       # Atalhos globais
├── brain/
│   └── brain.py         # LLM (Ollama)
├── voice/
│   ├── listener.py      # STT
│   ├── speaker.py       # TTS
│   ├── wake_word.py     # Wake word
│   ├── calibration.py   # Calibração
│   └── sounds.py        # Efeitos sonoros
├── actions/
│   └── action_executor.py  # Controle do PC (20+ ações)
├── memory/
│   └── memory_manager.py   # Memória (ChromaDB)
├── vision/
│   └── vision_module.py    # Reconhecimento facial
├── ui/
│   └── display.py       # Interface visual premium
└── utils/
    ├── config.py        # Configuração
    └── logger.py        # Logger
```

---

## ⚙️ Configuração

`config/config.yaml`:

```yaml
user:
  name: "Seu Nome"
  nickname: "Seu Apelido"

llm:
  model: "qwen2.5:1.5b"     # Ultra-rápido
  max_tokens: 200

voice:
  wake_word: "luna"
  tts_voice: "pt-BR-ThalitaMultilingualNeural"

actions:
  enabled: true
  allow_system_commands: true
```

---

## 🛠️ Requisitos

- **Python** 3.10+
- **Ollama** com `qwen2.5:1.5b`
- **Linux**: `xdotool`, `xclip`, `amixer`
- **Windows**: `pyautogui`

---

## 📄 Licença

MIT License

---

> 🌙 *"Luna, sempre ao seu lado."*
