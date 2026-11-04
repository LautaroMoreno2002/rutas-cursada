"""Une la base de datos con el planificador: arma el plan, la oferta y el estado del alumno."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Alumno, Carrera, Comision, Periodo
from .planificador import MateriaPlan, OfertaSemestre, OpcionComision, Parametros, Planificador


def proximo_semestre(hoy: date | None = None) -> tuple[int, int]:
    """Semestre a planificar por defecto: el próximo que todavía no empezó."""
    hoy = hoy or date.today()
    if hoy.month <= 2:
        return hoy.year, 1
    if hoy.month <= 7:
        return hoy.year, 2
    return hoy.year + 1, 1


def plan_de_carrera(carrera: Carrera) -> list[MateriaPlan]:
    orden: dict[int, int] = {}
    itinerarios = sorted(carrera.itinerarios, key=lambda i: i.semestre_inicio)
    if itinerarios:
        for s in itinerarios[0].semestres:
            for im in s.materias:
                orden.setdefault(im.plan_id, s.orden)
    return [
        MateriaPlan(
            id=p.id,
            nombre=p.materia.nombre,
            horas=p.carga_horaria_semanal or 0,
            anual=p.es_anual,
            correlativas={c.requiere_plan_id for c in p.correlativas},
            orden_sugerido=orden.get(p.id, 99),
            otro_requisito=p.otro_requisito,
        )
        for p in carrera.plan
    ]


def opcion_desde_comision(c: Comision) -> OpcionComision:
    bloques, detalle, a_confirmar = [], [], False
    for h in c.horarios:
        if h.dia is None or h.hora_desde is None:
            a_confirmar = True
            continue
        bloques.append((h.dia, h.hora_desde, h.hora_hasta))
        detalle.append({"aula": h.aula, "edificacion": h.edificacion, "tipo_clase": h.tipo_clase})
    return OpcionComision(
        id=c.id, nombre=c.nombre, bloques=bloques, detalle=detalle,
        docentes=c.docentes or [], horario_a_confirmar=a_confirmar or not bloques,
    )


class ProveedorOferta:
    """Oferta real si el período ya está cargado; si no, se estima con el último
    período del mismo semestre (los horarios suelen repetirse año a año)."""

    def __init__(self, db: Session, carrera: Carrera):
        self.db = db
        self.materia_a_plan = {p.materia_id: p.id for p in carrera.plan}
        self.periodos = list(db.scalars(select(Periodo).order_by(Periodo.anio.desc(), Periodo.semestre.desc())))
        self._cache: dict[int, dict[int, list[OpcionComision]]] = {}

    def _comisiones(self, periodo: Periodo):
        if periodo.id not in self._cache:
            por_plan: dict[int, list[OpcionComision]] = {}
            for c in periodo.comisiones:
                pid = self.materia_a_plan.get(c.materia_id)
                if pid is not None:
                    por_plan.setdefault(pid, []).append(opcion_desde_comision(c))
            self._cache[periodo.id] = por_plan
        return self._cache[periodo.id]

    def __call__(self, anio: int, semestre: int) -> OfertaSemestre:
        exacto = next((p for p in self.periodos if p.anio == anio and p.semestre == semestre), None)
        if exacto:
            return OfertaSemestre(self._comisiones(exacto), exacto.nombre, estimada=False)
        mismo = next((p for p in self.periodos if p.semestre == semestre), None)
        base = mismo or (self.periodos[0] if self.periodos else None)
        if base is None:
            return OfertaSemestre({}, "sin oferta cargada", estimada=True)
        return OfertaSemestre(self._comisiones(base), f"estimada según {base.nombre}", estimada=True)


def estado_alumno(alumno: Alumno) -> tuple[set[int], set[int]]:
    aprobadas = {am.plan_id for am in alumno.materias if am.estado == "aprobada"}
    cursando = {am.plan_id for am in alumno.materias if am.estado == "cursando"}
    return aprobadas, cursando


def generar_rutas(db: Session, carrera: Carrera, aprobadas: set[int], cursando: set[int], params: Parametros):
    planificador = Planificador(plan_de_carrera(carrera), ProveedorOferta(db, carrera), aprobadas, cursando, params)
    rutas = planificador.generar()
    return planificador, rutas
