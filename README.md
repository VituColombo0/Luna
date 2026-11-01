# Luna: Assistente Pessoal Local de Voz e Automação de Sistema

Assistente de inteligência artificial de operação 100% local, combinando reconhecimento de voz, processamento de linguagem natural por LLM embarcado e controle direto de tarefas no sistema operacional.

[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![LLM: Qwen 2.5](https://img.shields.io/badge/LLM-Qwen%202.5%201.5B%20(Ollama)-purple.svg)](https://ollama.com/)
[![STT: Faster-Whisper](https://img.shields.io/badge/STT-Faster--Whisper-teal.svg)](https://github.com/SYSTRAN/faster-whisper)
[![TTS: Edge-TTS](https://img.shields.io/badge/TTS-Edge--TTS%20PT--BR-darkgreen.svg)](https://github.com/rany2/edge-tts)
[![Memory: ChromaDB](https://img.shields.io/badge/Memory-ChromaDB%20Vector%20Store-orange.svg)](https://www.trychroma.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Visão Geral

O projeto **Luna** opera de maneira autônoma no computador do usuário, sem transmissão de áudio para servidores em nuvem. A assistente responde a comandos de voz disparados por palavra de ativação (*wake word*), interpreta a intenção do usuário por meio de um modelo de linguagem leve e aciona comandos de sistema ou sintetiza a resposta falada em tempo real.

```
                          [ Microfone Host ]
                                  │
                                  ▼
                        [ Wake Word Detection ]
                        Gatilho por voz: "Luna"
                                  │
                                  ▼
                     [ STT: Faster-Whisper Local ]
                      Conversão áudio -> texto
                                  │
                                  ▼
                      [ Orquestrador Central ]
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
[ Memória Semântica ]                             [ Inferência Local ]
   ChromaDB Vector                               Qwen 2.5 1.5B via Ollama
         │                                                 │
         └────────────────────────┬────────────────────────┘
                                  │
                                  ▼
                     [ Interpretador de Ações ]
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
[ Execução de Sistema ]                           [ TTS: Edge-TTS ]
Controle de janelas, volume,                    Resposta sintetizada em
processos, scripts e shell                      áudio natural (PT-BR)
```

---

## Módulos e Componentes

### 1. Áudio e Reconhecimento de Fala
- **Wake Word:** Monitoramento contínuo em baixa latência da palavra-chave "Luna".
- **Transcrição (STT):** Processamento local acelerado via **Faster-Whisper** com calibração automática de limiar de silêncio e ganho de microfone na primeira execução.
- **Síntese Vocal (TTS):** Geração de fala com prosódia natural em português brasileiro através da voz neural `pt-BR-ThalitaMultilingualNeural`.

### 2. Processamento Cognitivo e Memória
- **Modelo de Linguagem:** Utiliza o modelo **Qwen 2.5 1.5B** hospedado localmente via daemon do **Ollama**, priorizando baixa latência (tempo médio de resposta ~1 segundo) com respostas conversacionais concisas.
- **Memória de Longo Prazo:** Indexação de preferências e histórico de sessões em banco vetorial **ChromaDB**, recuperando contexto semântico relevante antes da geração do prompt.

### 3. Orquestração de Ações no Sistema
A camada de ações (`luna/actions/action_executor.py`) mapeia intenções em chamadas nativas de sistema operacional:

| Categoria | Ações Mapeadas | Exemplo de Comando Falado |
| :--- | :--- | :--- |
| **Navegação & Web** | Abertura de URLs, pesquisa no buscador padrão | *"Luna, pesquisa no Google sobre WebRTC"* |
| **Aplicativos** | Lançamento e encerramento de programas instalados | *"Abre o Spotify"* / *"Mata o processo do Chrome"* |
| **Controle de Sistema**| Volume, nível de brilho, captura de tela, energia | *"Aumenta o volume"* / *"Tira um screenshot"* |
| **Automação** | Manipulação de clipboard, temporizadores, status de rede | *"Copia isso"* / *"Timer de 10 minutos"* / *"Qual meu IP?"* |
| **Terminal & Shell** | Execução de comandos e scripts autorizados | *"Roda 'git status' no terminal"* |

### 4. Atalhos Globais de Teclado
- `Ctrl+Shift+L`: Alterna visibilidade do terminal interativo da assistente.
- `Ctrl+Shift+Q`: Encerra graciosamente o processo e descarrega modelos da memória.

---

## Pré-requisitos

- **Python 3.10** ou superior
- **Ollama** instalado com o modelo `qwen2.5:1.5b` baixado (`ollama pull qwen2.5:1.5b`)
- **Dependências de Sistema:**
  - **Linux:** `xdotool`, `xclip`, `alsa-utils` (`amixer`)
  - **Windows:** API Win32 e suporte ao `pyautogui`

---

## Instalação

### Instalação Automatizada

**No Linux:**
```bash
git clone https://github.com/VituColombo0/Luna.git
cd Luna

chmod +x install.sh
./install.sh
```

**No Windows:**
```cmd
git clone https://github.com/VituColombo0/Luna.git
cd Luna
install.bat
```

O assistente de instalação configura o ambiente virtual, instala os pacotes do `requirements.txt`, provisiona o modelo no Ollama e cria o arquivo de perfil inicial.

---

## Como Iniciar

```bash
# Inicialização padrão com interface de console
./start.sh          # Linux
start.bat           # Windows

# Inicialização em modo headless (segundo plano, sem terminal visível)
./start.sh --headless
```

---

## Configuração (`config/config.yaml`)

Parâmetros de usuário e execução podem ser personalizados:

```yaml
user:
  name: "Victor"
  nickname: "Vitu"

llm:
  model: "qwen2.5:1.5b"
  temperature: 0.3
  max_tokens: 150

voice:
  wake_word: "luna"
  tts_voice: "pt-BR-ThalitaMultilingualNeural"
  stt_model_size: "base"

actions:
  enabled: true
  allow_system_commands: true
```

---

## Testes e Calibração de Hardware

O repositório inclui utilitários isolados para testar periféricos antes de iniciar a assistente completa:

```bash
# Diagnóstico de captura e nível de sinal do microfone
python test_mic.py

# Validação da precisão da palavra de ativação
python test_wake_word.py

# Teste de tempo de resposta e acurácia do Faster-Whisper
python test_whisper.py
```

---

## Estrutura do Projeto

```text
Luna/
├── luna/
│   ├── __main__.py          # Ponto de entrada da aplicação
│   ├── core/                # Orquestrador central e atalhos globais
│   ├── brain/               # Cliente de integração com Ollama
│   ├── voice/               # Módulos de captura, STT, TTS e wake word
│   ├── actions/             # Handlers de automação e comandos do SO
│   ├── memory/              # Gerenciador de vetores e contexto ChromaDB
│   ├── vision/              # Módulo experimental de visão computacional
│   ├── ui/                  # Interface visual e feedback de status
│   └── utils/               # Configuração e logging
├── config/                  # Definições em YAML
├── test_mic.py              # Script de teste de microfone
├── test_wake_word.py        # Script de validação da wake word
├── test_whisper.py          # Script de validação de transcrição
├── install.sh / install.bat # Scripts de instalação
└── README.md                # Documentação técnica
```

---

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para mais detalhes.
