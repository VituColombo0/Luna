"""
ObsidianMemory — Memória de longo prazo da Luna usando Obsidian Vault.

Em vez de embeddings vetoriais (ChromaDB), usa arquivos Markdown (.md)
organizados em um vault Obsidian. Isso permite:

- Memórias legíveis e editáveis pelo humano
- Busca por keyword + fuzzy matching em português
- Organização por categorias (diário, pessoas, projetos, preferências)
- Sincronização via Git/Obsidian Sync
- Zero dependências externas pesadas
- Debug fácil (basta abrir o arquivo .md)

Estrutura do Vault:
    vault_path/
    ├── Diário/
    │   ├── 2026-07-06.md    # Interações do dia (append)
    │   └── ...
    ├── Pessoas/
    │   └── <nome>.md        # Info sobre cada pessoa
    ├── Projetos/
    │   └── <nome>.md        # Info sobre projetos mencionados
    ├── Preferências.md       # Gostos, hábitos, configurações
    ├── Fatos.md              # Fatos importantes
    └── Índice.md             # Sumário com links
"""

import logging
import os
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path


class ObsidianMemory:
    """
    Gerencia a memória de longo prazo da Luna via Obsidian Vault (Markdown).

    Interface compatível com o antigo MemoryManager (remember/recall/get_stats),
    garantindo que o Orchestrator funcione sem mudanças significativas.
    """

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("memory", {})
        self.logger = logger

        self.enabled = self.config.get("enabled", True)
        self.vault_path = Path(
            os.path.expanduser(self.config.get("vault_path", "data/obsidian"))
        )
        self.max_context = self.config.get("max_context_items", 8)
        self.auto_save = self.config.get("auto_save", True)

        # Número de dias recentes para incluir automaticamente no contexto
        self.recent_days = self.config.get("recent_days", 3)

        if self.enabled:
            self._initialize_vault()

    def _initialize_vault(self):
        """Cria a estrutura de pastas do vault se não existir."""
        try:
            dirs = [
                self.vault_path,
                self.vault_path / "Diário",
                self.vault_path / "Pessoas",
                self.vault_path / "Projetos",
            ]
            for d in dirs:
                d.mkdir(parents=True, exist_ok=True)

            # Criar Índice.md se não existir
            index_path = self.vault_path / "Índice.md"
            if not index_path.exists():
                index_path.write_text(
                    "# 🌙 Luna — Memória\n\n"
                    "## Estrutura\n\n"
                    "- [[Preferências]] — Gostos e hábitos do usuário\n"
                    "- [[Fatos]] — Informações importantes\n"
                    "- **Diário/** — Registro diário de conversas\n"
                    "- **Pessoas/** — Perfis de pessoas conhecidas\n"
                    "- **Projetos/** — Projetos mencionados\n",
                    encoding="utf-8",
                )

            # Criar Preferências.md se não existir
            prefs_path = self.vault_path / "Preferências.md"
            if not prefs_path.exists():
                prefs_path.write_text(
                    "# ⭐ Preferências\n\n"
                    "Gostos, hábitos e preferências do usuário.\n\n"
                    "---\n\n",
                    encoding="utf-8",
                )

            # Criar Fatos.md se não existir
            facts_path = self.vault_path / "Fatos.md"
            if not facts_path.exists():
                facts_path.write_text(
                    "# 📌 Fatos Importantes\n\n"
                    "Informações que a Luna deve sempre lembrar.\n\n"
                    "---\n\n",
                    encoding="utf-8",
                )

            # Contar memórias existentes
            count = self._count_entries()
            self.logger.info(
                f"Obsidian Vault inicializado em [cyan]{self.vault_path}[/] — "
                f"[cyan]{count}[/] entradas encontradas."
            )

        except Exception as e:
            self.logger.error(f"Erro ao inicializar vault Obsidian: {e}")
            self.enabled = False

    # ─── Interface Pública (compatível com MemoryManager) ──────

    def remember(
        self,
        user_message: str,
        assistant_response: str,
        user_name: str = "Usuário",
    ):
        """
        Salva uma interação no diário do dia atual.

        Cada interação é adicionada ao final do arquivo do dia,
        com timestamp e formatação limpa em Markdown.

        Args:
            user_message: O que o usuário disse.
            assistant_response: O que a Luna respondeu.
            user_name: Nome do usuário que falou.
        """
        if not self.enabled or not self.auto_save:
            return

        try:
            now = datetime.now()
            diary_path = self._get_diary_path(now)

            # Criar cabeçalho do dia se arquivo não existir
            if not diary_path.exists():
                header = (
                    f"# 📋 Diário — {now.strftime('%d/%m/%Y')}\n\n"
                    f"**{self._weekday_pt(now)}**\n\n---\n\n"
                )
                diary_path.write_text(header, encoding="utf-8")

            # Adicionar entrada da interação
            time_str = now.strftime("%H:%M")
            entry = (
                f"### 🕐 {time_str}\n\n"
                f"**{user_name}:** {user_message}\n\n"
                f"**Luna:** {assistant_response}\n\n"
                f"---\n\n"
            )

            with open(diary_path, "a", encoding="utf-8") as f:
                f.write(entry)

            self.logger.debug(
                f"Memória salva no diário: {diary_path.name} ({user_name})"
            )

        except Exception as e:
            self.logger.error(f"Erro ao salvar memória: {e}")

    def recall(self, query: str, n_results: int | None = None) -> str:
        """
        Busca memórias relevantes para uma query.

        Combina duas estratégias:
        1. **Diários recentes**: Sempre inclui os últimos N dias
        2. **Busca por keywords**: Busca termos da query em todos os arquivos

        Também sempre inclui Preferências.md e Fatos.md como contexto base.

        Args:
            query: Texto para buscar memórias relevantes.
            n_results: Número máximo de resultados.

        Returns:
            String formatada com as memórias encontradas, ou vazio.
        """
        if not self.enabled:
            return ""

        if n_results is None:
            n_results = self.max_context

        try:
            memories = []

            # 1. Contexto base — Preferências e Fatos (sempre incluídos)
            base_context = self._load_base_context()
            if base_context:
                memories.append(base_context)

            # 2. Diários recentes (últimos N dias)
            recent = self._load_recent_diaries()
            if recent:
                memories.append(recent)

            # 3. Busca por keywords em todo o vault
            keyword_results = self._search_vault(query, max_results=n_results)
            if keyword_results:
                memories.append(keyword_results)

            if not memories:
                return ""

            return "\n\n".join(memories)

        except Exception as e:
            self.logger.error(f"Erro ao buscar memórias: {e}")
            return ""

    def remember_fact(self, fact: str, category: str = "general"):
        """
        Salva um fato específico no arquivo Fatos.md.

        Args:
            fact: O fato a ser memorizado.
            category: Categoria do fato.
        """
        if not self.enabled:
            return

        try:
            facts_path = self.vault_path / "Fatos.md"
            now = datetime.now()
            time_str = now.strftime("%d/%m/%Y %H:%M")

            entry = f"- **[{time_str}]** ({category}) {fact}\n"

            with open(facts_path, "a", encoding="utf-8") as f:
                f.write(entry)

            self.logger.debug(f"Fato memorizado: {fact[:50]}...")

        except Exception as e:
            self.logger.error(f"Erro ao salvar fato: {e}")

    def remember_preference(self, preference: str):
        """
        Salva uma preferência do usuário no arquivo Preferências.md.

        Args:
            preference: A preferência a ser memorizada.
        """
        if not self.enabled:
            return

        try:
            prefs_path = self.vault_path / "Preferências.md"
            now = datetime.now()
            time_str = now.strftime("%d/%m/%Y")

            entry = f"- **[{time_str}]** {preference}\n"

            with open(prefs_path, "a", encoding="utf-8") as f:
                f.write(entry)

            self.logger.debug(f"Preferência memorizada: {preference[:50]}...")

        except Exception as e:
            self.logger.error(f"Erro ao salvar preferência: {e}")

    def remember_person(self, name: str, info: str):
        """
        Salva ou atualiza informações sobre uma pessoa.

        Cria/atualiza um arquivo em Pessoas/<nome>.md.

        Args:
            name: Nome da pessoa.
            info: Informação para adicionar.
        """
        if not self.enabled:
            return

        try:
            safe_name = self._sanitize_filename(name)
            person_path = self.vault_path / "Pessoas" / f"{safe_name}.md"

            now = datetime.now()
            time_str = now.strftime("%d/%m/%Y %H:%M")

            if not person_path.exists():
                header = f"# 👤 {name}\n\n---\n\n"
                person_path.write_text(header, encoding="utf-8")

            entry = f"- **[{time_str}]** {info}\n"

            with open(person_path, "a", encoding="utf-8") as f:
                f.write(entry)

            self.logger.debug(f"Info sobre {name} salva.")

        except Exception as e:
            self.logger.error(f"Erro ao salvar info de pessoa: {e}")

    def remember_project(self, name: str, info: str):
        """
        Salva ou atualiza informações sobre um projeto.

        Cria/atualiza um arquivo em Projetos/<nome>.md.

        Args:
            name: Nome do projeto.
            info: Informação para adicionar.
        """
        if not self.enabled:
            return

        try:
            safe_name = self._sanitize_filename(name)
            project_path = self.vault_path / "Projetos" / f"{safe_name}.md"

            now = datetime.now()
            time_str = now.strftime("%d/%m/%Y %H:%M")

            if not project_path.exists():
                header = f"# 📁 {name}\n\n---\n\n"
                project_path.write_text(header, encoding="utf-8")

            entry = f"- **[{time_str}]** {info}\n"

            with open(project_path, "a", encoding="utf-8") as f:
                f.write(entry)

            self.logger.debug(f"Info sobre projeto {name} salva.")

        except Exception as e:
            self.logger.error(f"Erro ao salvar info de projeto: {e}")

    def get_stats(self) -> dict:
        """Retorna estatísticas da memória."""
        if not self.enabled:
            return {"enabled": False, "count": 0}

        count = self._count_entries()
        diary_count = len(list((self.vault_path / "Diário").glob("*.md")))
        people_count = len(list((self.vault_path / "Pessoas").glob("*.md")))
        projects_count = len(list((self.vault_path / "Projetos").glob("*.md")))

        return {
            "enabled": True,
            "count": count,
            "diary_days": diary_count,
            "people": people_count,
            "projects": projects_count,
            "vault_path": str(self.vault_path),
        }

    def get_recent_memories(self, n: int = 10) -> list[dict]:
        """
        Retorna as N entradas mais recentes do diário.

        Args:
            n: Número de entradas a retornar.

        Returns:
            Lista de dicionários com as memórias.
        """
        if not self.enabled:
            return []

        try:
            diary_dir = self.vault_path / "Diário"
            diary_files = sorted(diary_dir.glob("*.md"), reverse=True)

            memories = []
            for diary_file in diary_files:
                if len(memories) >= n:
                    break

                content = diary_file.read_text(encoding="utf-8")
                entries = self._parse_diary_entries(content)

                for entry in reversed(entries):
                    if len(memories) >= n:
                        break
                    memories.append(entry)

            return memories

        except Exception as e:
            self.logger.error(f"Erro ao buscar memórias recentes: {e}")
            return []

    # ─── Métodos Internos ──────────────────────────────────────

    def _get_diary_path(self, dt: datetime) -> Path:
        """Retorna o caminho do arquivo de diário para uma data."""
        return self.vault_path / "Diário" / f"{dt.strftime('%Y-%m-%d')}.md"

    def _weekday_pt(self, dt: datetime) -> str:
        """Retorna o nome do dia da semana em português."""
        days = {
            0: "Segunda-feira",
            1: "Terça-feira",
            2: "Quarta-feira",
            3: "Quinta-feira",
            4: "Sexta-feira",
            5: "Sábado",
            6: "Domingo",
        }
        return days.get(dt.weekday(), "")

    def _sanitize_filename(self, name: str) -> str:
        """Remove caracteres inválidos para nomes de arquivo."""
        # Normalizar unicode e manter acentos
        safe = re.sub(r'[<>:"/\\|?*]', "", name)
        safe = safe.strip(". ")
        return safe or "sem_nome"

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para busca: lowercase, remove acentos."""
        text = text.lower()
        # Remover acentos para matching mais robusto
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def _count_entries(self) -> int:
        """Conta o número total de entradas no vault."""
        count = 0
        try:
            # Contar entradas nos diários
            diary_dir = self.vault_path / "Diário"
            for diary_file in diary_dir.glob("*.md"):
                content = diary_file.read_text(encoding="utf-8")
                count += content.count("### 🕐")

            # Contar fatos
            facts_path = self.vault_path / "Fatos.md"
            if facts_path.exists():
                content = facts_path.read_text(encoding="utf-8")
                count += content.count("- **[")

            # Contar preferências
            prefs_path = self.vault_path / "Preferências.md"
            if prefs_path.exists():
                content = prefs_path.read_text(encoding="utf-8")
                count += content.count("- **[")

        except Exception:
            pass

        return count

    def _load_base_context(self) -> str:
        """Carrega Preferências.md e Fatos.md como contexto base."""
        parts = []

        # Preferências
        prefs_path = self.vault_path / "Preferências.md"
        if prefs_path.exists():
            content = prefs_path.read_text(encoding="utf-8").strip()
            # Pegar só as linhas com itens (ignorar cabeçalho)
            items = [
                line
                for line in content.split("\n")
                if line.strip().startswith("- ")
            ]
            if items:
                parts.append(
                    "PREFERÊNCIAS DO USUÁRIO:\n" + "\n".join(items[-10:])
                )

        # Fatos
        facts_path = self.vault_path / "Fatos.md"
        if facts_path.exists():
            content = facts_path.read_text(encoding="utf-8").strip()
            items = [
                line
                for line in content.split("\n")
                if line.strip().startswith("- ")
            ]
            if items:
                parts.append(
                    "FATOS IMPORTANTES:\n" + "\n".join(items[-10:])
                )

        return "\n\n".join(parts) if parts else ""

    def _load_recent_diaries(self) -> str:
        """Carrega os diários dos últimos N dias."""
        parts = []
        now = datetime.now()

        for days_ago in range(self.recent_days):
            date = now - timedelta(days=days_ago)
            diary_path = self._get_diary_path(date)

            if not diary_path.exists():
                continue

            try:
                content = diary_path.read_text(encoding="utf-8").strip()

                # Limitar tamanho — pegar as últimas entradas do dia
                lines = content.split("\n")

                # Encontrar as últimas N entradas (separadas por "### 🕐")
                entries = content.split("### 🕐")
                # Pegar as últimas 5 entradas do dia
                recent_entries = entries[-5:] if len(entries) > 5 else entries[1:]

                if recent_entries:
                    label = "HOJE" if days_ago == 0 else f"HÁ {days_ago} DIA(S)"
                    date_str = date.strftime("%d/%m/%Y")
                    reconstructed = f"[{label} — {date_str}]\n"
                    for entry in recent_entries:
                        # Reconstruir com o marcador
                        entry_text = entry.strip()
                        if entry_text:
                            reconstructed += f"### 🕐{entry_text}\n\n"

                    parts.append(reconstructed.strip())

            except Exception as e:
                self.logger.debug(f"Erro ao ler diário {diary_path}: {e}")

        if not parts:
            return ""

        return "CONVERSAS RECENTES:\n" + "\n---\n".join(parts)

    def _search_vault(self, query: str, max_results: int = 5) -> str:
        """
        Busca por keywords em todos os arquivos do vault.

        Usa busca fuzzy e normalizada (sem acento) para
        melhor resultado com português brasileiro.

        Args:
            query: Texto de busca.
            max_results: Máximo de resultados.

        Returns:
            String formatada com resultados encontrados.
        """
        if not query or not query.strip():
            return ""

        # Extrair palavras-chave da query (ignorar stopwords)
        stopwords = {
            "o", "a", "os", "as", "um", "uma", "de", "do", "da", "dos",
            "das", "em", "no", "na", "nos", "nas", "por", "para", "com",
            "se", "que", "e", "ou", "não", "nao", "mas", "como", "quando",
            "onde", "quem", "qual", "eu", "tu", "ele", "ela", "nós", "nos",
            "eles", "elas", "meu", "minha", "seu", "sua", "esse", "essa",
            "este", "esta", "isso", "isto", "aquilo", "já", "ja", "ainda",
            "mais", "muito", "bem", "ser", "ter", "fazer", "ir", "estar",
            "poder", "dever", "saber", "ver", "querer", "dizer", "dar",
            "foi", "era", "tem", "está", "vai", "pode", "deve", "sou",
            "voce", "você", "me", "te", "lhe", "lo", "la", "sobre",
            "luna", "lembra", "lembrar", "sabe", "conta", "fala", "fale",
        }

        query_norm = self._normalize_text(query)
        keywords = [
            w for w in query_norm.split()
            if len(w) > 2 and w not in stopwords
        ]

        if not keywords:
            return ""

        results = []
        seen_files = set()

        # Buscar em todos os .md do vault
        for md_file in self.vault_path.rglob("*.md"):
            if md_file.name == "Índice.md":
                continue

            # Evitar duplicação com diários recentes (já incluídos)
            rel = md_file.relative_to(self.vault_path)
            if str(rel).startswith("Diário/"):
                # Só buscar em diários mais antigos que recent_days
                try:
                    date_str = md_file.stem  # YYYY-MM-DD
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if (datetime.now() - file_date).days < self.recent_days:
                        continue  # Já incluído nos recentes
                except ValueError:
                    pass

            try:
                content = md_file.read_text(encoding="utf-8")
                content_norm = self._normalize_text(content)

                # Calcular score por frequência de keywords
                score = sum(
                    content_norm.count(kw) for kw in keywords
                )

                if score > 0 and md_file.name not in seen_files:
                    seen_files.add(md_file.name)

                    # Extrair linhas relevantes (que contêm keywords)
                    relevant_lines = []
                    for line in content.split("\n"):
                        line_norm = self._normalize_text(line)
                        if any(kw in line_norm for kw in keywords):
                            clean_line = line.strip()
                            if clean_line and not clean_line.startswith("#"):
                                relevant_lines.append(clean_line)

                    if relevant_lines:
                        # Limitar a 5 linhas por arquivo
                        snippet = "\n".join(relevant_lines[:5])
                        source = str(rel).replace(".md", "")
                        results.append((score, source, snippet))

            except Exception:
                continue

        if not results:
            return ""

        # Ordenar por relevância (score descendente)
        results.sort(key=lambda x: x[0], reverse=True)
        results = results[:max_results]

        # Formatar resultados
        formatted = []
        for score, source, snippet in results:
            formatted.append(f"[De: {source}]\n{snippet}")

        return "MEMÓRIAS RELACIONADAS:\n" + "\n---\n".join(formatted)

    def _parse_diary_entries(self, content: str) -> list[dict]:
        """
        Faz parsing das entradas de um diário.

        Args:
            content: Conteúdo do arquivo .md do diário.

        Returns:
            Lista de dicts com 'time', 'user', 'text'.
        """
        entries = []
        blocks = content.split("### 🕐")

        for block in blocks[1:]:  # Pular header
            lines = block.strip().split("\n")
            if not lines:
                continue

            time_str = lines[0].strip()
            text_parts = []
            user = "?"

            for line in lines[1:]:
                line = line.strip()
                if line.startswith("**") and ":**" in line:
                    # Extrair nome do user
                    name_match = re.match(r"\*\*(.+?):\*\*\s*(.*)", line)
                    if name_match:
                        speaker = name_match.group(1)
                        msg = name_match.group(2)
                        if speaker != "Luna":
                            user = speaker
                        text_parts.append(f"{speaker}: {msg}")
                elif line and line != "---":
                    text_parts.append(line)

            if text_parts:
                entries.append({
                    "time": time_str,
                    "user": user,
                    "text": "\n".join(text_parts),
                    "date": "?",
                })

        return entries
