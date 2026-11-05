from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config


class Base(DeclarativeBase):
    pass


def crear_engine(url: str | None = None):
    url = url or config.DATABASE_URL
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # SQLite no valida FKs por defecto
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return engine


engine = crear_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def crear_tablas(eng=None):
    from . import models  # noqa: F401  (registra los modelos)
    Base.metadata.create_all(eng or engine)
