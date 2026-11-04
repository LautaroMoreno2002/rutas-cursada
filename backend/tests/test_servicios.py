from sqlalchemy import func, select

from app.models import Comision, Correlativa, Materia, PlanEstudio
from app.services.horarios import parsear_dia, parsear_horario
from app.services.importador import cargar_json, importar_carreras, importar_periodo
from app.services.texto import IndiceNombres, normalizar
from app.cli import DEMO, schema_sql


def test_normalizar():
    assert normalizar("BASES DE DATOS II (A0101)") == "bases de datos ii"
    assert normalizar("Programación 2") == "programacion ii"
    assert normalizar("Introd. a la Programación") == "introduccion a la programacion"


def test_indice_no_confunde_niveles():
    idx = IndiceNombres({"Programación I": 1, "Programación II": 2, "Programación III": 3})
    assert idx.buscar("PROGRAMACION II") == 2
    assert idx.buscar("Programacion 3") == 3
    assert idx.buscar("Programación IV") is None
    assert IndiceNombres({"Taller de Tesina de Licenciatura": 9}).buscar("Taller de Tesina") == 9


def test_parseo_horarios():
    assert parsear_horario("18:00 a 22:00") == (1080, 1320)
    assert parsear_horario("18 a 22") == (1080, 1320)
    assert parsear_horario("8.30-12.30 hs") == (510, 750)
    assert parsear_horario("a definir") == (None, None)
    assert [parsear_dia(d) for d in ["Lunes", "MIÉRCOLES", "sáb", "Ju"]] == [1, 3, 6, 4]


def test_importacion_idempotente(db):
    carreras = cargar_json(DEMO / "carreras.json")
    periodo = cargar_json(DEMO / "periodo_2026_2.json")
    for _ in range(2):
        r = importar_carreras(db, carreras)
        importar_periodo(db, periodo)
    assert r["correlativas_sin_match"] == []
    n_plan = len(carreras[0]["plan_estudios"])
    assert db.scalar(select(func.count()).select_from(PlanEstudio)) == n_plan
    # Los nombres en mayúsculas del PDF se vinculan con las materias del plan (no se duplican)
    assert db.scalar(select(func.count()).select_from(Materia)) == n_plan
    assert db.scalar(select(func.count()).select_from(Correlativa)) == r["correlativas"]
    assert db.scalar(select(func.count()).select_from(Comision)) == sum(
        len(m["comisiones"]) for m in periodo["materias"])


def test_reimportar_periodo_conserva_ids(db):
    importar_carreras(db, cargar_json(DEMO / "carreras.json"))
    data = cargar_json(DEMO / "periodo_2026_2.json")
    importar_periodo(db, data)
    ids = set(db.scalars(select(Comision.id)))
    data["materias"][0]["comisiones"][0]["dias"][0]["aula"] = "Aula nueva"
    importar_periodo(db, data)
    assert set(db.scalars(select(Comision.id))) == ids


def test_schema_sql_mysql():
    sql = schema_sql()
    assert "CREATE TABLE IF NOT EXISTS alumno_materia" in sql
    assert "SERIAL" not in sql  # antes el schema mezclaba sintaxis de PostgreSQL
