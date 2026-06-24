"""
VisionModule — Visão computacional do Alfred.

Funcionalidades:
- Captura de imagens da webcam
- Reconhecimento facial do usuário
- Descrição de cenas via modelo de visão (moondream/llava via Ollama)
"""

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

import numpy as np


class VisionModule:
    """
    Módulo de visão do Alfred — câmera, reconhecimento facial e análise de imagem.
    """

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config.get("vision", {})
        self.logger = logger

        self.enabled = self.config.get("enabled", True) and OPENCV_AVAILABLE
        self.camera_index = self.config.get("camera_index", 0)
        self.face_rec_enabled = (
            self.config.get("face_recognition", True) and FACE_REC_AVAILABLE
        )
        self.faces_dir = self.config.get("faces_dir", "data/faces")

        # Encodings conhecidos (carregados do faces_dir)
        self.known_encodings: list[np.ndarray] = []
        self.known_names: list[str] = []

        if not OPENCV_AVAILABLE:
            self.logger.warning(
                "OpenCV não disponível — visão desativada. "
                "Instale: [cyan]pip install opencv-python[/]"
            )
            self.enabled = False
            return

        if self.face_rec_enabled:
            self._load_known_faces()

        self.logger.info(
            f"Vision inicializado — câmera: [cyan]{self.camera_index}[/], "
            f"rostos conhecidos: [cyan]{len(self.known_names)}[/]"
        )

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

    def capture_for_analysis(self, save_path: str = "/tmp/alfred_vision.jpg") -> str | None:
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

    @property
    def is_available(self) -> bool:
        """Verifica se a visão está funcional."""
        return self.enabled
