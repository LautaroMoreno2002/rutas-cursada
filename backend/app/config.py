import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _database_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    host = os.getenv("DB_HOST")
    if host:
        user = quote_plus(os.getenv("DB_USER", "root"))
        pwd = quote_plus(os.getenv("DB_PASSWORD", ""))
        port = os.getenv("DB_PORT", "3306")
        name = os.getenv("DB_NAME", "rutas_cursada")
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}?charset=utf8mb4"
    # Sin MySQL configurado: SQLite local para desarrollo
    return f"sqlite:///{DATA_DIR / 'rutas_cursada.db'}"


DATABASE_URL = _database_url()
JWT_SECRET = os.getenv("JWT_SECRET", "cambiar-este-secreto-en-produccion")
JWT_EXP_HORAS = int(os.getenv("JWT_EXP_HORAS", "72"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
