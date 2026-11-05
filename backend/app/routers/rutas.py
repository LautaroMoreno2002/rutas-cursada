from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth import alumno_opcional
from ..database import get_db
from ..models import Alumno, Carrera
from ..schemas import ParametrosIn
from ..services.excel import rutas_a_excel
from ..services.horarios import DIAS, fmt_hora
from ..services.planificador import Parametros
from ..services.rutas import estado_alumno, generar_rutas, proximo_semestre

router = APIRouter(tags=["rutas"])


def _calcular(datos: ParametrosIn, alumno: Alumno | None, db: Session):
    carrera_id = datos.carrera_id or (alumno.carrera_id if alumno else None)
    if not carrera_id:
        raise HTTPException(400, "Indicá la carrera")
    carrera = db.get(Carrera, carrera_id)
    if carrera is None:
        raise HTTPException(404, "Carrera no encontrada")

    if alumno is not None and alumno.carrera_id == carrera.id:
        aprobadas, cursando = estado_alumno(alumno)
    else:
        aprobadas, cursando = set(), set()
    if datos.aprobadas is not None:
        aprobadas = set(datos.aprobadas)
    if datos.cursando is not None:
        cursando = set(datos.cursando)

    anio, sem = proximo_semestre()
    disponibilidad = None
    if datos.disponibilidad is not None:
        disponibilidad = {}
        for f in datos.disponibilidad:
            a, b = f.minutos()
            if b > a:
                disponibilidad.setdefault(f.dia, []).append((a, b))

    objetivo = round(datos.objetivo_anios * 2) if datos.objetivo_anios else None
    params = Parametros(
        anio_inicio=datos.anio_inicio or anio,
        semestre_inicio=datos.semestre_inicio or sem,
        max_materias=datos.max_materias,
        max_horas=datos.max_horas,
        disponibilidad=disponibilidad,
        turno_preferido=datos.turno_preferido,
        cantidad_rutas=datos.cantidad_rutas,
        objetivo_semestres=objetivo,
        asumir_cursando_aprobadas=datos.asumir_cursando_aprobadas,
        incluir_sin_oferta=datos.incluir_sin_oferta,
    )
    planificador, rutas = generar_rutas(db, carrera, aprobadas, cursando, params)

    if alumno is not None:  # recordar los últimos parámetros usados
        alumno = db.merge(alumno)
        alumno.preferencias = datos.model_dump(exclude={"aprobadas", "cursando", "carrera_id"})
        db.commit()

    rutas_dict = [r.to_dict() for r in rutas]
    for r in rutas_dict:
        r["cumple_objetivo"] = None if objetivo is None else (r["completa"] and r["cantidad_semestres"] <= objetivo)
    return carrera, params, planificador, rutas_dict


@router.post("/rutas")
def calcular_rutas(datos: ParametrosIn, alumno: Alumno | None = Depends(alumno_opcional),
                   db: Session = Depends(get_db)):
    carrera, params, planificador, rutas = _calcular(datos, alumno, db)
    return {
        "carrera": {"id": carrera.id, "nombre": carrera.nombre},
        "inicio": {"anio": params.anio_inicio, "semestre": params.semestre_inicio},
        "pendientes": len(planificador.pendientes_iniciales),
        "minimo_teorico_semestres": planificador.minimo_teorico(),
        "objetivo_semestres": params.objetivo_semestres,
        "rutas": rutas,
    }


def _texto_disponibilidad(params: Parametros) -> str:
    if not params.disponibilidad:
        return "Cualquier día y horario"
    return "; ".join(
        f"{DIAS[d][:3]} " + ", ".join(f"{fmt_hora(a)}-{fmt_hora(b)}" for a, b in rangos)
        for d, rangos in sorted(params.disponibilidad.items())
    )


@router.post("/rutas/excel")
def exportar_rutas(datos: ParametrosIn, alumno: Alumno | None = Depends(alumno_opcional),
                   db: Session = Depends(get_db)):
    carrera, params, planificador, rutas = _calcular(datos, alumno, db)
    turnos = {"manana": "Mañana", "tarde": "Tarde", "noche": "Noche"}
    contexto = {
        "Carrera": carrera.nombre,
        "Alumno": alumno.nombre if alumno else "-",
        "Generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Inicio": f"{params.semestre_inicio}° semestre {params.anio_inicio}",
        "Materias pendientes": len(planificador.pendientes_iniciales),
        "Máx. materias por semestre": params.max_materias,
        "Máx. horas semanales": params.max_horas or "-",
        "Turno preferido": turnos.get(params.turno_preferido, "-"),
        "Disponibilidad": _texto_disponibilidad(params),
        "Mínimo teórico (por correlativas)": f"{planificador.minimo_teorico()} semestres",
    }
    contenido = rutas_a_excel(rutas, contexto)
    nombre = f"rutas_{carrera.nombre.lower().replace(' ', '_')[:40]}.xlsx"
    return Response(
        contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
