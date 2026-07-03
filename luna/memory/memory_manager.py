"""
MemoryManager — Memória de longo prazo da Luna usando ChromaDB.

Armazena conversas como embeddings vetoriais para busca semântica.
Quando o usuário faz uma pergunta, o sistema busca memórias relevantes
e as injeta no contexto do LLM.

A memória persiste entre sessões — se o usuário falar de um projeto
hoje, a Luna vai lembrar dele daqui uma semana.
"""

import logging
import os
from datetime import datetime

try:
    # Desativar telemetria do ChromaDB (melhor prática de privacidade e logs)
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class MemoryManager:
    """
    Gerencia a memória de longo prazo da Luna via ChromaDB.

    As memórias são salvas automaticamente após cada interação e
    buscadas semanticamente antes de cada resposta, garantindo que
    a Luna se lembre de conversas passadas.
    """

    COLLECTION_NAME = "luna_memory"

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("memory", {})
        self.logger = logger

        self.enabled = self.config.get("enabled", True) and CHROMADB_AVAILABLE
        self.db_path = self.config.get("db_path", "data/memory")
        self.max_context = self.config.get("max_context_items", 5)
        self.auto_save = self.config.get("auto_save", True)

        self.client = None
        self.collection = None

        if not CHROMADB_AVAILABLE:
            self.logger.warning(
                "ChromaDB não disponível — memória desativada. "
                "Instale: [cyan]pip install chromadb[/]"
            )
            self.enabled = False
            return

        if self.enabled:
            self._initialize_db()

    def _initialize_db(self):
        """Inicializa o banco de dados ChromaDB."""
        try:
            os.makedirs(self.db_path, exist_ok=True)

            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(anonymized_telemetry=False),
            )

            self.collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

            count = self.collection.count()
            self.logger.info(
                f"Memória inicializada — [cyan]{count}[/] memórias armazenadas."
            )

        except Exception as e:
            self.logger.error(f"Erro ao inicializar ChromaDB: {e}")
            self.enabled = False

    def remember(self, user_message: str, assistant_response: str, user_name: str = "Usuário"):
        """
        Salva uma interação na memória de longo prazo.

        Cada interação é salva com metadados de data/hora e nome do usuário,
        permitindo buscas contextuais futuras.

        Args:
            user_message: O que o usuário disse.
            assistant_response: O que a Luna respondeu.
            user_name: Nome do usuário que falou.
        """
        if not self.enabled or not self.auto_save:
            return

        if not self.collection:
            return

        try:
            now = datetime.now()
            doc_id = f"mem_{now.strftime('%Y%m%d_%H%M%S_%f')}"

            # O documento que será embedding é a conversa completa, marcando o locutor
            document = f"{user_name}: {user_message}\nLuna: {assistant_response}"

            self.collection.add(
                documents=[document],
                metadatas=[
                    {
                        "user_message": user_message[:500],
                        "assistant_response": assistant_response[:500],
                        "user_name": user_name,
                        "timestamp": now.isoformat(),
                        "date": now.strftime("%d/%m/%Y"),
                        "time": now.strftime("%H:%M"),
                        "weekday": now.strftime("%A"),
                    }
                ],
                ids=[doc_id],
            )

            self.logger.debug(f"Memória salva: {doc_id} ({user_name})")

        except Exception as e:
            self.logger.error(f"Erro ao salvar memória: {e}")

    def recall(self, query: str, n_results: int | None = None) -> str:
        """
        Busca memórias relevantes para uma query.

        Usa busca semântica (cosine similarity) para encontrar memórias
        que são contextualmente relevantes para a pergunta atual.

        Args:
            query: Texto para buscar memórias semelhantes.
            n_results: Número máximo de resultados (None = usa max_context).

        Returns:
            String formatada com as memórias encontradas, ou vazio.
        """
        if not self.enabled or self.collection is None:
            return ""

        if n_results is None:
            n_results = self.max_context

        try:
            count = self.collection.count()
            if count == 0:
                return ""

            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
            )

            if not results or not results["documents"] or not results["documents"][0]:
                return ""

            memories = []
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                date = metadata.get("date", "?")
                time_ = metadata.get("time", "?")
                user = metadata.get("user_name", "")
                distance = results.get("distances", [[]])[0][i] if results.get("distances") else None

                # Só incluir memórias com relevância razoável (distância < 1.5)
                if distance is not None and distance > 1.5:
                    continue

                header = f"[{date} às {time_}]"
                if user:
                    header += f" (falando com {user})"

                memories.append(f"{header} {doc}")

            if not memories:
                return ""

            return "\n---\n".join(memories)

        except Exception as e:
            self.logger.error(f"Erro ao buscar memórias: {e}")
            return ""

    def remember_fact(self, fact: str, category: str = "general"):
        """
        Salva um fato específico na memória (não ligado a uma conversa).

        Útil para salvar informações sobre projetos, preferências, etc.

        Args:
            fact: O fato a ser memorizado.
            category: Categoria do fato (para filtragem futura).
        """
        if not self.enabled or not self.collection:
            return

        try:
            now = datetime.now()
            doc_id = f"fact_{now.strftime('%Y%m%d_%H%M%S_%f')}"

            self.collection.add(
                documents=[fact],
                metadatas=[
                    {
                        "type": "fact",
                        "category": category,
                        "timestamp": now.isoformat(),
                        "date": now.strftime("%d/%m/%Y"),
                        "time": now.strftime("%H:%M"),
                    }
                ],
                ids=[doc_id],
            )

            self.logger.debug(f"Fato memorizado: {doc_id}")

        except Exception as e:
            self.logger.error(f"Erro ao salvar fato: {e}")

    def get_stats(self) -> dict:
        """Retorna estatísticas da memória."""
        if not self.enabled or self.collection is None:
            return {"enabled": False, "count": 0}

        return {
            "enabled": True,
            "count": self.collection.count(),
            "db_path": self.db_path,
        }

    def get_recent_memories(self, n: int = 10) -> list[dict]:
        """
        Retorna as N memórias mais recentes.

        Args:
            n: Número de memórias a retornar.

        Returns:
            Lista de dicionários com as memórias.
        """
        if not self.enabled or self.collection is None:
            return []

        try:
            count = self.collection.count()
            if count == 0:
                return []

            # ChromaDB não tem "order by date", mas podemos pegar
            # os últimos IDs (que são cronológicos por design)
            results = self.collection.get(
                limit=min(n, count),
            )

            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    meta = results["metadatas"][i] if results["metadatas"] else {}
                    memories.append({
                        "text": doc,
                        "date": meta.get("date", "?"),
                        "time": meta.get("time", "?"),
                        "user": meta.get("user_name", "?"),
                    })

            return memories

        except Exception as e:
            self.logger.error(f"Erro ao buscar memórias recentes: {e}")
            return []
