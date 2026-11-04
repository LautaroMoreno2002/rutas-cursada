from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import alumno_actual, crear_token, hashear, verificar
from ..database import get_db
from ..models import Alumno, AlumnoMateria, Carrera, Comision, PlanEstudio
from ..schemas import AlumnoOut, AlumnoUpdate, EstadoMateriasIn, LoginIn, RegistroIn, TokenOut
from .carreras import comision_dict, periodo_dict

router = APIRouter(tags=["alumnos"])


@router.post("/auth/registro", response_model=TokenOut, status_code=201)
def registro(datos: RegistroIn, db: Session = Depends(get_db)):
    if db.scalar(select(Alumno).where(Alumno.email == datos.email)):
        raise HTTPException(409, "Ya existe una cuenta con ese email")
    if datos.carrera_id and not db.get(Carrera, datos.carrera_id):
        raise HTTPException(404, "Carrera no encontrada")
    alumno = Alumno(nombre=datos.nombre.strip(), email=datos.email, password_hash=hashear(datos.password),
                    carrera_id=datos.carrera_id)
    db.add(alumno)
    db.commit()
    return {"token": crear_token(alumno.id), "alumno": alumno}


@router.post("/auth/login", response_model=TokenOut)
def login(datos: LoginIn, db: Session = Depends(get_db)):
    alumno = db.scalar(select(Alumno).where(Alumno.email == datos.email.strip().lower()))
    if alumno is None or not verificar(datos.password, alumno.password_hash):
        raise HTTPException(401, "Email o contraseña incorrectos")
    return {"token": crear_token(alumno.id), "alumno": alumno}


@router.get("/me", response_model=AlumnoOut)
def yo(alumno: Alumno = Depends(alumno_actual)):
    return alumno


@router.put("/me", response_model=AlumnoOut)
def actualizar_yo(datos: AlumnoUpdate, alumno: Alumno = Depends(alumno_actual), db: Session = Depends(get_db)):
    alumno = db.merge(alumno)
    if datos.nombre:
        alumno.nombre = datos.nombre.strip()
    if datos.carrera_id is not None and datos.carrera_id != alumno.carrera_id:
        if not db.get(Carrera, datos.carrera_id):
            raise HTTPException(404, "Carrera no encontrada")
        alumno.carrera_id = datos.carrera_id
        alumno.materias.clear()  # el progreso es por carrera
    db.commit()
    return alumno


@router.get("/me/materias")
def mis_materias(alumno: Alumno = Depends(alumno_actual)):
    return [
        {"plan_id": am.plan_id, "estado": am.estado, "nota": am.nota, "comision_id": am.comision_id}
        for am in alumno.materias
    ]


@router.put("/me/materias")
def guardar_materias(datos: EstadoMateriasIn, alumno: Alumno = Depends(alumno_actual), db: Session = Depends(get_db)):
    alumno = db.merge(alumno)
    if not alumno.carrera_id:
        raise HTTPException(400, "Primero elegí tu carrera")
    plan = {p.id: p for p in db.scalars(select(PlanEstudio).where(PlanEstudio.carrera_id == alumno.carrera_id))}
    actuales = {am.plan_id: am for am in alumno.materias}

    for item in datos.materias:
        p = plan.get(item.plan_id)
        if p is None:
            raise HTTPException(400, f"La materia {item.plan_id} no pertenece a tu carrera")
        comision_id = item.comision_id if item.estado == "cursando" else None
        if comision_id:
            c = db.get(Comision, comision_id)
            if c is None or c.materia_id != p.materia_id:
                raise HTTPException(400, f"La comisión no corresponde a {p.materia.nombre}")
        am = actuales.get(item.plan_id)
        if item.estado == "pendiente":
            if am is not None:
                alumno.materias.remove(am)
            continue
        if am is None:
            am = AlumnoMateria(plan_id=item.plan_id)
            alumno.materias.append(am)
            actuales[item.plan_id] = am
        am.estado = item.estado
        am.nota = item.nota if item.estado == "aprobada" else None
        am.comision_id = comision_id
    db.commit()
    return mis_materias(alumno)


@router.get("/me/cursando")
def mi_cursada(alumno: Alumno = Depends(alumno_actual), db: Session = Depends(get_db)):
    """Materias que el alumno está cursando, con su comisión y cuántos compañeros la cursan."""
    alumno = db.merge(alumno)
    resultado = []
    for am in alumno.materias:
        if am.estado != "cursando":
            continue
        plan = db.get(PlanEstudio, am.plan_id)
        item = {"plan_id": am.plan_id, "materia": plan.materia.nombre, "comision": None, "periodo": None}
        if am.comision_id:
            c = db.get(Comision, am.comision_id)
            total = db.scalar(select(func.count()).select_from(AlumnoMateria).where(
                AlumnoMateria.comision_id == c.id, AlumnoMateria.estado == "cursando"))
            item["comision"] = comision_dict(c, total)
            item["periodo"] = periodo_dict(c.periodo)
        resultado.append(item)
    return resultado
