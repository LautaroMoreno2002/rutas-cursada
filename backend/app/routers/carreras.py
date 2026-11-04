from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AlumnoMateria, Carrera, Comision, Periodo
from ..services.horarios import DIAS, fmt_rango, turno_de

router = APIRouter(tags=["carreras y oferta"])


def periodo_en_curso(hoy: date | None = None) -> tuple[int, int]:
    hoy = hoy or date.today()
    if hoy.month <= 2:
        return hoy.year - 1, 2
    return (hoy.year, 1) if hoy.month <= 7 else (hoy.year, 2)


def periodo_por_defecto(db: Session) -> Periodo | None:
    anio, sem = periodo_en_curso()
    actual = db.scalar(select(Periodo).where(Periodo.anio == anio, Periodo.semestre == sem))
    return actual or db.scalar(select(Periodo).order_by(Periodo.anio.desc(), Periodo.semestre.desc()))


def periodo_dict(p: Periodo, comisiones: int | None = None) -> dict:
    d = {"id": p.id, "anio": p.anio, "semestre": p.semestre, "nombre": p.nombre, "titulo": p.titulo,
         "definido": p.definido, "importado": p.importado.isoformat() if p.importado else None}
    if comisiones is not None:
        d["comisiones"] = comisiones
    return d


def comision_dict(c: Comision, cursando: int = 0) -> dict:
    horarios = []
    for h in c.horarios:
        horarios.append({
            "dia": h.dia, "dia_nombre": DIAS.get(h.dia, h.dia_texto or ""), "desde": h.hora_desde,
            "hasta": h.hora_hasta, "rango": fmt_rango(h.hora_desde, h.hora_hasta) or (h.horario_texto or ""),
            "turno": turno_de(h.hora_desde, h.hora_hasta) if h.hora_desde is not None else None,
            "aula": h.aula, "edificacion": h.edificacion, "tipo_clase": h.tipo_clase,
            "compartido_con": h.compartido_con,
        })
    return {"id": c.id, "nombre": c.nombre, "docentes": c.docentes or [], "modalidad": c.modalidad,
            "inicio_dictado": c.inicio_dictado, "fin_dictado": c.fin_dictado, "horarios": horarios,
            "cursando": cursando}


def _carrera(db: Session, carrera_id: int) -> Carrera:
    carrera = db.get(Carrera, carrera_id)
    if carrera is None:
        raise HTTPException(404, "Carrera no encontrada")
    return carrera


@router.get("/carreras")
def listar_carreras(db: Session = Depends(get_db)):
    carreras = db.scalars(select(Carrera).order_by(Carrera.nombre)).all()
    return [
        {"id": c.id, "nombre": c.nombre, "titulo_oficial": c.titulo_oficial, "duracion": c.duracion,
         "modalidad": c.modalidad, "cantidad_materias": len(c.plan)}
        for c in carreras
    ]


@router.get("/carreras/{carrera_id}")
def detalle_carrera(carrera_id: int, db: Session = Depends(get_db)):
    carrera = _carrera(db, carrera_id)
    sugerido = {}
    itinerarios = []
    for it in sorted(carrera.itinerarios, key=lambda i: i.semestre_inicio):
        semestres = []
        for s in it.semestres:
            ids = [im.plan_id for im in s.materias]
            semestres.append({"orden": s.orden, "anio": s.anio, "semestre": s.semestre, "plan_ids": ids})
            if it.semestre_inicio == min(i.semestre_inicio for i in carrera.itinerarios):
                for pid in ids:
                    sugerido.setdefault(pid, s.orden)
        itinerarios.append({"id": it.id, "titulo": it.titulo, "semestre_inicio": it.semestre_inicio,
                            "semestres": semestres})

    plan = [
        {
            "plan_id": p.id, "materia_id": p.materia_id, "nombre": p.materia.nombre, "codigo": p.materia.codigo,
            "regimen": p.regimen, "anual": p.es_anual, "horas": p.carga_horaria_semanal,
            "carga_total": p.carga_horaria_total, "otro_requisito": p.otro_requisito,
            "correlativas": [c.requiere_plan_id for c in p.correlativas],
            "correlativas_sin_match": p.correlativas_sin_match or [],
            "semestre_sugerido": sugerido.get(p.id),
        }
        for p in sorted(carrera.plan, key=lambda p: p.orden)
    ]
    return {
        "id": carrera.id, "nombre": carrera.nombre, "titulo_oficial": carrera.titulo_oficial,
        "duracion": carrera.duracion, "modalidad": carrera.modalidad, "url": carrera.url_plan_estudios,
        "ambitos_desempeno": carrera.ambitos_desempeno or [], "plan": plan, "itinerarios": itinerarios,
    }


@router.get("/carreras/{carrera_id}/oferta")
def oferta_carrera(carrera_id: int, periodo_id: int | None = None, db: Session = Depends(get_db)):
    carrera = _carrera(db, carrera_id)
    periodo = db.get(Periodo, periodo_id) if periodo_id else periodo_por_defecto(db)
    if periodo is None:
        return {"periodo": None, "materias": []}

    plan_por_materia = {p.materia_id: p for p in carrera.plan}
    conteo = dict(db.execute(
        select(AlumnoMateria.comision_id, func.count())
        .where(AlumnoMateria.estado == "cursando", AlumnoMateria.comision_id.is_not(None))
        .group_by(AlumnoMateria.comision_id)
    ).all())

    materias: dict[int, dict] = {}
    for c in sorted(periodo.comisiones, key=lambda c: c.nombre):
        plan = plan_por_materia.get(c.materia_id)
        if plan is None:
            continue
        m = materias.setdefault(plan.id, {
            "plan_id": plan.id, "materia": plan.materia.nombre, "codigo": plan.materia.codigo,
            "horas": plan.carga_horaria_semanal, "orden": plan.orden, "comisiones": [],
        })
        m["comisiones"].append(comision_dict(c, conteo.get(c.id, 0)))
    lista = sorted(materias.values(), key=lambda m: m["orden"])
    return {"periodo": periodo_dict(periodo), "materias": lista}


@router.get("/periodos")
def listar_periodos(db: Session = Depends(get_db)):
    filas = db.execute(
        select(Periodo, func.count(Comision.id))
        .outerjoin(Comision, Comision.periodo_id == Periodo.id)
        .group_by(Periodo.id)
        .order_by(Periodo.anio.desc(), Periodo.semestre.desc())
    ).all()
    actual = periodo_por_defecto(db)
    return {"actual_id": actual.id if actual else None,
            "periodos": [periodo_dict(p, n) for p, n in filas]}
