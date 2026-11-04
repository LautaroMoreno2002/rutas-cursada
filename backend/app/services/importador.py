"""Carga en la base los JSON que generan los scrapers.

* carreras.json            -> carrera, materia, plan_estudio, correlativa, itinerario*
* materias_del_periodo.json -> periodo, comision, horario_comision

Las importaciones son idempotentes: se pueden volver a correr cuando cambia el PDF
(por ejemplo, cuando el período pasa de "no definido" a "definido" con aulas).
"""
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Carrera, Comision, Correlativa, HorarioComision, Itinerario, ItinerarioMateria,
    ItinerarioSemestre, Materia, Periodo, PlanEstudio,
)
from .horarios import parsear_dia, parsear_horario
from .texto import IndiceNombres, normalizar


def _num(valor) -> float | None:
    if valor is None:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", str(valor))
    return float(m.group().replace(",", ".")) if m else None


def _lista_correlativas(valor) -> list[str]:
    if isinstance(valor, list):
        return [str(v).strip() for v in valor if str(v).strip()]
    if not valor or "no tiene" in str(valor).lower():
        return []
    return [p.strip() for p in re.split(r"[,;]", str(valor)) if p.strip()]


def _cortar(valor, largo):
    if valor is None:
        return None
    s = str(valor).strip()
    return s[:largo] if s else None


class _Materias:
    """Cache de materias por código y por nombre para no duplicarlas."""

    def __init__(self, db: Session):
        self.db = db
        self.por_codigo: dict[str, Materia] = {}
        self.por_id: dict[int, Materia] = {}
        self.indice = IndiceNombres()
        for m in db.scalars(select(Materia)):
            self._registrar(m)

    def _registrar(self, m: Materia):
        self.por_id[m.id] = m
        if m.codigo:
            self.por_codigo[m.codigo.upper()] = m
        self.indice.agregar(m.nombre, m.id)

    def obtener(self, nombre: str, codigo: str | None = None, crear: bool = True) -> Materia | None:
        codigo = (codigo or "").strip().upper() or None
        if codigo and codigo in self.por_codigo:
            return self.por_codigo[codigo]
        mid = self.indice.buscar(nombre)
        if mid is not None:
            m = self.por_id[mid]
            if codigo and not m.codigo:
                m.codigo = codigo
                self.por_codigo[codigo] = m
            return m
        if not crear:
            return None
        m = Materia(nombre=nombre.strip(), nombre_normalizado=normalizar(nombre)[:255], codigo=codigo)
        self.db.add(m)
        self.db.flush()
        self._registrar(m)
        return m


def importar_carreras(db: Session, carreras: list[dict]) -> dict:
    materias = _Materias(db)
    resumen = {"carreras": 0, "materias_plan": 0, "correlativas": 0, "correlativas_sin_match": []}

    for data in carreras:
        nombre = (data.get("carrera") or "").strip()
        if not nombre or not data.get("plan_estudios"):
            continue
        carrera = db.scalar(select(Carrera).where(Carrera.nombre == nombre))
        if carrera is None:
            carrera = Carrera(nombre=nombre)
            db.add(carrera)
        carrera.titulo_oficial = _cortar(data.get("titulo_oficial"), 255)
        carrera.url_plan_estudios = _cortar(data.get("url_plan_estudios"), 500)
        carrera.duracion = _cortar(data.get("duracion"), 60)
        carrera.modalidad = _cortar(data.get("modalidad"), 60)
        carrera.ambitos_desempeno = data.get("ambitos_desempeno") or []
        db.flush()

        existentes = {p.materia_id: p for p in carrera.plan}
        vigentes: dict[int, PlanEstudio] = {}
        for orden, item in enumerate(data["plan_estudios"]):
            materia = materias.obtener(item["asignatura"])
            plan = existentes.get(materia.id) or vigentes.get(materia.id)
            if plan is None:
                plan = PlanEstudio(carrera=carrera, materia=materia)
                db.add(plan)
            plan.orden = orden
            plan.regimen = _cortar(item.get("regimen_de_cursada"), 40)
            plan.carga_horaria_semanal = _num(item.get("carga_horaria_semanal"))
            plan.carga_horaria_total = _num(item.get("carga_horaria_total", item.get("carg_horaria_total")))
            plan.otro_requisito = bool(item.get("otro_requisito"))
            plan.correlativas_texto = _lista_correlativas(item.get("correlativas"))
            vigentes[materia.id] = plan
        for materia_id, plan in existentes.items():
            if materia_id not in vigentes:
                db.delete(plan)
        db.flush()

        # Correlativas: se resuelven contra el plan de ESTA carrera
        indice_plan = IndiceNombres({p.materia.nombre: p.id for p in vigentes.values()})
        for plan in vigentes.values():
            plan.correlativas.clear()
        db.flush()
        for plan in vigentes.values():
            sin_match, vistos = [], set()
            for texto in plan.correlativas_texto or []:
                req_id = indice_plan.buscar(texto)
                if req_id is None or req_id == plan.id:
                    sin_match.append(texto)
                elif req_id not in vistos:
                    vistos.add(req_id)
                    plan.correlativas.append(Correlativa(requiere_plan_id=req_id))
                    resumen["correlativas"] += 1
            plan.correlativas_sin_match = sin_match
            resumen["correlativas_sin_match"] += [f"{plan.materia.nombre} -> {s}" for s in sin_match]

        # Itinerarios: se reemplazan completos
        for it in list(carrera.itinerarios):
            db.delete(it)
        db.flush()
        for it_data in data.get("itinerario") or []:
            semestres = it_data.get("semestres") or []
            it = Itinerario(
                carrera=carrera,
                titulo=_cortar(it_data.get("itinerario_titulo"), 255) or "Itinerario",
                semestre_inicio=semestres[0].get("semestre", 1) if semestres else 1,
            )
            db.add(it)
            for s in semestres:
                sem = ItinerarioSemestre(
                    orden=s.get("orden", 0), anio=s.get("año", s.get("anio", 1)), semestre=s.get("semestre", 1)
                )
                it.semestres.append(sem)
                vistos = set()
                for nombre_m in s.get("materias", []):
                    pid = indice_plan.buscar(nombre_m)
                    if pid and pid not in vistos:
                        vistos.add(pid)
                        sem.materias.append(ItinerarioMateria(plan_id=pid))

        resumen["carreras"] += 1
        resumen["materias_plan"] += len(vigentes)

    db.commit()
    return resumen


