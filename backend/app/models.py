"""Modelo de datos (basado en el diseño de dbdiagram.io de la rama base-de-datos).

carrera ─< plan_estudio >─ materia
plan_estudio ─< correlativa >─ plan_estudio
carrera ─< itinerario ─< itinerario_semestre ─< itinerario_materia >─ plan_estudio
periodo ─< comision >─ materia ;  comision ─< horario_comision
alumno ─< alumno_materia >─ plan_estudio  (estado: pendiente/cursando/aprobada, comisión si cursa)
"""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Integer, SmallInteger, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

ESTADOS_MATERIA = ("pendiente", "cursando", "aprobada")


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Carrera(Base):
    __tablename__ = "carrera"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), unique=True)
    titulo_oficial: Mapped[str | None] = mapped_column(String(255))
    url_plan_estudios: Mapped[str | None] = mapped_column(String(500))
    duracion: Mapped[str | None] = mapped_column(String(60))
    modalidad: Mapped[str | None] = mapped_column(String(60))
    ambitos_desempeno: Mapped[list | None] = mapped_column(JSON)
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=ahora, onupdate=ahora)

    plan: Mapped[list["PlanEstudio"]] = relationship(back_populates="carrera", cascade="all, delete-orphan")
    itinerarios: Mapped[list["Itinerario"]] = relationship(back_populates="carrera", cascade="all, delete-orphan")


class Materia(Base):
    """Materia única (puede estar en el plan de varias carreras)."""
    __tablename__ = "materia"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str | None] = mapped_column(String(20), unique=True)  # código de actividad del PDF (ej. A0075)
    nombre: Mapped[str] = mapped_column(String(255))
    nombre_normalizado: Mapped[str] = mapped_column(String(255), unique=True)


