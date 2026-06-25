"""
Brain — Módulo de integração com o modelo de linguagem via Ollama.

Este módulo gerencia toda a comunicação com o LLM, incluindo:
- Chat conversacional com histórico de contexto
- Análise de imagens via modelos de visão (moondream/llava)
- System prompt personalizado com informações do usuário
- Detecção de intenção de ações (tool calling manual)
"""

import json
import logging
from datetime import datetime

import ollama


# Ações que o Alfred pode executar no computador
AVAILABLE_ACTIONS = [
    {
        "name": "open_file",
        "description": "Abrir um arquivo ou pasta no computador",
        "parameters": {"path": "Caminho do arquivo ou pasta"},
    },
    {
        "name": "open_browser",
        "description": "Abrir uma URL no navegador",
        "parameters": {"url": "URL para abrir"},
    },
    {
        "name": "search_web",
        "description": "Pesquisar algo na internet",
        "parameters": {"query": "Termo de pesquisa"},
    },
    {
        "name": "search_files",
        "description": "Procurar um arquivo no computador",
        "parameters": {"filename": "Nome ou parte do nome do arquivo"},
    },
    {
        "name": "system_info",
        "description": "Obter informações do sistema (CPU, RAM, disco, etc.)",
        "parameters": {},
    },
    {
        "name": "take_note",
        "description": "Anotar algo importante para lembrar depois",
        "parameters": {"content": "Conteúdo da anotação"},
    },
]


