"""
Carregamento de configuração do Alfred.
Lê o arquivo YAML e disponibiliza como dicionário.
"""

import os
import yaml
from pathlib import Path


# Diretório raiz do projeto (onde fica o README, requirements, etc.)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_config(config_path: str | None = None) -> dict:
    """
    Carrega a configuração do Alfred a partir de um arquivo YAML.

    Args:
        config_path: Caminho para o arquivo de configuração.
                     Se None, procura em config/config.yaml.

    Returns:
        Dicionário com a configuração.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
    """
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuração não encontrada: {config_path}")

    # Tentar múltiplos encodings — o install.bat no Windows pode gerar
    # o arquivo em CP1252/Latin-1 ao invés de UTF-8
    config = None
    used_encoding = "utf-8"
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            with open(config_path, "r", encoding=encoding) as f:
                config = yaml.safe_load(f)
            used_encoding = encoding
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if config is None:
        # Último recurso: ler ignorando erros de encoding
        with open(config_path, "r", encoding="utf-8", errors="replace") as f:
            config = yaml.safe_load(f)
        used_encoding = "utf-8-replace"

    # Se leu com encoding não-UTF-8, re-salvar como UTF-8 para evitar
    # o mesmo problema no futuro
    if used_encoding != "utf-8":
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        except Exception:
            pass  # Não é crítico — o config já foi carregado

    # Expandir ~ nos caminhos de ações permitidas
    if "actions" in config and "allowed_paths" in config["actions"]:
        config["actions"]["allowed_paths"] = [
            os.path.expanduser(p) for p in config["actions"]["allowed_paths"]
        ]

    # Expandir caminho do banco de memória
    if "memory" in config and "db_path" in config["memory"]:
        db_path = config["memory"]["db_path"]
        if not os.path.isabs(db_path):
            config["memory"]["db_path"] = str(PROJECT_ROOT / db_path)

    # Expandir caminho das faces
    if "vision" in config and "faces_dir" in config["vision"]:
        faces_dir = config["vision"]["faces_dir"]
        if not os.path.isabs(faces_dir):
            config["vision"]["faces_dir"] = str(PROJECT_ROOT / faces_dir)

    return config
