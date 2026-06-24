"""
ActionExecutor — Executa ações no computador a pedido do Alfred.

Suporta:
- Abrir arquivos e pastas
- Abrir URLs no navegador
- Pesquisar na web
- Buscar arquivos locais
- Obter informações do sistema
"""

import logging
import os
import platform
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ActionExecutor:
    """
    Executor de ações do Alfred no sistema operacional.
    """

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("actions", {})
        self.logger = logger

        self.enabled = self.config.get("enabled", True)
        self.allowed_paths = self.config.get("allowed_paths", [])
        self.allow_browser = self.config.get("allow_browser", True)
        self.allow_system_commands = self.config.get("allow_system_commands", False)

        self.system = platform.system()  # Linux, Windows, Darwin

        if self.enabled:
            self.logger.info(
                f"Actions ativo — OS: [cyan]{self.system}[/], "
                f"paths permitidos: {len(self.allowed_paths)}"
            )

    def execute(self, action: dict) -> str | None:
        """
        Executa uma ação recebida do LLM.

        Args:
            action: Dicionário com "action" (str) e "params" (dict).

        Returns:
            Mensagem de resultado ou None.
        """
        if not self.enabled:
            return "Ações desativadas na configuração."

        action_name = action.get("action", "")
        params = action.get("params", {})

        handlers = {
            "open_file": self._open_file,
            "open_browser": self._open_browser,
            "search_web": self._search_web,
            "search_files": self._search_files,
            "system_info": self._system_info,
            "take_note": self._take_note,
        }

        handler = handlers.get(action_name)
        if handler:
            self.logger.info(f"Executando ação: [bold cyan]{action_name}[/]")
            return handler(params)
        else:
            self.logger.warning(f"Ação desconhecida: {action_name}")
            return None

    def _open_file(self, params: dict) -> str:
        """Abre um arquivo ou pasta usando o programa padrão do sistema."""
        path = params.get("path", "")
        if not path:
            return "Caminho não especificado."

        # Expandir ~ e variáveis de ambiente
        path = os.path.expanduser(os.path.expandvars(path))
        target = Path(path)

        # Verificar se o caminho existe
        if not target.exists():
            # Tentar procurar em pastas permitidas
            found = self._find_in_allowed_paths(target.name)
            if found:
                target = found
            else:
                return f"Arquivo não encontrado: {path}"

        # Verificar permissão de acesso
        if not self._is_path_allowed(str(target)):
            return f"Acesso negado ao caminho: {path}"

        try:
            if self.system == "Linux":
                subprocess.Popen(["xdg-open", str(target)])
            elif self.system == "Darwin":
                subprocess.Popen(["open", str(target)])
            elif self.system == "Windows":
                os.startfile(str(target))

            return f"Abrindo: {target}"

        except Exception as e:
            return f"Erro ao abrir: {e}"

    def _open_browser(self, params: dict) -> str:
        """Abre uma URL no navegador padrão."""
        url = params.get("url", "")
        if not url:
            return "URL não especificada."

        if not self.allow_browser:
            return "Navegador desativado na configuração."

        # Garantir que tem protocolo
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            webbrowser.open(url)
            return f"Abrindo no navegador: {url}"
        except Exception as e:
            return f"Erro ao abrir navegador: {e}"

    def _search_web(self, params: dict) -> str:
        """Pesquisa algo no Google via navegador."""
        query = params.get("query", "")
        if not query:
            return "Termo de pesquisa não especificado."

        if not self.allow_browser:
            return "Navegador desativado na configuração."

        url = f"https://www.google.com/search?q={quote_plus(query)}"
        try:
            webbrowser.open(url)
            return f"Pesquisando: {query}"
        except Exception as e:
            return f"Erro na pesquisa: {e}"

    def _search_files(self, params: dict) -> str:
        """Procura arquivos pelo nome nas pastas permitidas."""
        filename = params.get("filename", "")
        if not filename:
            return "Nome do arquivo não especificado."

        results = []
        for allowed in self.allowed_paths:
            allowed_path = Path(allowed)
            if not allowed_path.exists():
                continue

            try:
                for match in allowed_path.rglob(f"*{filename}*"):
                    results.append(str(match))
                    if len(results) >= 10:
                        break
            except PermissionError:
                continue

            if len(results) >= 10:
                break

        if results:
            file_list = "\n".join(f"  • {r}" for r in results)
            return f"Encontrados {len(results)} arquivo(s):\n{file_list}"
        else:
            return f"Nenhum arquivo encontrado com '{filename}'."

    def _system_info(self, params: dict) -> str:
        """Retorna informações do sistema."""
        if not PSUTIL_AVAILABLE:
            return "psutil não disponível para informações do sistema."

        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            info = (
                f"CPU: {cpu_percent}% em uso\n"
                f"RAM: {memory.used / (1024**3):.1f}GB / "
                f"{memory.total / (1024**3):.1f}GB ({memory.percent}%)\n"
                f"Disco: {disk.used / (1024**3):.1f}GB / "
                f"{disk.total / (1024**3):.1f}GB ({disk.percent}%)"
            )
            return info

        except Exception as e:
            return f"Erro ao obter info do sistema: {e}"

    def _take_note(self, params: dict) -> str:
        """Salva uma nota/anotação em arquivo."""
        content = params.get("content", "")
        if not content:
            return "Conteúdo da anotação não especificado."

        from datetime import datetime

        notes_dir = Path(os.path.expanduser("~/Documents/alfred_notes"))
        notes_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        note_file = notes_dir / f"notas_{date_str}.md"

        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(note_file, "a", encoding="utf-8") as f:
            f.write(f"\n## [{timestamp}]\n{content}\n")

        return f"Nota salva em: {note_file}"

    def _is_path_allowed(self, path: str) -> bool:
        """Verifica se um caminho está dentro dos diretórios permitidos."""
        if not self.allowed_paths:
            return True  # Se não há restrições, permitir tudo

        resolved = Path(path).resolve()
        for allowed in self.allowed_paths:
            allowed_resolved = Path(allowed).resolve()
            try:
                resolved.relative_to(allowed_resolved)
                return True
            except ValueError:
                continue

        return False

    def _find_in_allowed_paths(self, filename: str) -> Path | None:
        """Tenta encontrar um arquivo pelo nome nos diretórios permitidos."""
        for allowed in self.allowed_paths:
            allowed_path = Path(allowed)
            if not allowed_path.exists():
                continue

            try:
                for match in allowed_path.rglob(f"*{filename}*"):
                    return match
            except PermissionError:
                continue

        return None
