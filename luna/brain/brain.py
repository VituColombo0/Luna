"""
Brain — Módulo de integração com o modelo de linguagem via Ollama.

Este módulo gerencia toda a comunicação com o LLM, incluindo:
- Chat conversacional com histórico de contexto
- Análise de imagens via modelos de visão (moondream/llava)
- System prompt personalizado com informações do usuário
- Detecção de intenção de ações (tool calling manual)
- Integração com visão (câmera) e memória de longo prazo
"""

import json
import logging
import re
from datetime import datetime

import ollama


# Ações que a Luna pode executar no computador
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
    {
        "name": "run_command",
        "description": "Executar um comando no terminal/shell do sistema operacional (ex: ls, mkdir, pip install, etc.)",
        "parameters": {"command": "Comando a executar no terminal"},
    },
    {
        "name": "open_application",
        "description": "Abrir um aplicativo pelo nome (ex: firefox, code, nautilus, terminal, spotify, discord)",
        "parameters": {"app_name": "Nome do aplicativo a abrir"},
    },
    {
        "name": "control_volume",
        "description": "Controlar o volume do sistema (aumentar, diminuir, mutar/desmutar)",
        "parameters": {"action": "up, down, mute, unmute ou um número de 0-100"},
    },
    {
        "name": "list_processes",
        "description": "Listar processos em execução ou matar um processo pelo nome",
        "parameters": {"action": "list ou kill", "name": "nome do processo (para kill)"},
    },
    {
        "name": "take_screenshot",
        "description": "Tirar uma captura de tela (screenshot) do computador",
        "parameters": {"region": "Opcional: 'full' para tela inteira ou 'active' para janela ativa"},
    },
    {
        "name": "clipboard",
        "description": "Ler ou escrever na área de transferência (clipboard)",
        "parameters": {"action": "read ou write", "text": "Texto para copiar (quando action=write)"},
    },
    {
        "name": "control_brightness",
        "description": "Controlar o brilho da tela (aumentar, diminuir ou definir valor)",
        "parameters": {"action": "up, down ou um número de 0-100"},
    },
    {
        "name": "system_power",
        "description": "Desligar, reiniciar ou suspender o computador",
        "parameters": {"action": "shutdown, restart, suspend, lock"},
    },
    {
        "name": "manage_network",
        "description": "Gerenciar rede — ver IP, status da conexão",
        "parameters": {"action": "status, wifi_on, wifi_off, ip"},
    },
    {
        "name": "type_text",
        "description": "Digitar um texto no campo ativo (simula teclado)",
        "parameters": {"text": "Texto a digitar", "press_enter": "true/false"},
    },
    {
        "name": "hotkey",
        "description": "Pressionar atalho de teclado. Ex: ctrl+c, alt+tab, ctrl+shift+t",
        "parameters": {"keys": "Combinação separada por +"},
    },
    {
        "name": "set_timer",
        "description": "Configurar temporizador (a Luna avisa quando o tempo acabar)",
        "parameters": {"seconds": "Tempo em segundos", "message": "Mensagem ao terminar"},
    },
    {
        "name": "read_file_content",
        "description": "Ler o conteúdo de um arquivo de texto",
        "parameters": {"path": "Caminho do arquivo"},
    },
    {
        "name": "write_file_content",
        "description": "Escrever/criar um arquivo de texto",
        "parameters": {"path": "Caminho do arquivo", "content": "Conteúdo a escrever"},
    },
]


