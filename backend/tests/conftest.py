import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = tempfile.mkdtemp(prefix="rutas_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["DATA_DIR"] = _TMP
os.environ["ADMIN_TOKEN"] = "secreto-admin"
os.environ["JWT_SECRET"] = "clave-de-prueba-suficientemente-larga-123"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cli import DEMO  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.services.importador import cargar_json, importar_carreras, importar_periodo  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def db_demo(db):
    importar_carreras(db, cargar_json(DEMO / "carreras.json"))
    for f in sorted(DEMO.glob("periodo_*.json")):
        importar_periodo(db, cargar_json(f))
    return db


@pytest.fixture()
def tmp_dir():
    return Path(tempfile.mkdtemp(dir=_TMP))
