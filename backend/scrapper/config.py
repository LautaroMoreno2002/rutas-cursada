"""Lectura centralizada de variables de entorno del scraper (con valores por defecto)."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Busca el .env en backend/ y en la raíz del repo
_BACKEND = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND / ".env")
load_dotenv(_BACKEND.parent / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", _BACKEND / "data"))


def env_str(nombre: str, defecto: str = "") -> str:
    valor = os.getenv(nombre)
    return valor.strip() if valor and valor.strip() else defecto


def env_int(nombre: str, defecto: int) -> int:
    try:
        return int(os.getenv(nombre, defecto))
    except (TypeError, ValueError):
        return defecto


def ruta(nombre_env: str, archivo_defecto: str) -> Path:
    """Ruta de un archivo de datos; crea la carpeta si no existe."""
    p = Path(env_str(nombre_env, str(DATA_DIR / archivo_defecto)))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


MAX_RETRIES = env_int("MAX_RETRIES", 5)
INITIAL_DELAY = env_int("INITIAL_DELAY", 3)
DELAY_BETWEEN_CAREERS = env_int("DELAY_BETWEEN_CAREERS", 15)
URL_BASE = env_str("URL_BASE").rstrip("/")
URL_CARRERAS = env_str("URL_CARRERAS")
URL_PERIODO = env_str("URL_PERIODO")