class Brain:
    """
    Cérebro do Luna — gerencia a comunicação com o LLM local via Ollama.
    
    Otimizado para respostas rápidas com streaming e num_predict limitado.
    Integra visão (câmera + membros) e memória de longo prazo.
    """

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("llm", {})
        self.user_config = config.get("user", {})
        self.logger = logger

        self.model = self.config.get("model", "qwen2.5:1.5b")
        self.vision_model = self.config.get("vision_model", "moondream")
        self.temperature = self.config.get("temperature", 0.7)
        self.host = self.config.get("ollama_host", "http://localhost:11434")
        self.max_tokens = self.config.get("max_tokens", 200)

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
        Constrói o system prompt personalizado com informações do usuário,
        memórias relevantes, contexto de visão e info de membros.

        Args:
            memory_context: Contexto combinado (memórias + visão + membros).

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

        prompt = (
            f'Voce eh Luna, assistente pessoal de IA com controle TOTAL do computador e VISAO por camera.\n'
            f'\n'
            f'DATA/HORA: {now}\n'
            f'DONO: {user_name} (chame de "{nickname}")\n'
            f'BIO: {bio}\n'
            f'\n'
            f'== CONTEXTO ==\n'
            f'{memory_context if memory_context else "(sem contexto adicional)"}\n'
            f'\n'
            f'== VISAO ==\n'
            f'Voce tem camera e pode identificar pessoas pelo rosto. '
            f'Se a mensagem inclui "PESSOA IDENTIFICADA PELA CAMERA", use o nome para personalizar a resposta e cumprimente pelo nome. '
            f'Se perguntarem "quem sou eu" ou "quem esta aqui", responda com base na identificacao visual. '
            f'Se receber "DESCRICAO DA CAMERA", use para responder sobre o que esta vendo.\n'
            f'\n'
            f'== MEMORIA ==\n'
            f'Voce tem memoria PERSISTENTE em Obsidian Vault. O contexto acima pode conter:\n'
            f'- PREFERENCIAS DO USUARIO: gostos, habitos, configs\n'
            f'- FATOS IMPORTANTES: informacoes que devem ser lembradas sempre\n'
            f'- CONVERSAS RECENTES: dialogos dos ultimos dias\n'
            f'- MEMORIAS RELACIONADAS: trechos de conversas antigas relevantes\n'
            f'Use TUDO isso para personalizar. Se algo esta no contexto, voce LEMBRA. Mencione proativamente.\n'
            f'Nunca diga "nao me lembro" se a informacao esta no contexto.\n'
            f'\n'
            f'== ACOES NO PC ==\n'
            f'Para executar algo no computador, SEMPRE inclua um bloco JSON exatamente assim:\n'
            f'\n'
            f'EXEMPLO 1 - Abrir arquivo ou pasta:\n'
            f'```action\n'
            f'{{"action": "open_file", "params": {{"path": "~/Documents/relatorio.pdf"}}}}\n'
            f'```\n'
            f'\n'
            f'EXEMPLO 2 - Pesquisar no Google:\n'
            f'```action\n'
            f'{{"action": "search_web", "params": {{"query": "clima em Sao Paulo"}}}}\n'
            f'```\n'
            f'\n'
            f'EXEMPLO 3 - Abrir um site:\n'
            f'```action\n'
            f'{{"action": "open_browser", "params": {{"url": "https://google.com"}}}}\n'
            f'```\n'
            f'\n'
            f'EXEMPLO 4 - Abrir aplicativo:\n'
            f'```action\n'
            f'{{"action": "open_application", "params": {{"app_name": "firefox"}}}}\n'
            f'```\n'
            f'\n'
            f'TODAS AS ACOES DISPONIVEIS:\n'
            f'{actions_desc}\n'
            f'\n'
            f'== REGRAS ==\n'
            f'1. RESPOSTAS CURTAS: 1-2 frases. Voce eh assistente de VOZ.\n'
            f'2. Portugues do Brasil, natural e direto.\n'
            f'3. SEMPRE EXECUTE acoes do PC com bloco ```action```. FACA, nao sugira.\n'
            f'4. NUNCA escreva codigo Python. Use APENAS blocos ```action``` com JSON.\n'
            f'5. Use memorias para personalizar. Se lembra, mencione.\n'
            f'6. Se identificou alguem pela camera, trate pelo nome.\n'
            f'7. NUNCA listas longas.\n'
            f'8. Para abrir sites como Google, YouTube, etc, use open_browser com a URL completa.\n'
            f'9. Para pesquisar algo, use search_web. Para abrir um site direto, use open_browser.\n'
        )
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

        Usa streaming para latência mínima e limita tokens para
        respostas rápidas e concisas.

        Args:
            user_message: A mensagem de texto do usuário.
            memory_context: Contexto combinado (memórias + visão + membros).
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
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                },
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
