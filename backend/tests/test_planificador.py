from app.services.horarios import se_superponen
from app.services.planificador import MateriaPlan, OfertaSemestre, OpcionComision, Parametros, Planificador

H = 60


def op(nombre, *bloques, id_=None):
    return OpcionComision(id=id_, nombre=nombre, bloques=[(d, a * H, b * H) for d, a, b in bloques])


def oferta_fija(comisiones_s1, comisiones_s2=None):
    def f(anio, semestre):
        c = comisiones_s1 if semestre == 1 or comisiones_s2 is None else comisiones_s2
        return OfertaSemestre(c, f"{semestre}° semestre", estimada=False)
    return f


def validar(ruta, plan, aprobadas, params):
    """Invariantes que toda ruta debe cumplir."""
    hechas = set(aprobadas)
    por_id = {m.id: m for m in plan}
    for s in ruta.semestres:
        bloques = [b for a in s.asignaciones for b in a.comision.bloques]
        for i, b1 in enumerate(bloques):
            for b2 in bloques[i + 1:]:
                assert not se_superponen(b1, b2), f"superposición en {s.titulo}"
        assert len(s.asignaciones) <= params.max_materias
        for a in s.asignaciones:
            if not a.continua_anual:
                assert por_id[a.materia.id].correlativas <= hechas, f"{a.materia.nombre} sin correlativas"
            if params.disponibilidad:
                for d, x, y in a.comision.bloques:
                    assert any(r0 <= x and y <= r1 for r0, r1 in params.disponibilidad.get(d, []))
        for a in s.asignaciones:
            if not a.materia.anual or a.continua_anual:
                hechas.add(a.materia.id)


def test_cadena_simple_respeta_correlativas():
    plan = [MateriaPlan(1, "A", 4), MateriaPlan(2, "B", 4, correlativas={1}), MateriaPlan(3, "C", 4, correlativas={2})]
    oferta = {1: [op("C1", (1, 18, 22))], 2: [op("C1", (2, 18, 22))], 3: [op("C1", (3, 18, 22))]}
    p = Parametros(2027, 1, max_materias=3, cantidad_rutas=2)
    rutas = Planificador(plan, oferta_fija(oferta), set(), set(), p).generar()
    assert rutas[0].cantidad_semestres == 3 and rutas[0].completa
    for r in rutas:
        validar(r, plan, set(), p)


def test_no_superpone_y_elige_otra_comision():
    plan = [MateriaPlan(1, "A", 4), MateriaPlan(2, "B", 4)]
    oferta = {1: [op("C1", (1, 18, 22))], 2: [op("C1", (1, 19, 21)), op("C2", (2, 18, 22))]}
    p = Parametros(2027, 1, max_materias=2, cantidad_rutas=1)
    r = Planificador(plan, oferta_fija(oferta), set(), set(), p).generar()[0]
    assert r.cantidad_semestres == 1
    assert {a.comision.nombre for a in r.semestres[0].asignaciones if a.materia.id == 2} == {"C2"}


def test_disponibilidad_horaria_y_turno():
    plan = [MateriaPlan(1, "A", 4)]
    oferta = {1: [op("Mañana", (1, 8, 12)), op("Noche", (1, 18, 22))]}
    disp = {d: [(18 * H, 23 * H)] for d in range(1, 6)}
    p = Parametros(2027, 1, disponibilidad=disp, cantidad_rutas=1)
    r = Planificador(plan, oferta_fija(oferta), set(), set(), p).generar()[0]
    assert r.semestres[0].asignaciones[0].comision.nombre == "Noche"
    # Sin restricción pero prefiriendo la mañana
    p2 = Parametros(2027, 1, turno_preferido="manana", cantidad_rutas=1)
    r2 = Planificador(plan, oferta_fija(oferta), set(), set(), p2).generar()[0]
    assert r2.semestres[0].asignaciones[0].comision.nombre == "Mañana"


def test_sin_comision_compatible_queda_sin_planificar():
    plan = [MateriaPlan(1, "A", 4)]
    oferta = {1: [op("Mañana", (1, 8, 12))]}
    p = Parametros(2027, 1, disponibilidad={1: [(18 * H, 23 * H)]}, cantidad_rutas=1)
    r = Planificador(plan, oferta_fija(oferta), set(), set(), p).generar()[0]
    assert not r.completa
    assert "disponibilidad" in r.sin_planificar[0]["motivo"]