def importar_periodo(
    db: Session,
    data: dict | list,
    anio: int | None = None,
    semestre: int | None = None,
    titulo: str | None = None,
    fuente: str | None = None,
) -> dict:
    meta = {}
    if isinstance(data, dict):
        meta = data.get("periodo") or {}
        lista = data.get("materias") or []
    else:
        lista = data
    anio = anio or meta.get("anio")
    semestre = semestre or meta.get("semestre")
    if not anio or semestre not in (1, 2):
        raise ValueError("Falta indicar el año y el semestre (1 o 2) del período")

    definido = meta.get("definido")
    if definido is None:  # Se deduce: el formato no definido no trae aulas
        definido = any(
            d.get("aula") not in ("", None, "NO ASIGNADO", "NO ASIGNADA")
            for m in lista for c in m.get("comisiones", []) for d in c.get("dias", [])
        )

    periodo = db.scalar(select(Periodo).where(Periodo.anio == anio, Periodo.semestre == semestre))
    if periodo is None:
        periodo = Periodo(anio=anio, semestre=semestre)
        db.add(periodo)
    periodo.titulo = _cortar(titulo or meta.get("titulo"), 255)
    periodo.fuente = _cortar(fuente or meta.get("fuente"), 500)
    periodo.definido = bool(definido)
    db.flush()

    materias = _Materias(db)
    existentes = {(c.materia_id, c.nombre): c for c in periodo.comisiones}
    vigentes = set()
    resumen = {"periodo": periodo.nombre, "definido": periodo.definido, "materias": 0, "comisiones": 0,
               "horarios_sin_parsear": []}

    for item in lista:
        nombre = (item.get("actividad") or "").strip()
        if not nombre:
            continue
        materia = materias.obtener(nombre, item.get("codigo_actividad"))
        resumen["materias"] += 1
        for i, c in enumerate(item.get("comisiones") or [], start=1):
            nombre_com = _cortar(c.get("comision"), 40) or f"COM-{i:02d}"
            clave = (materia.id, nombre_com)
            if clave in vigentes:  # comisión repetida en el PDF: se suman los días
                comision = existentes[clave]
            else:
                comision = existentes.get(clave)
                if comision is None:
                    comision = Comision(periodo=periodo, materia=materia, nombre=nombre_com)
                    db.add(comision)
                    existentes[clave] = comision
                comision.horarios.clear()
                vigentes.add(clave)
                resumen["comisiones"] += 1
            docentes = c.get("docentes") or []
            comision.docentes = docentes if isinstance(docentes, list) else [docentes]
            comision.modalidad = _cortar(item.get("modalidad"), 60)
            comision.inicio_dictado = _cortar(item.get("inicio_dictado"), 30)
            comision.fin_dictado = _cortar(item.get("fin_dictado"), 30)
            comision.instancia = _cortar(item.get("instancia"), 60)
            for d in c.get("dias") or []:
                desde, hasta = parsear_horario(d.get("horario"))
                dia = parsear_dia(d.get("dia"))
                if dia is None or desde is None:
                    resumen["horarios_sin_parsear"].append(f"{nombre} {nombre_com}: {d.get('dia')} {d.get('horario')}")
                comision.horarios.append(HorarioComision(
                    dia=dia, hora_desde=desde, hora_hasta=hasta,
                    dia_texto=_cortar(d.get("dia"), 30), horario_texto=_cortar(d.get("horario"), 60),
                    tipo_clase=_cortar(d.get("tipo_clase"), 60), aula=_cortar(d.get("aula"), 60),
                    edificacion=_cortar(d.get("edificacion"), 100),
                    compartido_con=_cortar(d.get("compartido_con"), 255),
                ))
    for clave, comision in existentes.items():
        if clave not in vigentes:
            db.delete(comision)
    db.commit()
    return resumen


def cargar_json(ruta: str | Path):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)
