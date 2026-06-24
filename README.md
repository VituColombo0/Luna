# 🧠 Alfred — Assistente Pessoal de IA Local

Um assistente virtual estilo Jarvis que roda 100% localmente no seu PC.

## Funcionalidades

- 🗣️ **Conversação por voz** — Fale naturalmente e receba respostas faladas
- 👁️ **Visão computacional** — Reconhece você pela câmera e entende imagens
- 📚 **Memória de longo prazo** — Lembra de conversas passadas usando ChromaDB
- 💻 **Autonomia no PC** — Abre arquivos, pastas e executa comandos
- 🔒 **100% Local** — Nenhum dado sai do seu computador

## Requisitos

- Python 3.10+
- [Ollama](https://ollama.ai) instalado e rodando
- Microfone e câmera (opcional para visão)

## Instalação

```bash
# 1. Clone o repositório
git clone <repo-url> Alfred
cd Alfred

# 2. Crie o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Baixe o modelo no Ollama
ollama pull phi3

# 5. Configure seu perfil
cp config/config.example.yaml config/config.yaml
# Edite config.yaml com suas informações

# 6. Rode o Alfred
python -m alfred
```

## Estrutura do Projeto

```
Alfred/
├── alfred/                 # Pacote principal
│   ├── __init__.py
│   ├── __main__.py         # Ponto de entrada
│   ├── core/               # Orquestrador principal
│   ├── brain/              # Integração com LLM (Ollama)
│   ├── voice/              # STT e TTS
│   ├── vision/             # Câmera e reconhecimento
│   ├── memory/             # Memória de longo prazo
│   ├── actions/            # Controle do computador
│   └── utils/              # Utilitários
├── config/                 # Configurações
├── data/                   # Dados persistentes (memória, faces)
├── requirements.txt
└── README.md
```
