"""
MemoryManager — Memória de longo prazo do Alfred usando ChromaDB.

Armazena conversas como embeddings vetoriais para busca semântica.
Quando o usuário faz uma pergunta, o sistema busca memórias relevantes
e as injeta no contexto do LLM.
"""

import logging
import os
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class MemoryManager:
    """
    Gerencia a memória de longo prazo do Alfred via ChromaDB.
    """

    COLLECTION_NAME = "alfred_memory"

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

    def remember(self, user_message: str, assistant_response: str):
        """
        Salva uma interação na memória de longo prazo.

        Args:
            user_message: O que o usuário disse.
            assistant_response: O que o Alfred respondeu.
        """
        if not self.enabled or not self.auto_save:
            return

        try:
            now = datetime.now()
            doc_id = f"mem_{now.strftime('%Y%m%d_%H%M%S_%f')}"

            # O documento que será embedding é a conversa completa
            document = f"Usuário: {user_message}\nAlfred: {assistant_response}"

            self.collection.add(
                documents=[document],
                metadatas=[
                    {
                        "user_message": user_message[:500],
                        "assistant_response": assistant_response[:500],
                        "timestamp": now.isoformat(),
                        "date": now.strftime("%d/%m/%Y"),
                        "time": now.strftime("%H:%M"),
                    }
                ],
                ids=[doc_id],
            )

            self.logger.debug(f"Memória salva: {doc_id}")

        except Exception as e:
            self.logger.error(f"Erro ao salvar memória: {e}")

    def recall(self, query: str) -> str:
        """
        Busca memórias relevantes para uma query.

        Args:
            query: Texto para buscar memórias semelhantes.

        Returns:
            String formatada com as memórias encontradas, ou vazio.
        """
        if not self.enabled or self.collection is None:
            return ""

        try:
            count = self.collection.count()
            if count == 0:
                return ""

            results = self.collection.query(
                query_texts=[query],
                n_results=min(self.max_context, count),
            )

            if not results or not results["documents"] or not results["documents"][0]:
                return ""

            memories = []
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                date = metadata.get("date", "?")
                time_ = metadata.get("time", "?")
                memories.append(f"[{date} às {time_}] {doc}")

            return "\n---\n".join(memories)

        except Exception as e:
            self.logger.error(f"Erro ao buscar memórias: {e}")
            return ""

    def get_stats(self) -> dict:
        """Retorna estatísticas da memória."""
        if not self.enabled or self.collection is None:
            return {"enabled": False, "count": 0}

        return {
            "enabled": True,
            "count": self.collection.count(),
            "db_path": self.db_path,
        }
