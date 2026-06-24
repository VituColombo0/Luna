# 🧠 Alfred — Assistente Pessoal de IA Local

Um assistente virtual estilo **Alexa/Jarvis** que roda **100% localmente** no seu PC.
Diga **"Alfred"** e ele responde — sem depender de internet, sem enviar dados pra ninguém.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/Ollama-Local%20LLM-blueviolet?logo=ollama" />
  <img src="https://img.shields.io/badge/Whisper-STT-green" />
  <img src="https://img.shields.io/badge/100%25-Offline-success" />
</p>

---

## ✨ Funcionalidades

| Feature | Descrição |
|---------|-----------|
| 🎤 **Wake Word** | Diga "Alfred" e ele ativa — igual uma Alexa |
| 🗣️ **Voz Natural** | Fale naturalmente e receba respostas por voz |
| 🧠 **IA Local** | Usa Ollama (phi3, llama3, mistral) — 100% offline |
| 📚 **Memória** | Lembra de conversas passadas via ChromaDB |
| 👁️ **Visão** | Reconhece seu rosto pela câmera (opcional) |
| 💻 **Ações no PC** | Abre arquivos, pesquisa na web, info do sistema |
| 🔒 **Privacidade** | Nenhum dado sai do seu computador |
| 🔔 **Feedback Sonoro** | Beeps de confirmação ao ativar/desativar |
| 🚀 **Auto-Start** | Inicia junto com o computador |

---

## 🚀 Instalação Rápida (1 comando)

### Linux / macOS

```bash
git clone https://github.com/VituColombo0/Alfred.git
cd Alfred
bash install.sh
```

### Windows

```powershell
git clone https://github.com/VituColombo0/Alfred.git
cd Alfred
install.bat
```

O instalador faz **tudo automaticamente**:
- ✅ Instala dependências do sistema
- ✅ Cria ambiente virtual Python
- ✅ Instala pacotes necessários
- ✅ Instala e configura o Ollama
- ✅ Baixa o modelo de IA (interativo)
- ✅ Gera configuração personalizada
- ✅ Configura auto-start no boot

---

## 📖 Instalação Manual (passo a passo)

Se preferir instalar manualmente:

```bash
# 1. Clone o repositório
git clone https://github.com/VituColombo0/Alfred.git
cd Alfred

# 2. Crie o ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instale as dependências
pip install -r requirements-core.txt         # Essencial (voz + LLM)
pip install -r requirements-memory.txt       # Opcional: memória
pip install -r requirements-vision.txt       # Opcional: visão
# OU tudo de uma vez:
pip install -r requirements-full.txt

# 4. Instale o Ollama
curl -fsSL https://ollama.ai/install.sh | sh  # Linux
# Windows: baixe em https://ollama.ai/download

# 5. Baixe o modelo
ollama pull phi3

# 6. Configure
cp config/config.example.yaml config/config.yaml
# Edite config.yaml com suas informações

# 7. Rode!
python -m alfred
```

---

## 🎤 Como Usar

### Modo Voz (padrão — estilo Alexa)

1. O Alfred inicia e fica ouvindo em background
2. Diga **"Alfred"** — você ouve um beep de confirmação 🔔
3. Fale seu comando: *"Alfred, que horas são?"*
4. Ele processa e responde por voz
5. Volta a ouvir automaticamente

### Modo Texto (fallback)

Se o sistema de voz não estiver disponível, o Alfred opera por texto no terminal.
Você também pode alternar digitando `/voz` ou `/texto`.

### Comandos Especiais

| Comando | Ação |
|---------|------|
| `/sair` | Desliga o Alfred |
| `/limpar` | Limpa histórico de conversa |
| `/voz` | Muda para modo voz |
| `/texto` | Muda para modo texto |
| `/status` | Mostra status dos módulos |

---

## ⚙️ Configuração

Edite `config/config.yaml` para personalizar:

```yaml
user:
  name: "Seu Nome"
  nickname: "Apelido"

llm:
  model: "phi3"          # phi3, llama3.2, mistral, gemma2

voice:
  wake_word: "alfred"    # Palavra de ativação
  tts_voice: "pt-BR-AntonioNeural"  # ou FranciscaNeural
```

---

## 📁 Estrutura do Projeto

```
Alfred/
├── alfred/                 # Pacote principal
│   ├── __init__.py
│   ├── __main__.py         # Ponto de entrada
│   ├── core/
│   │   └── orchestrator.py # Coração do Alfred (loop principal)
│   ├── brain/
│   │   └── brain.py        # Integração com LLM (Ollama)
│   ├── voice/
│   │   ├── listener.py     # Speech-to-Text (Faster-Whisper)
│   │   ├── speaker.py      # Text-to-Speech (Edge-TTS/Piper)
│   │   ├── wake_word.py    # Detecção de wake word contínua
│   │   └── sounds.py       # Sons de feedback (beeps)
│   ├── vision/
│   │   └── vision_module.py # Câmera e reconhecimento facial
│   ├── memory/
│   │   └── memory_manager.py # Memória de longo prazo (ChromaDB)
│   ├── actions/
│   │   └── action_executor.py # Controle do computador
│   ├── ui/
│   │   └── display.py      # Interface visual animada no terminal
│   └── utils/
│       ├── config.py        # Carregamento de configuração
│       └── logger.py        # Sistema de logs
├── config/
│   ├── config.example.yaml  # Exemplo de configuração
│   └── config.yaml          # Sua configuração (gitignored)
├── data/
│   ├── faces/               # Fotos para reconhecimento facial
│   └── memory/              # Banco de dados de memória
├── install.sh               # Instalador Linux (1 comando)
├── install.bat              # Instalador Windows (1 comando)
├── start.sh                 # Iniciar no Linux
├── start.bat                # Iniciar no Windows
├── requirements-core.txt    # Dependências essenciais
├── requirements-memory.txt  # Dependências de memória (opcional)
├── requirements-vision.txt  # Dependências de visão (opcional)
├── requirements-full.txt    # Todas as dependências
└── README.md
```

---

## 🔧 Requisitos Mínimos

| Requisito | Mínimo | Recomendado |
|-----------|--------|-------------|
| **Python** | 3.10 | 3.11+ |
| **RAM** | 4 GB | 8 GB+ |
| **Disco** | 5 GB | 10 GB |
| **Microfone** | Qualquer | USB/headset |
| **GPU** | Não necessária | Ajuda no LLM |

---

## 📝 Licença

MIT — use como quiser.