def test_materia_anual_ocupa_dos_semestres():
    plan = [MateriaPlan(1, "Tesina", 4, anual=True), MateriaPlan(2, "Final", 4, correlativas={1}),
            MateriaPlan(3, "Otra", 4)]
    s1 = {1: [op("C1", (5, 18, 22))], 2: [op("C1", (1, 18, 22))], 3: [op("C1", (5, 18, 20)), op("C2", (3, 18, 22))]}
    s2 = {2: [op("C1", (1, 18, 22))], 3: [op("C1", (5, 19, 21))]}
    p = Parametros(2027, 1, max_materias=3, cantidad_rutas=1)
    r = Planificador(plan, oferta_fija(s1, s2), set(), set(), p).generar()[0]
    validar(r, plan, set(), p)
    nombres = [[a.materia.nombre for a in s.asignaciones] for s in r.semestres]
    assert "Tesina" in nombres[0] and "Tesina" in nombres[1]
    assert "Final" not in nombres[0] + nombres[1]  # recién al terminar la anual
    # "Otra" en el 2do semestre chocaría con la continuación de la Tesina (viernes)
    assert "Otra" in nombres[0]


def test_materia_que_solo_se_dicta_en_un_semestre_tiene_prioridad():
    # B sólo se dicta en el 1er semestre y destraba C; A se dicta siempre.
    plan = [MateriaPlan(1, "A", 4), MateriaPlan(2, "B", 4), MateriaPlan(3, "C", 4, correlativas={2})]
    s1 = {1: [op("C1", (1, 18, 22))], 2: [op("C1", (1, 18, 22))]}
    s2 = {1: [op("C1", (1, 18, 22))], 3: [op("C1", (2, 18, 22))]}
    p = Parametros(2027, 1, max_materias=1, cantidad_rutas=1)
    r = Planificador(plan, oferta_fija(s1, s2), set(), set(), p).generar()[0]
    assert r.semestres[0].asignaciones[0].materia.nombre == "B"
    assert r.cantidad_semestres == 3


def test_aprobadas_y_cursando():
    plan = [MateriaPlan(1, "A", 4), MateriaPlan(2, "B", 4, correlativas={1}), MateriaPlan(3, "C", 4)]
    oferta = {i: [op("C1", (i, 18, 22))] for i in (1, 2, 3)}
    p = Parametros(2027, 1, cantidad_rutas=1)
    r = Planificador(plan, oferta_fija(oferta), {3}, {1}, p).generar()[0]
    assert [[a.materia.nombre for a in s.asignaciones] for s in r.semestres] == [["B"]]
    p.asumir_cursando_aprobadas = False
    r = Planificador(plan, oferta_fija(oferta), {3}, {1}, p).generar()[0]
    assert r.cantidad_semestres == 2


def test_rutas_distintas_y_limite_horas():
    plan = [MateriaPlan(i, f"M{i}", 6) for i in range(1, 7)]
    oferta = {i: [op("C1", (i % 6 + 1, 18, 22)), op("C2", (i % 6 + 1, 8, 12))] for i in range(1, 7)}
    p = Parametros(2027, 1, max_materias=6, max_horas=12, cantidad_rutas=4)
    rutas = Planificador(plan, oferta_fija(oferta), set(), set(), p).generar()
    assert len({r.firma() for r in rutas}) == len(rutas) >= 2
    for r in rutas:
        validar(r, plan, set(), p)
        assert all(s.horas <= 12 for s in r.semestres)


def test_datos_demo(db_demo):
    from sqlalchemy import select

    from app.models import Carrera
    from app.services.rutas import generar_rutas

    carrera = db_demo.scalar(select(Carrera))
    disp = {d: [(18 * H, 23 * H)] for d in range(1, 6)}
    disp[6] = [(8 * H, 14 * H)]
    p = Parametros(2027, 1, max_materias=4, disponibilidad=disp, cantidad_rutas=4)
    planificador, rutas = generar_rutas(db_demo, carrera, set(), set(), p)
    plan = [m for m in planificador.plan.values()]
    assert len(rutas) == 4
    for r in rutas:
        assert r.completa
        validar(r, plan, set(), p)
