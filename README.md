# 🌙 Luna — Assistente Pessoal de IA Local

Luna é uma assistente pessoal de IA que roda **100% localmente** no seu computador.
Ela ouve, entende, fala e executa ações no seu PC — tudo sem depender da nuvem.

---

## ✨ Funcionalidades

### 🎤 Interação por Voz
- **Wake word**: Diga "Luna" para ativar (estilo Alexa)
- **Speech-to-Text**: Transcrição local via Faster-Whisper com InputStream contínuo
- **Text-to-Speech**: Voz natural em PT-BR via Edge-TTS com **cache de áudio**
- **Calibração adaptativa**: Calibra o microfone na primeira execução
- **Detecção RMS**: Imune a ruídos, detecta fala real

### 🧠 Inteligência
- **LLM local**: Integração com Ollama (Gemma 3 4B, Llama 3.1, etc.)
- **Respostas rápidas**: Otimizado para respostas curtas por voz (2-3 frases)
- **Memória de longo prazo**: ChromaDB com busca semântica
- **Contexto personalizado**: Luna conhece e lembra de você

### 🖥️ Controle Total do Computador
- **Aplicativos**: Abrir, fechar e gerenciar apps
- **Navegador**: Pesquisar na web, abrir URLs
- **Arquivos**: Buscar, ler e criar arquivos
- **Terminal**: Executar qualquer comando do sistema
- **Volume**: Aumentar, diminuir, mutar
- **Brilho**: Controlar brilho da tela
- **Teclado**: Digitar texto e pressionar atalhos
- **Clipboard**: Ler e escrever na área de transferência
- **Screenshots**: Capturar tela inteira ou janela ativa
- **Rede**: Ver IP, status da conexão, ligar/desligar Wi-Fi
- **Energia**: Desligar, reiniciar, suspender, bloquear
- **Timer**: Temporizadores com notificação
- **Processos**: Listar e encerrar processos

### 🔑 Atalhos de Teclado Globais
| Atalho | Ação |
|--------|------|
| `Ctrl+Shift+L` | Abrir/fechar terminal da Luna |
| `Ctrl+Shift+Q` | Encerrar a Luna |

### 👁️ Visão (Opcional)
- Reconhecimento facial
- Análise de imagens com modelos de visão

### 🔇 Modo Headless
- Roda em background sem terminal visível
- Perfeito para uso no dia a dia

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

---

## ▶️ Como Usar

### Modo normal (com terminal)
```bash
./start.sh          # Linux
start.bat           # Windows
```

### Modo headless (sem terminal)
```bash
./start.sh --headless       # Linux
start.bat --headless        # Windows
```

### Direto com Python
```bash
python3 -m luna                 # Normal
python3 -m luna --headless      # Background
```

---

## 📁 Estrutura do Projeto

```
luna/
├── __init__.py          # Package metadata
├── __main__.py          # Ponto de entrada
├── core/
│   ├── orchestrator.py  # Orquestrador principal
│   └── hotkeys.py       # Atalhos de teclado globais
├── brain/
│   └── brain.py         # Integração LLM (Ollama)
├── voice/
│   ├── listener.py      # Speech-to-Text (InputStream contínuo)
│   ├── speaker.py       # Text-to-Speech (com cache)
│   ├── wake_word.py     # Detecção de wake word (RMS)
│   ├── calibration.py   # Calibração de voz adaptativa
│   └── sounds.py        # Efeitos sonoros programáticos
├── actions/
│   └── action_executor.py  # Controle do computador (20+ ações)
├── memory/
│   └── memory_manager.py   # Memória de longo prazo (ChromaDB)
├── vision/
│   └── vision_module.py    # Reconhecimento facial
├── ui/
│   └── display.py       # Interface visual animada
└── utils/
    ├── config.py        # Carregamento de config
    └── logger.py        # Logger com Rich
```

---

## ⚙️ Configuração

Edite `config/config.yaml` com suas informações:

```yaml
user:
  name: "Seu Nome"
  nickname: "Seu Apelido"

llm:
  model: "gemma3:4b"       # Modelo rápido e leve
  max_tokens: 256          # Respostas curtas para voz

voice:
  wake_word: "luna"
  tts_voice: "pt-BR-ThalitaMultilingualNeural"
  tts_rate: "+15%"         # Velocidade da fala

actions:
  enabled: true
  allow_system_commands: true
```

---

## 🛠️ Requisitos

- **Python** 3.10+
- **Ollama** com um modelo instalado (`ollama pull gemma3:4b`)
- **Linux**: `xdotool`, `xclip`, `amixer` (para controle total)
- **Windows**: `pyautogui` (instalado automaticamente)
- **pynput**: Para atalhos de teclado globais

---

## 📝 Exemplos de Comandos

| Comando | O que a Luna faz |
|---------|-------------------|
| "Luna, abre o Firefox" | Abre o Firefox |
| "Pesquisa sobre IA no Google" | Abre pesquisa no navegador |
| "Aumenta o volume" | Volume +10% |
| "Tira um screenshot" | Captura a tela |
| "Coloca um timer de 5 minutos" | Timer com notificação |
| "Qual meu IP?" | Mostra IP local |
| "Desliga o computador" | Shutdown do sistema |
| "Ctrl+C" | Simula atalho de teclado |
| "Lê o arquivo ~/notas.txt" | Lê conteúdo do arquivo |
| "Roda 'ls -la' no terminal" | Executa comando |

---

## 📄 Licença

MIT License — use como quiser.

---

> 🌙 *"Luna, sempre ao seu lado."*
