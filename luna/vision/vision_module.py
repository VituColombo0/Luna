"""
VisionModule — Visão computacional da Luna.

Funcionalidades:
- Captura de imagens da webcam
- Reconhecimento facial dos membros do grupo
- Descrição de cenas via modelo de visão (moondream via Ollama)
- Identificação de quem está falando baseado em fotos cadastradas
- Integração com arquivo de Membros para contexto personalizado
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

try:
    import cv2

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    import face_recognition

    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class VisionModule:
    """
    Módulo de visão do Luna — câmera, reconhecimento facial e análise de imagem.

    Integra com o arquivo Membros.txt para saber quem são os membros do grupo
    e dar contexto ao LLM sobre com quem está falando.
    """

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("vision", {})
        self.llm_config = config.get("llm", {})
        self.logger = logger

        self.enabled = self.config.get("enabled", True) and OPENCV_AVAILABLE
        self.camera_index = self.config.get("camera_index", 0)
        self.face_rec_enabled = (
            self.config.get("face_recognition", True) and FACE_REC_AVAILABLE
        )
        self.faces_dir = self.config.get("faces_dir", "data/faces")
        self.vision_model = self.llm_config.get("vision_model", "moondream")
        self.ollama_host = self.llm_config.get("ollama_host", "http://localhost:11434")

        # Encodings conhecidos (carregados do faces_dir)
        self.known_encodings: list[np.ndarray] = []
        self.known_names: list[str] = []

        # Informações dos membros carregadas do Membros.txt
        self.members_info: dict[str, str] = {}

        if not OPENCV_AVAILABLE:
            self.logger.warning(
                "OpenCV não disponível — visão desativada. "
                "Instale: [cyan]pip install opencv-python[/]"
            )
            self.enabled = False
            return

        # Carregar info dos membros
        self._load_members_info()

        if self.face_rec_enabled:
            self._load_known_faces()

        self.logger.info(
            f"Vision inicializado — câmera: [cyan]{self.camera_index}[/], "
            f"rostos conhecidos: [cyan]{len(self.known_names)}[/], "
            f"membros carregados: [cyan]{len(self.members_info)}[/]"
        )

    def _load_members_info(self):
        """
        Carrega informações dos membros do arquivo Membros.txt.

        Procura o arquivo na raiz do projeto e parseia os blocos
        de texto associados a cada pessoa.
        """
        # Procurar Membros.txt na raiz do projeto
        project_root = Path(__file__).resolve().parent.parent.parent
        members_file = project_root / "Membros.txt"

        if not members_file.exists():
            self.logger.info(
                "Arquivo Membros.txt não encontrado. "
                "Crie-o na raiz do projeto para identificação de membros."
            )
            return

        try:
            content = members_file.read_text(encoding="utf-8")
            self._parse_members(content)
            self.logger.info(
                f"Membros carregados: {', '.join(self.members_info.keys())}"
            )
        except Exception as e:
            self.logger.warning(f"Erro ao carregar Membros.txt: {e}")

    def _parse_members(self, content: str):
        """
        Parseia o conteúdo do Membros.txt e extrai informações de cada membro.

        Identifica blocos de texto associados a nomes conhecidos.
        O arquivo pode ter formato livre — o parser procura por nomes
        seguidos de descrições.

        Args:
            content: Conteúdo completo do arquivo Membros.txt.
        """
        lines = content.strip().split("\n")

        current_name = None
        current_desc = []

        # Nomes que indicam início de um novo membro
        # (linhas curtas que parecem ser nomes de pessoas)
        potential_names = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # Detectar se é um nome (linha curta, sem ponto, sem dois pontos no fim)
            # Heurística: linha com 2-5 palavras, sem pontuação pesada
            words = stripped.split()
            is_name_line = (
                2 <= len(words) <= 6
                and not stripped.endswith(".")
                and not stripped.endswith(":")
                and not stripped.startswith("-")
                and not stripped.startswith("•")
                and not stripped.lower().startswith("o professor")
                and not stripped.lower().startswith("os outros")
                and not stripped.lower() == "membros"
                and not stripped.lower().startswith("formação")
                and not stripped.lower().startswith("áreas")
                and not stripped.lower().startswith("cargo")
                and not stripped.lower().startswith("esse é")
                and not stripped.lower().startswith("atualmente")
                and any(w[0].isupper() for w in words)
                and len(stripped) < 60
            )

            if is_name_line and not any(c in stripped for c in [".", ";", ",", ":"]):
                # Salvar bloco anterior
                if current_name:
                    self.members_info[current_name] = "\n".join(current_desc).strip()

                current_name = stripped
                current_desc = []
            elif current_name:
                current_desc.append(stripped)
            else:
                # Texto antes do primeiro nome — tentar capturar como info geral
                # Verificar se menciona um nome no meio da descrição
                if "professor" in stripped.lower() and "gazziro" in stripped.lower():
                    current_name = "Mario Alexandre Gazziro"
                    current_desc = [stripped]
                elif "professor mario" in stripped.lower():
                    current_name = "Mario Alexandre Gazziro"
                    current_desc = [stripped]

        # Salvar o último bloco
        if current_name:
            self.members_info[current_name] = "\n".join(current_desc).strip()

    def get_member_info(self, name: str) -> str:
        """
        Retorna informações sobre um membro pelo nome.

        Faz busca parcial (se o nome contém parte do nome cadastrado).

        Args:
            name: Nome a buscar.

        Returns:
            Descrição do membro ou string vazia.
        """
        import unicodedata

        def _normalize(text: str) -> str:
            # Remove acentos
            nfkd = unicodedata.normalize('NFKD', text)
            return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()

        # Busca exata (normalizada)
        name_norm = _normalize(name)
        for member_name, info in self.members_info.items():
            if _normalize(member_name) == name_norm:
                return info

        # Busca parcial com pontuação
        search_parts = [p for p in name_norm.split() if len(p) > 2]

        best_match = None
        best_score = 0

        for member_name, info in self.members_info.items():
            member_parts = _normalize(member_name).split()
            score = 0

            for part in search_parts:
                if any(part in mp for mp in member_parts):
                    score += 1

            if score > best_score:
                best_score = score
                best_match = info

        if best_match and best_score > 0:
            return best_match

        return ""

    def get_all_members_context(self) -> str:
        """
        Retorna um resumo de todos os membros para injetar no prompt do LLM.

        Returns:
            String formatada com info de todos os membros.
        """
        if not self.members_info:
            return ""

        parts = []
        for name, info in self.members_info.items():
            # Pegar apenas as primeiras 200 chars da info para não estourar o contexto
            short_info = info[:200] + "..." if len(info) > 200 else info
            parts.append(f"- {name}: {short_info}")

        return "MEMBROS DO GRUPO:\n" + "\n".join(parts)

    def _load_known_faces(self):
        """
        Carrega faces conhecidas da pasta faces_dir.

        Estrutura esperada:
            data/faces/
                nome_da_pessoa/
                    foto1.jpg
                    foto2.jpg
        """
        faces_path = Path(self.faces_dir)
        if not faces_path.exists():
            faces_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(
                f"Pasta de faces criada: [cyan]{faces_path}[/]\n"
                "Adicione subpastas com fotos para reconhecimento facial."
            )
            return

        for person_dir in faces_path.iterdir():
            if not person_dir.is_dir():
                continue

            person_name = person_dir.name

            for img_file in person_dir.iterdir():
                if img_file.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                    continue

                try:
                    image = face_recognition.load_image_file(str(img_file))
                    encodings = face_recognition.face_encodings(image)

                    if encodings:
                        self.known_encodings.append(encodings[0])
                        self.known_names.append(person_name)
                        self.logger.debug(
                            f"Face carregada: {person_name} ({img_file.name})"
                        )
                except Exception as e:
                    self.logger.warning(
                        f"Erro ao carregar face {img_file}: {e}"
                    )

        if self.known_names:
            unique = set(self.known_names)
            self.logger.info(
                f"Rostos carregados: {', '.join(unique)} "
                f"({len(self.known_encodings)} fotos total)"
            )

    def capture_frame(self) -> np.ndarray | None:
        """
        Captura um frame da webcam.

        Returns:
            Frame como array numpy (BGR) ou None se falhar.
        """
        if not self.enabled:
            return None

        try:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                self.logger.warning("Não foi possível abrir a câmera.")
                return None

            # Capturar múltiplos frames para pegar um bom (descarta os primeiros)
            for _ in range(5):
                ret, frame = cap.read()

            cap.release()

            if ret:
                return frame
            return None

        except Exception as e:
            self.logger.error(f"Erro ao capturar frame: {e}")
            return None

    def save_frame(self, frame: np.ndarray, path: str) -> bool:
        """
        Salva um frame como arquivo de imagem.

        Args:
            frame: Frame numpy (BGR).
            path: Caminho do arquivo de saída.

        Returns:
            True se salvou com sucesso.
        """
        try:
            cv2.imwrite(path, frame)
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar frame: {e}")
            return False

    def identify_face(self, frame: np.ndarray | None = None) -> str | None:
        """
        Identifica quem está na frente da câmera.

        Args:
            frame: Frame opcional. Se None, captura da webcam.

        Returns:
            Nome da pessoa identificada ou None.
        """
        if not self.face_rec_enabled or not self.known_encodings:
            return None

        if frame is None:
            frame = self.capture_frame()
            if frame is None:
                return None

        try:
            # Reduzir resolução para performance
            small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small)
            face_encodings = face_recognition.face_encodings(
                rgb_small, face_locations
            )

            for encoding in face_encodings:
                matches = face_recognition.compare_faces(
                    self.known_encodings, encoding, tolerance=0.6
                )
                distances = face_recognition.face_distance(
                    self.known_encodings, encoding
                )

                if True in matches:
                    best_idx = np.argmin(distances)
                    if matches[best_idx]:
                        name = self.known_names[best_idx]
                        self.logger.debug(
                            f"Face identificada: {name} "
                            f"(distância: {distances[best_idx]:.3f})"
                        )
                        return name

            return None

        except Exception as e:
            self.logger.error(f"Erro no reconhecimento facial: {e}")
            return None

    def capture_for_analysis(self, save_path: str = "/tmp/luna_vision.jpg") -> str | None:
        """
        Captura um frame e salva para análise pelo modelo de visão.

        Args:
            save_path: Onde salvar a imagem temporária.

        Returns:
            Caminho da imagem salva ou None.
        """
        frame = self.capture_frame()
        if frame is None:
            return None

        if self.save_frame(frame, save_path):
            return save_path
        return None

    def describe_scene(self, image_path: str | None = None, question: str = "") -> str:
        """
        Usa o modelo de visão (moondream) para descrever o que a câmera está vendo.

        Args:
            image_path: Caminho para imagem existente. Se None, captura da câmera.
            question: Pergunta específica sobre a imagem.

        Returns:
            Descrição textual da cena ou mensagem de erro.
        """
        if not OLLAMA_AVAILABLE:
            return "Módulo Ollama não disponível para análise de visão."

        if image_path is None:
            image_path = self.capture_for_analysis()
            if image_path is None:
                return "Não consegui capturar imagem da câmera."

        try:
            prompt = question if question else "Descreva detalhadamente o que você vê nesta imagem em português do Brasil. Inclua pessoas, objetos, ambiente e qualquer detalhe relevante."

            client = ollama.Client(host=self.ollama_host)
            response = client.chat(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_path],
                    }
                ],
                options={
                    "num_predict": 300,
                    "temperature": 0.5,
                },
            )

            return response.message.content

        except Exception as e:
            self.logger.error(f"Erro ao analisar imagem com {self.vision_model}: {e}")
            return f"Erro ao analisar imagem: {e}"

    def identify_and_describe(self) -> dict:
        """
        Captura frame, identifica rostos e descreve a cena.

        Combina reconhecimento facial (se disponível) com análise de cena
        via modelo de visão.

        Returns:
            Dicionário com:
                - "identified_person": Nome da pessoa identificada (ou None)
                - "member_info": Info do membro do Membros.txt (ou "")
                - "scene_description": Descrição da cena pelo modelo de visão
                - "image_path": Caminho da imagem capturada
        """
        result = {
            "identified_person": None,
            "member_info": "",
            "scene_description": "",
            "image_path": None,
        }

        # Capturar frame
        frame = self.capture_frame()
        if frame is None:
            result["scene_description"] = "Não consegui acessar a câmera."
            return result

        # Salvar para análise
        save_path = "/tmp/luna_vision.jpg"
        self.save_frame(frame, save_path)
        result["image_path"] = save_path

        # Identificar rosto
        if self.face_rec_enabled:
            identified = self.identify_face(frame)
            if identified:
                result["identified_person"] = identified
                result["member_info"] = self.get_member_info(identified)
                self.logger.info(f"Pessoa identificada: [cyan]{identified}[/]")

        return result

    @property
    def is_available(self) -> bool:
        """Verifica se a visão está funcional."""
        return self.enabled
