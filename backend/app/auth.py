from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import Alumno

_bearer = HTTPBearer(auto_error=False)


def hashear(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verificar(password: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hash_.encode())
    except ValueError:
        return False


def crear_token(alumno_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXP_HORAS)
    return jwt.encode({"sub": str(alumno_id), "exp": exp}, config.JWT_SECRET, algorithm="HS256")


def _alumno_desde_token(cred: HTTPAuthorizationCredentials | None, db: Session) -> Alumno | None:
    if cred is None:
        return None
    try:
        datos = jwt.decode(cred.credentials, config.JWT_SECRET, algorithms=["HS256"])
        return db.get(Alumno, int(datos["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def alumno_actual(cred=Depends(_bearer), db: Session = Depends(get_db)) -> Alumno:
    alumno = _alumno_desde_token(cred, db)
    if alumno is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o vencida")
    return alumno


def alumno_opcional(cred=Depends(_bearer), db: Session = Depends(get_db)) -> Alumno | None:
    return _alumno_desde_token(cred, db)


def solo_admin(x_admin_token: str | None = Header(default=None)):
    if not config.ADMIN_TOKEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administración deshabilitada: definí ADMIN_TOKEN en el .env")
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token de administración inválido")
