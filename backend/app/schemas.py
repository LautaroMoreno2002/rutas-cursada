import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EstadoMateria = Literal["pendiente", "cursando", "aprobada"]
Turno = Literal["manana", "tarde", "noche"]


# ---------------------------------------------------------------- auth / alumno
class RegistroIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=190)
    password: str = Field(min_length=6, max_length=72)
    carrera_id: int | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("Email inválido")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


class AlumnoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    email: str
    carrera_id: int | None
    preferencias: dict | None = None


class TokenOut(BaseModel):
    token: str
    alumno: AlumnoOut


class AlumnoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    carrera_id: int | None = None


class EstadoMateriaIn(BaseModel):
    plan_id: int
    estado: EstadoMateria
    nota: float | None = Field(default=None, ge=0, le=10)
    comision_id: int | None = None


class EstadoMateriasIn(BaseModel):
    materias: list[EstadoMateriaIn]


# ---------------------------------------------------------------- planificador
class FranjaIn(BaseModel):
    dia: int = Field(ge=1, le=7)
    desde: str = Field(pattern=r"^\d{1,2}:\d{2}$")
    hasta: str = Field(pattern=r"^\d{1,2}:\d{2}$")

    def minutos(self) -> tuple[int, int]:
        h1, m1 = map(int, self.desde.split(":"))
        h2, m2 = map(int, self.hasta.split(":"))
        return h1 * 60 + m1, h2 * 60 + m2


class ParametrosIn(BaseModel):
    carrera_id: int | None = None
    # Si no se envían se usa lo registrado por el alumno logueado
    aprobadas: list[int] | None = None
    cursando: list[int] | None = None

    anio_inicio: int | None = Field(default=None, ge=2000, le=2100)
    semestre_inicio: Literal[1, 2] | None = None
    max_materias: int = Field(default=4, ge=1, le=10)
    max_horas: float | None = Field(default=None, gt=0, le=80)
    disponibilidad: list[FranjaIn] | None = None  # None = cualquier día y horario
    turno_preferido: Turno | None = None
    trabaja: bool = False  # informativo (el front lo usa para precargar la disponibilidad)
    objetivo_anios: float | None = Field(default=None, gt=0, le=15)
    cantidad_rutas: int = Field(default=4, ge=1, le=8)
    asumir_cursando_aprobadas: bool = True
    incluir_sin_oferta: bool = True