class PlanEstudio(Base):
    __tablename__ = "plan_estudio"
    __table_args__ = (UniqueConstraint("carrera_id", "materia_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    carrera_id: Mapped[int] = mapped_column(ForeignKey("carrera.id", ondelete="CASCADE"))
    materia_id: Mapped[int] = mapped_column(ForeignKey("materia.id"))
    orden: Mapped[int] = mapped_column(Integer, default=0)
    regimen: Mapped[str | None] = mapped_column(String(40))  # Semestral / Anual
    carga_horaria_semanal: Mapped[float | None] = mapped_column(Float)
    carga_horaria_total: Mapped[float | None] = mapped_column(Float)
    otro_requisito: Mapped[bool] = mapped_column(Boolean, default=False)  # inglés, utilitarios, etc.
    correlativas_texto: Mapped[list | None] = mapped_column(JSON)  # texto original scrapeado
    correlativas_sin_match: Mapped[list | None] = mapped_column(JSON)  # nombres que no se pudieron vincular

    carrera: Mapped[Carrera] = relationship(back_populates="plan")
    materia: Mapped[Materia] = relationship(lazy="joined")
    correlativas: Mapped[list["Correlativa"]] = relationship(
        foreign_keys="Correlativa.plan_id", cascade="all, delete-orphan", back_populates="plan"
    )

    @property
    def es_anual(self) -> bool:
        return bool(self.regimen and "anual" in self.regimen.lower())


class Correlativa(Base):
    __tablename__ = "correlativa"
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan_estudio.id", ondelete="CASCADE"), primary_key=True)
    requiere_plan_id: Mapped[int] = mapped_column(ForeignKey("plan_estudio.id", ondelete="CASCADE"), primary_key=True)
    plan: Mapped[PlanEstudio] = relationship(foreign_keys=[plan_id], back_populates="correlativas")
    requiere: Mapped[PlanEstudio] = relationship(foreign_keys=[requiere_plan_id])


class Itinerario(Base):
    __tablename__ = "itinerario"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    carrera_id: Mapped[int] = mapped_column(ForeignKey("carrera.id", ondelete="CASCADE"))
    titulo: Mapped[str] = mapped_column(String(255))
    semestre_inicio: Mapped[int] = mapped_column(SmallInteger, default=1)
    carrera: Mapped[Carrera] = relationship(back_populates="itinerarios")
    semestres: Mapped[list["ItinerarioSemestre"]] = relationship(
        cascade="all, delete-orphan", order_by="ItinerarioSemestre.orden"
    )


class ItinerarioSemestre(Base):
    __tablename__ = "itinerario_semestre"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    itinerario_id: Mapped[int] = mapped_column(ForeignKey("itinerario.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(SmallInteger)
    anio: Mapped[int] = mapped_column(SmallInteger)
    semestre: Mapped[int] = mapped_column(SmallInteger)
    materias: Mapped[list["ItinerarioMateria"]] = relationship(cascade="all, delete-orphan")


class ItinerarioMateria(Base):
    __tablename__ = "itinerario_materia"
    itinerario_semestre_id: Mapped[int] = mapped_column(
        ForeignKey("itinerario_semestre.id", ondelete="CASCADE"), primary_key=True
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan_estudio.id", ondelete="CASCADE"), primary_key=True)


class Periodo(Base):
    __tablename__ = "periodo"
    __table_args__ = (UniqueConstraint("anio", "semestre"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anio: Mapped[int] = mapped_column(SmallInteger)
    semestre: Mapped[int] = mapped_column(SmallInteger)
    titulo: Mapped[str | None] = mapped_column(String(255))
    definido: Mapped[bool] = mapped_column(Boolean, default=False)  # True = tiene aulas/docentes
    fuente: Mapped[str | None] = mapped_column(String(500))
    importado: Mapped[datetime] = mapped_column(DateTime, default=ahora, onupdate=ahora)
    comisiones: Mapped[list["Comision"]] = relationship(back_populates="periodo", cascade="all, delete-orphan")

    @property
    def nombre(self) -> str:
        return f"{self.semestre}° semestre {self.anio}"


class Comision(Base):
    __tablename__ = "comision"
    __table_args__ = (UniqueConstraint("periodo_id", "materia_id", "nombre"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo.id", ondelete="CASCADE"))
    materia_id: Mapped[int] = mapped_column(ForeignKey("materia.id"))
    nombre: Mapped[str] = mapped_column(String(40))
    docentes: Mapped[list | None] = mapped_column(JSON)
    modalidad: Mapped[str | None] = mapped_column(String(60))
    inicio_dictado: Mapped[str | None] = mapped_column(String(30))
    fin_dictado: Mapped[str | None] = mapped_column(String(30))
    instancia: Mapped[str | None] = mapped_column(String(60))

    periodo: Mapped[Periodo] = relationship(back_populates="comisiones")
    materia: Mapped[Materia] = relationship(lazy="joined")
    horarios: Mapped[list["HorarioComision"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="HorarioComision.dia"
    )


class HorarioComision(Base):
    __tablename__ = "horario_comision"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comision_id: Mapped[int] = mapped_column(ForeignKey("comision.id", ondelete="CASCADE"))
    dia: Mapped[int | None] = mapped_column(SmallInteger)  # 1=Lunes ... 6=Sábado, 7=Domingo
    hora_desde: Mapped[int | None] = mapped_column(SmallInteger)  # minutos desde 00:00
    hora_hasta: Mapped[int | None] = mapped_column(SmallInteger)
    dia_texto: Mapped[str | None] = mapped_column(String(30))
    horario_texto: Mapped[str | None] = mapped_column(String(60))
    tipo_clase: Mapped[str | None] = mapped_column(String(60))
    aula: Mapped[str | None] = mapped_column(String(60))
    edificacion: Mapped[str | None] = mapped_column(String(100))
    compartido_con: Mapped[str | None] = mapped_column(String(255))


class Alumno(Base):
    __tablename__ = "alumno"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(190), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    carrera_id: Mapped[int | None] = mapped_column(ForeignKey("carrera.id", ondelete="SET NULL"))
    preferencias: Mapped[dict | None] = mapped_column(JSON)  # últimos parámetros usados en el planificador
    creado: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    carrera: Mapped[Carrera | None] = relationship()
    materias: Mapped[list["AlumnoMateria"]] = relationship(cascade="all, delete-orphan")


class AlumnoMateria(Base):
    __tablename__ = "alumno_materia"
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumno.id", ondelete="CASCADE"), primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan_estudio.id", ondelete="CASCADE"), primary_key=True)
    estado: Mapped[str] = mapped_column(String(15), default="pendiente")
    nota: Mapped[float | None] = mapped_column(Float)
    comision_id: Mapped[int | None] = mapped_column(ForeignKey("comision.id", ondelete="SET NULL"))
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=ahora, onupdate=ahora)

    comision: Mapped[Comision | None] = relationship()
