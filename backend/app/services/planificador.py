"""Motor de rutas de cursada.

Dado el plan de estudios (con correlativas), lo que el alumno ya aprobó / está
cursando, la oferta de comisiones por semestre y sus restricciones (días y
horarios disponibles, turno preferido, máximo de materias u horas por semestre),
arma varias rutas alternativas semestre a semestre hasta terminar la carrera.

El módulo no depende de la base de datos: recibe estructuras simples, lo que
permite testearlo de forma aislada (ver tests/test_planificador.py).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, replace

from .horarios import DIAS, fmt_rango, se_superponen

Bloque = tuple[int, int, int]  # (dia, desde, hasta) en minutos


# ----------------------------------------------------------------------------- entrada
@dataclass
class MateriaPlan:
    id: int
    nombre: str
    horas: float = 0
    anual: bool = False
    correlativas: set[int] = field(default_factory=set)
    orden_sugerido: int = 99  # semestre del itinerario oficial
    otro_requisito: bool = False


@dataclass
class OpcionComision:
    id: int | None
    nombre: str
    bloques: list[Bloque] = field(default_factory=list)
    detalle: list[dict] = field(default_factory=list)  # aula, tipo de clase, etc. por bloque
    docentes: list[str] = field(default_factory=list)
    horario_a_confirmar: bool = False


@dataclass
class OfertaSemestre:
    """Comisiones disponibles en un semestre dado, por id de materia del plan."""
    comisiones: dict[int, list[OpcionComision]]
    fuente: str = ""  # "2° semestre 2026" (real) o "estimada según 2° semestre 2026"
    estimada: bool = False


@dataclass
class Parametros:
    anio_inicio: int
    semestre_inicio: int  # 1 o 2
    max_materias: int = 4
    max_horas: float | None = None
    disponibilidad: dict[int, list[tuple[int, int]]] | None = None  # dia -> [(desde, hasta)]
    turno_preferido: str | None = None  # manana | tarde | noche
    cantidad_rutas: int = 4
    max_semestres: int = 16
    objetivo_semestres: int | None = None
    asumir_cursando_aprobadas: bool = True
    incluir_sin_oferta: bool = True  # materias sin comisiones conocidas: se planifican "a confirmar"
    semilla: int = 7


# ----------------------------------------------------------------------------- salida
@dataclass
class Asignacion:
    materia: MateriaPlan
    comision: OpcionComision
    continua_anual: bool = False  # 2da mitad de una materia anual

    def to_dict(self):
        return {
            "plan_id": self.materia.id,
            "materia": self.materia.nombre,
            "horas": self.materia.horas,
            "anual": self.materia.anual,
            "continua_anual": self.continua_anual,
            "comision_id": self.comision.id,
            "comision": self.comision.nombre,
            "docentes": self.comision.docentes,
            "horario_a_confirmar": self.comision.horario_a_confirmar,
            "bloques": [
                {"dia": d, "dia_nombre": DIAS.get(d, ""), "desde": a, "hasta": b, "rango": fmt_rango(a, b),
                 **(self.comision.detalle[i] if i < len(self.comision.detalle) else {})}
                for i, (d, a, b) in enumerate(self.comision.bloques)
            ],
        }


@dataclass
class Candidata:
    """Fila del panel lateral del Excel: materias pendientes en ese semestre."""
    materia: MateriaPlan
    disponible: bool
    cursar: bool
    motivo: str
    dias: str
    horarios: str
    faltan: list[str]

    def to_dict(self):
        return {
            "plan_id": self.materia.id, "materia": self.materia.nombre, "horas": self.materia.horas,
            "disponible": self.disponible, "cursar": self.cursar, "motivo": self.motivo,
            "dias": self.dias, "horarios": self.horarios, "correlativas_faltantes": self.faltan,
        }


@dataclass
class SemestrePlan:
    anio: int
    semestre: int
    asignaciones: list[Asignacion]
    candidatas: list[Candidata]
    fuente_oferta: str
    oferta_estimada: bool

    @property
    def titulo(self):
        return f"{self.semestre}° SEMESTRE {self.anio}"

    @property
    def horas(self):
        return sum(a.materia.horas for a in self.asignaciones)

    def to_dict(self):
        return {
            "anio": self.anio, "semestre": self.semestre, "titulo": self.titulo, "horas": self.horas,
            "fuente_oferta": self.fuente_oferta, "oferta_estimada": self.oferta_estimada,
            "materias": [a.to_dict() for a in self.asignaciones],
            "candidatas": [c.to_dict() for c in self.candidatas],
        }


@dataclass
class Ruta:
    nombre: str
    descripcion: str
    semestres: list[SemestrePlan]
    sin_planificar: list[dict]
    vetos: frozenset | None = None
    estrategia: "Estrategia | None" = None

    @property
    def completa(self):
        return not self.sin_planificar

    @property
    def cantidad_semestres(self):
        # Semestres hasta la última materia (los vacíos intermedios cuentan)
        ultimos = [i for i, s in enumerate(self.semestres) if s.asignaciones]
        return (ultimos[-1] + 1) if ultimos else 0

    def firma(self):
        return tuple(
            frozenset((a.materia.id, a.comision.nombre) for a in s.asignaciones) for s in self.semestres
        )

    def to_dict(self):
        fin = self.semestres[self.cantidad_semestres - 1] if self.cantidad_semestres else None
        return {
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "completa": self.completa,
            "cantidad_semestres": self.cantidad_semestres,
            "finaliza": fin.titulo if fin else None,
            "semestres": [s.to_dict() for s in self.semestres[: self.cantidad_semestres]],
            "sin_planificar": self.sin_planificar,
        }


# ----------------------------------------------------------------------------- utilidades
def siguiente(anio: int, semestre: int) -> tuple[int, int]:
    return (anio, 2) if semestre == 1 else (anio + 1, 1)


def _encaja(op: OpcionComision, disponibilidad) -> bool:
    if disponibilidad is None:
        return True
    for dia, desde, hasta in op.bloques:
        rangos = disponibilidad.get(dia) or []
        if not any(r0 <= desde and hasta <= r1 for r0, r1 in rangos):
            return False
    return True


def _superpone(op: OpcionComision, ocupados: list[Bloque]) -> bool:
    return any(se_superponen(b, o) for b in op.bloques for o in ocupados)


def _afinidad_turno(op: OpcionComision, turno: str | None) -> float:
    """0..1: proporción de minutos de la comisión dentro del turno preferido."""
    from .horarios import TURNOS

    if not turno or turno not in TURNOS or not op.bloques:
        return 0.0
    t0, t1 = TURNOS[turno]
    total = sum(b - a for _, a, b in op.bloques)
    dentro = sum(max(0, min(b, t1) - max(a, t0)) for _, a, b in op.bloques)
    return dentro / total if total else 0.0


def _resumen_horario(op: OpcionComision | None) -> tuple[str, str]:
    if op is None:
        return "", ""
    if op.horario_a_confirmar or not op.bloques:
        return "A confirmar", ""
    dias = " - ".join(DIAS.get(d, "?") for d, _, _ in op.bloques)
    rangos = [fmt_rango(a, b) for _, a, b in op.bloques]
    horarios = rangos[0] if len(set(rangos)) == 1 else " - ".join(rangos)
    return dias, horarios


def profundidad_critica(plan: dict[int, MateriaPlan], pendientes: set[int]) -> dict[int, int]:
    """Semestres mínimos que faltan desde cada materia hasta el final de su cadena de dependientes."""
    dependientes: dict[int, set[int]] = {m: set() for m in pendientes}
    for m in pendientes:
        for c in plan[m].correlativas:
            if c in dependientes:
                dependientes[c].add(m)
    memo: dict[int, int] = {}

    def prof(m, pila=()):
        if m in memo:
            return memo[m]
        if m in pila:  # ciclo en correlativas mal cargadas: se corta
            return 1
        duracion = 2 if plan[m].anual else 1
        memo[m] = duracion + max((prof(d, pila + (m,)) for d in dependientes[m]), default=0)
        return memo[m]

    return {m: prof(m) for m in pendientes}


def _descendientes(plan, pendientes) -> dict[int, int]:
    hijos: dict[int, set[int]] = {m: set() for m in pendientes}
    for m in pendientes:
        for c in plan[m].correlativas:
            if c in hijos:
                hijos[c].add(m)
    res = {}
    for m in pendientes:
        vistos, pila = set(), list(hijos[m])
        while pila:
            x = pila.pop()
            if x not in vistos:
                vistos.add(x)
                pila.extend(hijos[x])
        res[m] = len(vistos)
    return res


# ----------------------------------------------------------------------------- estrategias
@dataclass
class Estrategia:
    nombre: str
    descripcion: str
    peso_critico: float = 100
    peso_descendientes: float = 10
    peso_itinerario: float = 5
    peso_turno: float = 30
    peso_escasez: float = 100
    delta_materias: int = 0  # -1 = una materia menos que el máximo por semestre
    ruido: float = 0.0
    postergar: float = 0.0  # probabilidad de dejar una materia elegible para más adelante
    semilla: int = 0


ESTRATEGIAS = [
    Estrategia("Más rápida", "Prioriza las materias que destraban más correlativas (camino crítico) "
               "y llena cada semestre al máximo permitido."),
    Estrategia("Itinerario oficial", "Sigue el orden sugerido por el plan de la carrera, respetando tus horarios.",
               peso_critico=20, peso_descendientes=2, peso_itinerario=120, peso_escasez=20),
    Estrategia("Más liviana", "Una materia menos por semestre que el máximo indicado: más tiempo, menos carga.",
               delta_materias=-1),
    Estrategia("Turno preferido", "Elige comisiones en tu turno preferido aunque eso demore alguna materia.",
               peso_critico=40, peso_descendientes=4, peso_turno=400),
]


# ----------------------------------------------------------------------------- motor
class Planificador:
    def __init__(
        self,
        plan: list[MateriaPlan],
        oferta_por_semestre,  # callable (anio, semestre) -> OfertaSemestre
        aprobadas: set[int],
        cursando: set[int],
        params: Parametros,
    ):
        self.plan = {m.id: m for m in plan}
        self.oferta = oferta_por_semestre
        self.params = params
        self.aprobadas = set(aprobadas) & self.plan.keys()
        self.cursando = set(cursando) & self.plan.keys()
        self._cache_oferta: dict[tuple[int, int], OfertaSemestre] = {}
        hechas = self.aprobadas | (self.cursando if params.asumir_cursando_aprobadas else set())
        self.pendientes_iniciales = set(self.plan) - hechas
        self.hechas_iniciales = hechas
        self.critico = profundidad_critica(self.plan, self.pendientes_iniciales)
        self.descendientes = _descendientes(self.plan, self.pendientes_iniciales)
        # Materias que aparecen en alguna oferta conocida (se miran ambos semestres del año)
        self._con_oferta: set[int] = set()
        self._oferta(params.anio_inicio, params.semestre_inicio)
        self._oferta(*siguiente(params.anio_inicio, params.semestre_inicio))

    # -- oferta
    def _oferta(self, anio, semestre) -> OfertaSemestre:
        clave = (anio, semestre)
        if clave not in self._cache_oferta:
            of = self.oferta(anio, semestre)
            self._cache_oferta[clave] = of
            self._con_oferta |= {m for m, ops in of.comisiones.items() if ops}
        return self._cache_oferta[clave]

    def _opciones(self, mid: int, of: OfertaSemestre) -> list[OpcionComision]:
        ops = of.comisiones.get(mid) or []
        if ops:
            return ops
        if self.params.incluir_sin_oferta and mid not in self._con_oferta:
            return [OpcionComision(id=None, nombre="A confirmar", horario_a_confirmar=True)]
        return []

    # -- prioridad
    def _prioridad(self, mid: int, est: Estrategia, rng: random.Random) -> float:
        m = self.plan[mid]
        p = (
            est.peso_critico * self.critico.get(mid, 1)
            + est.peso_descendientes * self.descendientes.get(mid, 0)
            + est.peso_itinerario * max(0, 20 - m.orden_sugerido)
        )
        if est.ruido:
            p *= 1 + rng.uniform(-est.ruido, est.ruido)
        return p

    # -- selección de un semestre (branch & bound)
    def _elegir(self, elegibles, prioridades, ocupados, cupo_materias, cupo_horas, est):
        """Devuelve la mejor combinación [(materia, comision)] sin superposiciones."""
        p = self.params
        elegibles = sorted(elegibles, key=lambda e: -prioridades[e[0]])[:14]
        mejor = {"valor": -1.0, "sel": []}
        nodos = [0]

        def valor_op(mid, op):
            # Prioridad de la materia + afinidad al turno + pequeño premio por horario conocido
            return prioridades[mid] + est.peso_turno * _afinidad_turno(op, p.turno_preferido) + \
                (0 if op.horario_a_confirmar else 1)

        cotas = [max((valor_op(mid, op) for op in ops), default=0) for mid, ops in elegibles]

        def dfs(i, sel, valor, ocup, horas):
            nodos[0] += 1
            if valor > mejor["valor"]:
                mejor["valor"], mejor["sel"] = valor, list(sel)
            if i >= len(elegibles) or len(sel) >= cupo_materias or nodos[0] > 40000:
                return
            # Cota superior: lo mejor que podrían sumar las restantes
            resto = sorted(cotas[i:], reverse=True)[: cupo_materias - len(sel)]
            if valor + sum(resto) <= mejor["valor"]:
                return
            mid, ops = elegibles[i]
            h = self.plan[mid].horas or 0
            if cupo_horas is None or horas + h <= cupo_horas:
                for op in sorted(ops, key=lambda o: -valor_op(mid, o)):
                    if not _superpone(op, ocup):
                        sel.append((mid, op))
                        dfs(i + 1, sel, valor + valor_op(mid, op), ocup + op.bloques, horas + h)
                        sel.pop()
            dfs(i + 1, sel, valor, ocup, horas)

        dfs(0, [], 0.0, list(ocupados), 0.0)
        return mejor["sel"]

    # -- simulación de una ruta
    def _simular(self, est: Estrategia, vetos: frozenset = frozenset()) -> Ruta:
        """`vetos`: {(índice de semestre, plan_id)} materias que NO se cursan en ese semestre."""
        p = self.params
        rng = random.Random(est.semilla)
        prioridades = {m: self._prioridad(m, est, rng) for m in self.pendientes_iniciales}
        max_mat = max(1, p.max_materias + est.delta_materias)
        max_horas = p.max_horas

        hechas = set(self.hechas_iniciales)
        pendientes = set(self.pendientes_iniciales)
        arrastre: list[Asignacion] = []  # 2da mitad de materias anuales
        anio, sem = p.anio_inicio, p.semestre_inicio
        semestres: list[SemestrePlan] = []
        vacios_seguidos = 0

        while (pendientes or arrastre) and len(semestres) < p.max_semestres:
            of = self._oferta(anio, sem)
            ocupados = [b for a in arrastre for b in a.comision.bloques]
            horas_arrastre = sum(a.materia.horas for a in arrastre)
            cupo_mat = max_mat - len(arrastre)
            cupo_horas = None if max_horas is None else max_horas - horas_arrastre

            elegibles, motivos = [], {}
            for mid in pendientes:
                m = self.plan[mid]
                faltan = m.correlativas - hechas
                if faltan:
                    motivos[mid] = "Faltan correlativas"
                    continue
                ops = self._opciones(mid, of)
                if not ops:
                    motivos[mid] = "No se dicta este semestre"
                    continue
                ops_ok = [o for o in ops if _encaja(o, p.disponibilidad)]
                if not ops_ok:
                    motivos[mid] = "Fuera de tu disponibilidad horaria"
                    continue
                elegibles.append((mid, ops_ok))
            if vetos:
                idx = len(semestres)
                for mid, _ in elegibles:
                    if (idx, mid) in vetos:
                        motivos[mid] = "Postergada para destrabar otras materias"
                elegibles = [e for e in elegibles if (idx, e[0]) not in vetos]
            if est.postergar:
                # Explorar: a veces conviene NO cursar algo ahora (p. ej. una anual que
                # bloquea un día del semestre siguiente)
                postergadas = {mid for mid, _ in elegibles if rng.random() < est.postergar}
                for mid in postergadas:
                    motivos[mid] = "Postergada en esta alternativa"
                elegibles = [e for e in elegibles if e[0] not in postergadas]

            # Escasez: si la materia no se puede cursar el semestre siguiente (no se dicta o no
            # encaja con tus horarios), postergarla cuesta un año entero -> se le da más prioridad.
            of_sig = self._oferta(*siguiente(anio, sem))
            prioridad_sem = dict(prioridades)
            for mid, _ in elegibles:
                ops_sig = [o for o in self._opciones(mid, of_sig) if _encaja(o, p.disponibilidad)]
                if not ops_sig:
                    prioridad_sem[mid] += est.peso_escasez * self.critico.get(mid, 1)

            seleccion = self._elegir(elegibles, prioridad_sem, ocupados, cupo_mat, cupo_horas, est) \
                if cupo_mat > 0 else []
            elegidas = {mid for mid, _ in seleccion}
            asignaciones = list(arrastre) + [Asignacion(self.plan[mid], op) for mid, op in seleccion]

            # Panel de candidatas (como las columnas Cursar/Disp/Materias/Días/Horarios del Excel)
            ocupados_final = [b for a in asignaciones for b in a.comision.bloques]
            candidatas = []
            for a in arrastre:
                d, h = _resumen_horario(a.comision)
                candidatas.append(Candidata(a.materia, True, True, "Continúa (anual)", d, h, []))
            sel_por_mid = dict(seleccion)
            for mid in sorted(pendientes, key=lambda x: (-prioridades[x], self.plan[x].nombre)):
                m = self.plan[mid]
                faltan = sorted(self.plan[c].nombre for c in m.correlativas - hechas)
                op = sel_por_mid.get(mid)
                if op is None:
                    ops = self._opciones(mid, of)
                    op = next((o for o in ops if _encaja(o, p.disponibilidad)), ops[0] if ops else None)
                d, h = _resumen_horario(op)
                if mid in elegidas:
                    motivo = ""
                elif mid in motivos:
                    motivo = motivos[mid]
                elif cupo_mat <= 0 or len(elegidas) + len(arrastre) >= max_mat:
                    motivo = "Límite de materias del semestre"
                elif any(not _superpone(o, ocupados_final) for o in dict(elegibles).get(mid, [])):
                    motivo = "Excede el límite de horas semanales"
                else:
                    motivo = "Se superpone con otra materia elegida"
                candidatas.append(Candidata(m, not faltan, mid in elegidas, motivo, d, h, faltan))

            semestres.append(SemestrePlan(anio, sem, asignaciones, candidatas, of.fuente, of.estimada))

            # Avance: las semestrales se aprueban al terminar; las anuales pasan al próximo semestre
            nuevo_arrastre = []
            for a in asignaciones:
                if a.materia.anual and not a.continua_anual:
                    nuevo_arrastre.append(Asignacion(a.materia, a.comision, continua_anual=True))
                else:
                    hechas.add(a.materia.id)
            pendientes -= elegidas
            arrastre = nuevo_arrastre

            vacios_seguidos = 0 if asignaciones else vacios_seguidos + 1
            if vacios_seguidos >= 2:  # dos semestres seguidos sin poder cursar nada: bloqueo
                break
            anio, sem = siguiente(anio, sem)

        sin_planificar = []
        for mid in sorted(pendientes, key=lambda x: self.plan[x].nombre):
            m = self.plan[mid]
            faltan = m.correlativas - hechas
            if faltan:
                motivo = "Correlativas sin aprobar: " + ", ".join(sorted(self.plan[c].nombre for c in faltan))
            elif mid not in self._con_oferta and not p.incluir_sin_oferta:
                motivo = "No hay comisiones cargadas para esta materia"
            else:
                motivo = "Ninguna comisión encaja con tu disponibilidad horaria"
            sin_planificar.append({"plan_id": mid, "materia": m.nombre, "motivo": motivo})

        # Quito semestres vacíos del final
        while semestres and not semestres[-1].asignaciones:
            semestres.pop()
        return Ruta(est.nombre, est.descripcion, semestres, sin_planificar,
                    vetos=None if est.postergar else frozenset(vetos), estrategia=est)

    # -- API pública
    @staticmethod
    def puntaje(ruta: Ruta):
        """Menor es mejor: completa, menos semestres, materias lo antes posible."""
        adelanto = sum(i for i, s in enumerate(ruta.semestres) for a in s.asignaciones if not a.continua_anual)
        return (not ruta.completa, len(ruta.sin_planificar), ruta.cantidad_semestres, adelanto)

    def _mejorar(self, _est, ruta: Ruta, rondas: int = 4) -> Ruta:
        """Búsqueda local: prueba postergar cada materia de la ruta en su semestre y
        se queda con el cambio si la ruta resultante es mejor (p. ej. no empezar una
        anual que bloquea un día que necesita otra materia el semestre siguiente)."""
        if ruta.vetos is None or ruta.estrategia is None:
            return ruta
        est = ruta.estrategia
        mejor, vetos = ruta, ruta.vetos
        for _ in range(rondas):
            mejoro = False
            for i, sem in enumerate(mejor.semestres):
                for a in sem.asignaciones:
                    if a.continua_anual:
                        continue
                    prueba = self._simular(est, vetos | {(i, a.materia.id)})
                    if self.puntaje(prueba) < self.puntaje(mejor):
                        mejor, vetos, mejoro = prueba, prueba.vetos, True
                        break
                if mejoro:
                    break
            if not mejoro:
                break
        return mejor

    def generar(self, variantes: int = 24) -> list[Ruta]:
        """Para cada estrategia corre la versión base y `variantes` versiones con ruido
        (orden de prioridades y materias postergadas al azar) y se queda con la mejor.
        Las rutas alternativas son las mejores restantes, sin repetir."""
        p = self.params
        estrategias = list(ESTRATEGIAS)
        if not p.turno_preferido:
            estrategias = [e for e in estrategias if e.nombre != "Turno preferido"]
        if p.max_materias <= 1:
            estrategias = [e for e in estrategias if e.delta_materias == 0]

        rutas, firmas, pool = [], set(), []

        def agregar(ruta):
            f = ruta.firma()
            if f in firmas:
                return False
            firmas.add(f)
            rutas.append(ruta)
            return True

        for k, est in enumerate(estrategias):
            n = variantes * (2 if k == 0 else 1)
            candidatas = [self._simular(est)]
            for v in range(n):
                semilla = p.semilla * 100003 + k * 1009 + v
                candidatas.append(self._simular(replace(
                    est, ruido=0.15 + 0.35 * (v % 4) / 3, postergar=(0.0, 0.08, 0.15, 0.25)[v % 4], semilla=semilla,
                )))
            candidatas.sort(key=self.puntaje)
            refinables = [c for c in candidatas if c.vetos is not None][:2]
            candidatas.extend(self._mejorar(None, c) for c in refinables)
            candidatas.sort(key=self.puntaje)
            pool.extend(candidatas)
            if len(rutas) < p.cantidad_rutas:
                for c in candidatas:
                    if agregar(c):
                        break

        for c in sorted(pool, key=self.puntaje):
            if len(rutas) >= p.cantidad_rutas:
                break
            if c.firma() not in firmas:
                agregar(Ruta("Alternativa", "Otra combinación de materias y comisiones con buen resultado.",
                             c.semestres, c.sin_planificar))

        rutas.sort(key=self.puntaje)
        for i, r in enumerate(rutas, start=1):
            r.nombre = f"Ruta {i} - {r.nombre}"
        return rutas

    def minimo_teorico(self) -> int:
        """Cota inferior de semestres (sólo por correlativas)."""
        return max(self.critico.values(), default=0)
