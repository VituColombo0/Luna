"""
ActionExecutor — Executa ações no computador a pedido da Luna.

Suporta:
- Abrir arquivos e pastas
- Abrir URLs no navegador
- Pesquisar na web
- Buscar arquivos locais
- Obter informações do sistema
- Screenshots e clipboard
- Controle de teclado e mouse
- Controle de brilho, rede e energia
- Temporizadores
- Leitura e escrita de arquivos
"""

import logging
import os
import platform
import subprocess
import threading
import time
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
    Executor de ações da Luna no sistema operacional.
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
            "take_screenshot": self._take_screenshot,
            "clipboard": self._clipboard,
            "control_brightness": self._control_brightness,
            "system_power": self._system_power,
            "manage_network": self._manage_network,
            "type_text": self._type_text,
            "hotkey": self._hotkey,
            "set_timer": self._set_timer,
            "read_file_content": self._read_file_content,
            "write_file_content": self._write_file_content,
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

        # Se o caminho não é absoluto e não começa com ~, tentar como relativo ao home
        if not target.is_absolute():
            home_target = Path(os.path.expanduser("~")) / path
            if home_target.exists():
                target = home_target
            else:
                # Tentar nos caminhos comuns do usuário
                common_dirs = ["Documents", "Downloads", "Desktop", "Pictures", "Videos"]
                for d in common_dirs:
                    candidate = Path(os.path.expanduser("~")) / d / path
                    if candidate.exists():
                        target = candidate
                        break

        # Verificar se o caminho existe
        if not target.exists():
            # Tentar procurar em pastas permitidas (busca case-insensitive)
            found = self._find_in_allowed_paths(target.name)
            if found:
                target = found
            else:
                return f"Arquivo não encontrado: {path}. Verifique se o caminho está correto."

        # Verificar permissão de acesso
        if not self._is_path_allowed(str(target)):
            return f"Acesso negado ao caminho: {path}"

        try:
            if self.system == "Linux":
                subprocess.Popen(
                    ["xdg-open", str(target)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
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

        self.logger.info(f"Abrindo URL: [cyan]{url}[/]")

        try:
            # Tentar webbrowser primeiro
            success = webbrowser.open(url)
            if success:
                return f"Abrindo no navegador: {url}"
        except Exception as e:
            self.logger.debug(f"webbrowser.open falhou: {e}")

        # Fallback: xdg-open no Linux
        if self.system == "Linux":
            try:
                subprocess.Popen(
                    ["xdg-open", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return f"Abrindo no navegador: {url}"
            except Exception as e:
                return f"Erro ao abrir navegador: {e}"

        return f"Não foi possível abrir o navegador para: {url}"

    def _search_web(self, params: dict) -> str:
        """Pesquisa algo no Google via navegador."""
        query = params.get("query", "")
        if not query:
            return "Termo de pesquisa não especificado."

        if not self.allow_browser:
            return "Navegador desativado na configuração."

        url = f"https://www.google.com/search?q={quote_plus(query)}"
        self.logger.info(f"Pesquisando: [cyan]{query}[/] -> {url}")

        try:
            success = webbrowser.open(url)
            if success:
                return f"Pesquisando: {query}"
        except Exception as e:
            self.logger.debug(f"webbrowser.open falhou: {e}")

        # Fallback: xdg-open no Linux
        if self.system == "Linux":
            try:
                subprocess.Popen(
                    ["xdg-open", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return f"Pesquisando: {query}"
            except Exception as e:
                return f"Erro na pesquisa: {e}"

        return f"Não foi possível abrir o navegador para pesquisar: {query}"

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

        notes_dir = Path(os.path.expanduser("~/Documents/luna_notes"))
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

    # ─── Novas Ações ─────────────────────────────────────────────

    def _take_screenshot(self, params: dict) -> str:
        """Tira uma captura de tela."""
        from datetime import datetime
        region = params.get("region", "full")
        screenshots_dir = Path(os.path.expanduser("~/Pictures/luna_screenshots"))
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        filename = screenshots_dir / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        try:
            if self.system == "Linux":
                if region == "active":
                    subprocess.run(["gnome-screenshot", "-w", "-f", str(filename)],
                                   capture_output=True, timeout=10)
                else:
                    subprocess.run(["gnome-screenshot", "-f", str(filename)],
                                   capture_output=True, timeout=10)
            elif self.system == "Windows":
                try:
                    import pyautogui
                    img = pyautogui.screenshot()
                    img.save(str(filename))
                except ImportError:
                    subprocess.run(["powershell", "-c",
                        f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen"],
                        capture_output=True)
                    return "pyautogui não instalado para screenshots."
            return f"Screenshot salva em: {filename}"
        except Exception as e:
            return f"Erro ao tirar screenshot: {e}"

    def _clipboard(self, params: dict) -> str:
        """Lê ou escreve na área de transferência."""
        action = params.get("action", "read").lower()
        try:
            if action == "read":
                if self.system == "Linux":
                    result = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                           capture_output=True, text=True, timeout=5)
                    return f"Conteúdo da clipboard: {result.stdout[:500]}" if result.stdout else "Clipboard vazia."
                elif self.system == "Windows":
                    result = subprocess.run(["powershell", "-c", "Get-Clipboard"],
                                           capture_output=True, text=True, timeout=5)
                    return f"Conteúdo da clipboard: {result.stdout[:500]}" if result.stdout else "Clipboard vazia."
            elif action == "write":
                text = params.get("text", "")
                if not text:
                    return "Texto não especificado."
                if self.system == "Linux":
                    process = subprocess.Popen(["xclip", "-selection", "clipboard"],
                                              stdin=subprocess.PIPE)
                    process.communicate(text.encode())
                elif self.system == "Windows":
                    subprocess.run(["powershell", "-c", f"Set-Clipboard -Value '{text}'"],
                                   capture_output=True)
                return f"Texto copiado para clipboard."
            return f"Ação de clipboard desconhecida: {action}"
        except Exception as e:
            return f"Erro na clipboard: {e}"

    def _control_brightness(self, params: dict) -> str:
        """Controla o brilho da tela."""
        action = params.get("action", "").lower()
        if not action:
            return "Ação de brilho não especificada."
        try:
            if self.system == "Linux":
                if action == "up":
                    subprocess.run(["xrandr", "--output", "eDP-1", "--brightness", "1.0"],
                                   capture_output=True)
                    return "Brilho aumentado."
                elif action == "down":
                    subprocess.run(["xrandr", "--output", "eDP-1", "--brightness", "0.5"],
                                   capture_output=True)
                    return "Brilho diminuído."
                elif action.isdigit():
                    level = min(int(action), 100) / 100.0
                    subprocess.run(["xrandr", "--output", "eDP-1", "--brightness", str(level)],
                                   capture_output=True)
                    return f"Brilho ajustado para {int(level*100)}%."
            return f"Controle de brilho não suportado em {self.system}."
        except Exception as e:
            return f"Erro ao controlar brilho: {e}"

    def _system_power(self, params: dict) -> str:
        """Controla energia do sistema."""
        action = params.get("action", "").lower()
        try:
            if self.system == "Linux":
                cmds = {
                    "shutdown": ["systemctl", "poweroff"],
                    "restart": ["systemctl", "reboot"],
                    "suspend": ["systemctl", "suspend"],
                    "lock": ["loginctl", "lock-session"],
                }
            elif self.system == "Windows":
                cmds = {
                    "shutdown": ["shutdown", "/s", "/t", "0"],
                    "restart": ["shutdown", "/r", "/t", "0"],
                    "suspend": ["rundll32.exe", "powrprof.dll,SetSuspendState"],
                    "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
                }
            else:
                return f"Não suportado em {self.system}."

            cmd = cmds.get(action)
            if cmd:
                subprocess.Popen(cmd)
                return f"Executando: {action}..."
            return f"Ação de energia desconhecida: {action}"
        except Exception as e:
            return f"Erro: {e}"

    def _manage_network(self, params: dict) -> str:
        """Gerencia conexão de rede."""
        action = params.get("action", "status").lower()
        try:
            if action == "ip":
                import socket
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                return f"Hostname: {hostname}\nIP local: {local_ip}"
            elif action == "status":
                if PSUTIL_AVAILABLE:
                    nets = psutil.net_if_addrs()
                    stats = psutil.net_if_stats()
                    info_lines = []
                    for iface, addrs in nets.items():
                        is_up = stats[iface].isup if iface in stats else False
                        for addr in addrs:
                            if addr.family.name == 'AF_INET':
                                info_lines.append(f"  {iface}: {addr.address} ({'UP' if is_up else 'DOWN'})")
                    return "Interfaces de rede:\n" + "\n".join(info_lines) if info_lines else "Nenhuma interface encontrada."
                return "psutil não disponível."
            elif action == "wifi_on" and self.system == "Linux":
                subprocess.run(["nmcli", "radio", "wifi", "on"], capture_output=True)
                return "Wi-Fi ligado."
            elif action == "wifi_off" and self.system == "Linux":
                subprocess.run(["nmcli", "radio", "wifi", "off"], capture_output=True)
                return "Wi-Fi desligado."
            return f"Ação de rede desconhecida: {action}"
        except Exception as e:
            return f"Erro na rede: {e}"

    def _type_text(self, params: dict) -> str:
        """Digita texto simulando teclado."""
        text = params.get("text", "")
        if not text:
            return "Texto não especificado."
        try:
            if self.system == "Linux":
                subprocess.run(["xdotool", "type", "--delay", "20", text],
                               capture_output=True, timeout=30)
                if params.get("press_enter", "").lower() == "true":
                    subprocess.run(["xdotool", "key", "Return"], capture_output=True)
            elif self.system == "Windows":
                try:
                    import pyautogui
                    pyautogui.typewrite(text, interval=0.02)
                    if params.get("press_enter", "").lower() == "true":
                        pyautogui.press("enter")
                except ImportError:
                    return "pyautogui não instalado."
            return f"Texto digitado."
        except Exception as e:
            return f"Erro ao digitar: {e}"

    def _hotkey(self, params: dict) -> str:
        """Pressiona uma combinação de teclas."""
        keys = params.get("keys", "")
        if not keys:
            return "Teclas não especificadas."
        try:
            key_list = [k.strip().lower() for k in keys.split("+")]
            if self.system == "Linux":
                xdotool_keys = "+".join(key_list)
                subprocess.run(["xdotool", "key", xdotool_keys], capture_output=True)
            elif self.system == "Windows":
                try:
                    import pyautogui
                    pyautogui.hotkey(*key_list)
                except ImportError:
                    return "pyautogui não instalado."
            return f"Atalho {keys} pressionado."
        except Exception as e:
            return f"Erro no atalho: {e}"

    def _set_timer(self, params: dict) -> str:
        """Configura um temporizador."""
        try:
            seconds = int(params.get("seconds", 0))
        except (ValueError, TypeError):
            return "Tempo inválido."
        if seconds <= 0:
            return "Tempo deve ser maior que zero."

        message = params.get("message", "Timer finalizado!")

        def _timer_callback():
            time.sleep(seconds)
            # Notificar via sistema
            if self.system == "Linux":
                subprocess.run(["notify-send", "Luna Timer", message], capture_output=True)
                # Também tocar um som
                subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                               capture_output=True)
            elif self.system == "Windows":
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, message, "Luna Timer", 0x40)
                except Exception:
                    pass

        thread = threading.Thread(target=_timer_callback, daemon=True)
        thread.start()

        mins = seconds // 60
        secs = seconds % 60
        time_str = f"{mins}min {secs}s" if mins > 0 else f"{secs}s"
        return f"Timer configurado para {time_str}. Vou te avisar!"

    def _read_file_content(self, params: dict) -> str:
        """Lê o conteúdo de um arquivo de texto."""
        path = params.get("path", "")
        if not path:
            return "Caminho não especificado."
        path = os.path.expanduser(os.path.expandvars(path))
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(2000)  # Limitar a 2000 chars
            truncated = " (truncado)" if len(content) >= 2000 else ""
            return f"Conteúdo de {path}{truncated}:\n{content}"
        except FileNotFoundError:
            return f"Arquivo não encontrado: {path}"
        except Exception as e:
            return f"Erro ao ler arquivo: {e}"

    def _write_file_content(self, params: dict) -> str:
        """Escreve conteúdo em um arquivo de texto."""
        path = params.get("path", "")
        content = params.get("content", "")
        if not path:
            return "Caminho não especificado."
        if not content:
            return "Conteúdo não especificado."
        path = os.path.expanduser(os.path.expandvars(path))
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Arquivo salvo em: {path}"
        except Exception as e:
            return f"Erro ao escrever arquivo: {e}"

    # ─── Utilidades Internas ─────────────────────────────────────

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
