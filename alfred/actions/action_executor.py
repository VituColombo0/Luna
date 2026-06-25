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
        # Expandir ~ nos caminhos permitidos
        raw_paths = self.config.get("allowed_paths", [])
        self.allowed_paths = [os.path.expanduser(os.path.expandvars(p)) for p in raw_paths]
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
            "run_command": self._run_command,
            "open_application": self._open_application,
            "control_volume": self._control_volume,
            "list_processes": self._list_processes,
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

    def _run_command(self, params: dict) -> str:
        """Executa um comando no terminal/shell do sistema."""
        command = params.get("command", "")
        if not command:
            return "Comando não especificado."

        if not self.allow_system_commands:
            return "Comandos de sistema estão desativados na configuração."

        # Bloquear comandos destrutivos óbvios
        dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:", "format c:"]
        if any(d in command.lower() for d in dangerous):
            return "Comando bloqueado por segurança."

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.expanduser("~"),
            )

            output = result.stdout.strip() if result.stdout else ""
            error = result.stderr.strip() if result.stderr else ""

            if result.returncode == 0:
                response = f"Comando executado com sucesso."
                if output:
                    # Limitar output para não sobrecarregar o TTS
                    lines = output.split("\n")
                    if len(lines) > 10:
                        response += f"\nSaída ({len(lines)} linhas):\n" + "\n".join(lines[:10]) + "\n..."
                    else:
                        response += f"\nSaída:\n{output}"
                return response
            else:
                return f"Erro no comando (código {result.returncode}): {error or output}"

        except subprocess.TimeoutExpired:
            return "Comando excedeu o tempo limite de 30 segundos."
        except Exception as e:
            return f"Erro ao executar comando: {e}"

    def _open_application(self, params: dict) -> str:
        """Abre um aplicativo pelo nome."""
        app_name = params.get("app_name", "").lower()
        if not app_name:
            return "Nome do aplicativo não especificado."

        # Mapa de aliases de aplicativos comuns
        app_aliases = {
            # Navegadores
            "chrome": "google-chrome",
            "google chrome": "google-chrome",
            "firefox": "firefox",
            "brave": "brave-browser",
            # Editores
            "code": "code",
            "vscode": "code",
            "visual studio code": "code",
            "vim": "vim",
            "nano": "nano",
            # Gerenciadores de arquivos
            "arquivos": "nautilus",
            "nautilus": "nautilus",
            "explorador": "nautilus",
            "files": "nautilus",
            "thunar": "thunar",
            "dolphin": "dolphin",
            # Terminal
            "terminal": "x-terminal-emulator",
            "konsole": "konsole",
            "gnome-terminal": "gnome-terminal",
            # Mídia
            "spotify": "spotify",
            "vlc": "vlc",
            # Comunicação
            "discord": "discord",
            "telegram": "telegram-desktop",
            "slack": "slack",
            # Utilitários
            "calculadora": "gnome-calculator",
            "calculator": "gnome-calculator",
            "configurações": "gnome-control-center",
            "settings": "gnome-control-center",
            "monitor do sistema": "gnome-system-monitor",
        }

        if self.system == "Windows":
            app_aliases.update({
                "arquivos": "explorer",
                "explorador": "explorer",
                "files": "explorer",
                "terminal": "cmd",
                "powershell": "powershell",
                "configurações": "ms-settings:",
                "settings": "ms-settings:",
                "calculadora": "calc",
                "calculator": "calc",
                "notepad": "notepad",
                "bloco de notas": "notepad",
            })

        actual_app = app_aliases.get(app_name, app_name)

        try:
            if self.system == "Windows":
                if actual_app.startswith("ms-"):
                    os.startfile(actual_app)
                else:
                    subprocess.Popen([actual_app], shell=True)
            else:
                subprocess.Popen(
                    [actual_app],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            return f"Abrindo {app_name}..."
        except FileNotFoundError:
            return f"Aplicativo '{app_name}' não encontrado no sistema."
        except Exception as e:
            return f"Erro ao abrir {app_name}: {e}"

    def _control_volume(self, params: dict) -> str:
        """Controla o volume do sistema."""
        action = params.get("action", "").lower()
        if not action:
            return "Ação de volume não especificada."

        try:
            if self.system == "Linux":
                if action == "up":
                    subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "10%+"],
                                   capture_output=True)
                    return "Volume aumentado em 10%."
                elif action == "down":
                    subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "10%-"],
                                   capture_output=True)
                    return "Volume diminuído em 10%."
                elif action == "mute":
                    subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "mute"],
                                   capture_output=True)
                    return "Volume mutado."
                elif action == "unmute":
                    subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "unmute"],
                                   capture_output=True)
                    return "Volume desmutado."
                elif action.isdigit():
                    level = min(int(action), 100)
                    subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"],
                                   capture_output=True)
                    return f"Volume ajustado para {level}%."
                else:
                    return f"Ação de volume desconhecida: {action}"

            elif self.system == "Windows":
                # Usar nircmd se disponível, senão PowerShell
                if action == "mute":
                    subprocess.run(
                        ["powershell", "-c",
                         "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
                        capture_output=True,
                    )
                    return "Volume mutado."
                else:
                    return "Controle de volume no Windows requer nircmd."
            else:
                return f"Controle de volume não suportado em {self.system}."

        except FileNotFoundError:
            return "amixer não encontrado. Instale alsa-utils."
        except Exception as e:
            return f"Erro ao controlar volume: {e}"

    def _list_processes(self, params: dict) -> str:
        """Lista ou mata processos."""
        if not PSUTIL_AVAILABLE:
            return "psutil não disponível."

        action = params.get("action", "list").lower()

        if action == "list":
            try:
                procs = []
                for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                    info = p.info
                    if info["cpu_percent"] and info["cpu_percent"] > 0.1:
                        procs.append(info)

                procs.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
                top = procs[:10]

                if not top:
                    return "Nenhum processo com uso significativo de CPU."

                lines = [f"  • {p['name']} (PID {p['pid']}) — CPU: {p['cpu_percent']:.1f}%, RAM: {p['memory_percent']:.1f}%"
                         for p in top]
                return "Top 10 processos:\n" + "\n".join(lines)
            except Exception as e:
                return f"Erro ao listar processos: {e}"

        elif action == "kill":
            name = params.get("name", "")
            if not name:
                return "Nome do processo não especificado."

            killed = 0
            for p in psutil.process_iter(["name"]):
                if name.lower() in p.info["name"].lower():
                    try:
                        p.kill()
                        killed += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            if killed:
                return f"Encerrados {killed} processo(s) com nome '{name}'."
            else:
                return f"Nenhum processo encontrado com nome '{name}'."

        return f"Ação desconhecida: {action}"

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