class Brain:
    """
    Cérebro do Alfred — gerencia a comunicação com o LLM local via Ollama.
    """

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("llm", {})
        self.user_config = config.get("user", {})
        self.logger = logger

        self.model = self.config.get("model", "llama3.1")
        self.vision_model = self.config.get("vision_model", "moondream")
        self.temperature = self.config.get("temperature", 0.7)
        self.host = self.config.get("ollama_host", "http://localhost:11434")

        # Histórico de mensagens para manter contexto na conversa
        self.conversation_history: list[dict] = []
        self.max_history = 20  # Manter últimas N mensagens

        # Configurar cliente Ollama
        self.client = ollama.Client(host=self.host)

        self.logger.info(
            f"Brain inicializado — modelo: [bold cyan]{self.model}[/], "
            f"visão: [bold cyan]{self.vision_model}[/]"
        )

    def _build_system_prompt(self, memory_context: str = "") -> str:
        """
        Constrói o system prompt personalizado com informações do usuário
        e memórias relevantes.

        Args:
            memory_context: Contexto adicional vindo da memória de longo prazo.

        Returns:
            System prompt formatado.
        """
        user_name = self.user_config.get("name", "Usuário")
        nickname = self.user_config.get("nickname", user_name)
        bio = self.user_config.get("bio", "")

        now = datetime.now().strftime("%A, %d de %B de %Y, %H:%M")

        actions_desc = "\n".join(
            f'  - "{a["name"]}": {a["description"]}' for a in AVAILABLE_ACTIONS
        )

        prompt = f"""Você é o Alfred, um assistente pessoal de IA inteligente, prestativo e com personalidade.
Você pertence exclusivamente ao {user_name} (pode chamá-lo de "{nickname}").

SOBRE SEU DONO:
{bio}

DATA E HORA ATUAL: {now}

MEMÓRIAS RELEVANTES:
{memory_context if memory_context else "(Nenhuma memória relevante para este contexto)"}

AÇÕES DISPONÍVEIS:
Você pode executar ações no computador do {nickname}. Quando ele pedir para fazer algo no PC, \
responda normalmente E inclua um bloco JSON de ação no final da sua resposta, no formato:
```action
{{"action": "<nome_da_acao>", "params": {{<parametros>}}}}
```

Ações disponíveis:
{actions_desc}

REGRAS:
1. Seja natural, amigável e direto. Nada de respostas genéricas.
2. Fale em português do Brasil.
3. Use as memórias para personalizar suas respostas — demonstre que lembra de coisas passadas.
4. Quando executar uma ação, confirme o que vai fazer antes ou depois.
5. Se não souber algo, diga honestamente.
6. Mantenha respostas concisas — você está falando por voz, então respostas longas ficam cansativas.
"""
        return prompt

    def check_connection(self) -> bool:
        """
        Verifica se o Ollama está rodando e o modelo está disponível.

        Returns:
            True se a conexão e o modelo estão OK.
        """
        try:
            models = self.client.list()
            available = [m.model for m in models.models]
            self.logger.info(f"Modelos disponíveis no Ollama: {available}")

            # Verificar se o modelo configurado está disponível
            # Ollama retorna nomes como "phi3:latest", precisamos checar o prefixo
            model_found = any(
                m.startswith(self.model) for m in available
            )
            if not model_found:
                self.logger.warning(
                    f"Modelo [bold red]{self.model}[/] não encontrado. "
                    f"Execute: [cyan]ollama pull {self.model}[/]"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(
                f"Não foi possível conectar ao Ollama em {self.host}: {e}\n"
                "Certifique-se de que o Ollama está rodando: [cyan]ollama serve[/]"
            )
            return False

    def think(
        self,
        user_message: str,
        memory_context: str = "",
        image_path: str | None = None,
    ) -> dict:
        """
        Processa uma mensagem do usuário e retorna a resposta do LLM.

        Args:
            user_message: A mensagem de texto do usuário.
            memory_context: Contexto de memórias relevantes (do ChromaDB).
            image_path: Caminho opcional para uma imagem (ativa modelo de visão).

        Returns:
            Dicionário com:
                - "text": A resposta em texto do LLM.
                - "action": Dicionário da ação a executar (ou None).
        """
        system_prompt = self._build_system_prompt(memory_context)

        # Montar mensagens
        messages = [{"role": "system", "content": system_prompt}]

        # Adicionar histórico recente
        messages.extend(self.conversation_history[-self.max_history :])

        # Mensagem atual do usuário
        current_msg = {"role": "user", "content": user_message}
        if image_path:
            current_msg["images"] = [image_path]

        messages.append(current_msg)

        # Escolher modelo (visão se tiver imagem)
        model = self.vision_model if image_path else self.model

        try:
            self.logger.info(f"Pensando com [cyan]{model}[/]...")

            response = self.client.chat(
                model=model,
                messages=messages,
                options={"temperature": self.temperature},
            )

            reply_text = response.message.content

            # Salvar no histórico
            self.conversation_history.append(current_msg)
            self.conversation_history.append(
                {"role": "assistant", "content": reply_text}
            )

            # Detectar ação no response
            action = self._extract_action(reply_text)

            # Limpar o bloco de ação do texto de resposta
            clean_text = self._clean_action_block(reply_text)

            return {"text": clean_text, "action": action}

        except Exception as e:
            self.logger.error(f"Erro ao comunicar com o Ollama: {e}")
            return {
                "text": "Desculpa, tive um problema ao processar sua mensagem. Pode repetir?",
                "action": None,
            }

    def _extract_action(self, text: str) -> dict | None:
        """
        Extrai um bloco de ação JSON da resposta do LLM.

        Args:
            text: Texto completo da resposta.

        Returns:
            Dicionário da ação ou None se não houver ação.
        """
        import re
        try:
            # Procurar bloco ```action ... ``` ou ```json ... ```
            action_json = None
            if "```action" in text:
                start = text.index("```action") + len("```action")
                end = text.index("```", start)
                action_json = text[start:end].strip()
            elif "```json" in text:
                start = text.index("```json") + len("```json")
                end = text.index("```", start)
                action_json = text[start:end].strip()

            if action_json:
                # Arrumar possíveis single-backslashes nos caminhos gerados pelo LLM
                # Exemplo: C:\Documents -> C:\\Documents (se não estiver escapado)
                action_json = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', action_json)
                action = json.loads(action_json)

                # Validar que a ação existe
                valid_names = [a["name"] for a in AVAILABLE_ACTIONS]
                if action.get("action") in valid_names:
                    return action
                else:
                    self.logger.warning(
                        f"Ação desconhecida ignorada: {action.get('action')}"
                    )
        except (ValueError, json.JSONDecodeError) as e:
            self.logger.debug(f"Nenhuma ação detectada na resposta: {e}")

        return None

    def _clean_action_block(self, text: str) -> str:
        """
        Remove o bloco ```action``` do texto para que a resposta
        falada seja limpa.

        Args:
            text: Texto completo da resposta.

        Returns:
            Texto sem o bloco de ação.
        """
        try:
            if "```action" in text:
                start = text.index("```action")
                end = text.index("```", start + 9) + 3
                text = text[:start].strip() + text[end:].strip()
            elif "```json" in text:
                start = text.index("```json")
                end = text.index("```", start + 7) + 3
                text = text[:start].strip() + text[end:].strip()
        except ValueError:
            pass

        return text.strip()

    def clear_history(self):
        """Limpa o histórico de conversação."""
        self.conversation_history.clear()
        self.logger.info("Histórico de conversa limpo.")
