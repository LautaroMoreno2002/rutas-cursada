from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.cli import DEMO
from app.main import app
from tests.fixtures.generar_pdfs import NO_DEFINIDO, generar

ADMIN = {"X-Admin-Token": "secreto-admin"}


@pytest.fixture()
def client(db):
    with TestClient(app) as c:
        with open(DEMO / "carreras.json", "rb") as f:
            assert c.post("/api/admin/carreras/importar", files={"archivo": f}, headers=ADMIN).status_code == 200
        for nombre in ("periodo_2026_2.json", "periodo_2027_1.json"):
            with open(DEMO / nombre, "rb") as f:
                r = c.post("/api/admin/periodos/importar", files={"archivo": f}, headers=ADMIN)
                assert r.status_code == 200, r.text
        yield c


def _registrar(client, email="ana@test.com"):
    carrera_id = client.get("/api/carreras").json()[0]["id"]
    r = client.post("/api/auth/registro", json={"nombre": "Ana", "email": email, "password": "secreta1",
                                                "carrera_id": carrera_id})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}, carrera_id


def test_admin_requiere_token(client):
    with open(DEMO / "carreras.json", "rb") as f:
        assert client.post("/api/admin/carreras/importar", files={"archivo": f}).status_code == 403


def test_admin_importa_pdf(client, tmp_dir):
    pdf = generar(tmp_dir / "oferta.pdf", NO_DEFINIDO)
    with open(pdf, "rb") as f:
        r = client.post("/api/admin/periodos/importar", files={"archivo": ("oferta.pdf", f, "application/pdf")},
                        data={"anio": "2027", "semestre": "2"}, headers=ADMIN)
    assert r.status_code == 200, r.text
    assert r.json()["periodo"] == "2° semestre 2027" and r.json()["definido"] is False
    periodos = client.get("/api/periodos").json()["periodos"]
    assert [p["nombre"] for p in periodos][0] == "2° semestre 2027"


def test_flujo_completo_alumno(client):
    h, carrera_id = _registrar(client)
    assert client.post("/api/auth/login", json={"email": "ana@test.com", "password": "mala"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ANA@test.com", "password": "secreta1"}).status_code == 200

    carrera = client.get(f"/api/carreras/{carrera_id}").json()
    plan = {m["nombre"]: m for m in carrera["plan"]}
    assert plan["Taller de Tesina"]["anual"] is True
    assert len(carrera["itinerarios"]) == 2

    # Marca la mitad de la carrera como aprobada y una materia como cursando con comisión
    aprobadas = [m for m in carrera["plan"] if (m["semestre_sugerido"] or 9) <= 4]
    oferta = client.get(f"/api/carreras/{carrera_id}/oferta").json()
    ids_aprobadas = {m["plan_id"] for m in aprobadas}
    bd2 = next(m for m in oferta["materias"] if m["plan_id"] not in ids_aprobadas)  # una que esté cursando
    com = bd2["comisiones"][0]
    cambios = [{"plan_id": m["plan_id"], "estado": "aprobada", "nota": 8} for m in aprobadas]
    cambios.append({"plan_id": bd2["plan_id"], "estado": "cursando", "comision_id": com["id"]})
    r = client.put("/api/me/materias", json={"materias": cambios}, headers=h)
    assert r.status_code == 200, r.text
    assert len(r.json()) == len(aprobadas) + 1

    cursando = client.get("/api/me/cursando", headers=h).json()
    assert cursando[0]["materia"] == bd2["materia"] and cursando[0]["comision"]["cursando"] == 1
    oferta = client.get(f"/api/carreras/{carrera_id}/oferta?periodo_id={oferta['periodo']['id']}").json()
    bd2 = next(m for m in oferta["materias"] if m["plan_id"] == bd2["plan_id"])
    assert bd2["comisiones"][0]["cursando"] == 1

    # Comisión que no corresponde a la materia
    otra = next(m for m in oferta["materias"] if m["plan_id"] != bd2["plan_id"])
    r = client.put("/api/me/materias", headers=h, json={"materias": [
        {"plan_id": bd2["plan_id"], "estado": "cursando", "comision_id": otra["comisiones"][0]["id"]}]})
    assert r.status_code == 400

    params = {
        "anio_inicio": 2027, "semestre_inicio": 1, "max_materias": 3, "turno_preferido": "noche",
        "disponibilidad": [{"dia": d, "desde": "18:00", "hasta": "23:00"} for d in range(1, 6)]
        + [{"dia": 6, "desde": "08:00", "hasta": "14:00"}],
        "cantidad_rutas": 3, "objetivo_anios": 3,
    }
    r = client.post("/api/rutas", json=params, headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["rutas"]) == 3
    pendientes = len(carrera["plan"]) - len(aprobadas) - 1
    assert data["pendientes"] == pendientes
    ruta = data["rutas"][0]
    assert ruta["completa"] and ruta["cumple_objetivo"] in (True, False)
    materias_en_ruta = {m["plan_id"] for s in ruta["semestres"] for m in s["materias"]}
    assert len(materias_en_ruta) == pendientes
    assert bd2["plan_id"] not in materias_en_ruta  # la que cursa se asume aprobada
    for s in ruta["semestres"]:
        for m in s["materias"]:
            for b in m["bloques"]:
                assert b["desde"] >= 18 * 60 or b["dia"] == 6

    # Las preferencias quedan guardadas
    assert client.get("/api/me", headers=h).json()["preferencias"]["max_materias"] == 3

    r = client.post("/api/rutas/excel", json=params, headers=h)
    assert r.status_code == 200
    wb = load_workbook(BytesIO(r.content))
    assert wb.sheetnames[0] == "Resumen" and len(wb.sheetnames) == 4
    ws = wb.worksheets[1]
    assert ws["A1"].value.endswith("2027") and ws["A2"].value == "Hora" and ws["I2"].value == "Cursar"


def test_rutas_sin_cuenta(client):
    carrera_id = client.get("/api/carreras").json()[0]["id"]
    r = client.post("/api/rutas", json={"carrera_id": carrera_id, "aprobadas": [], "cantidad_rutas": 2,
                                        "anio_inicio": 2027, "semestre_inicio": 1})
    assert r.status_code == 200
    assert all(rt["completa"] for rt in r.json()["rutas"])
    assert client.post("/api/rutas", json={}).status_code == 400


def test_cambiar_carrera_borra_progreso(client):
    h, carrera_id = _registrar(client, "b@test.com")
    plan_id = client.get(f"/api/carreras/{carrera_id}").json()["plan"][0]["plan_id"]
    client.put("/api/me/materias", headers=h, json={"materias": [{"plan_id": plan_id, "estado": "aprobada"}]})
    assert len(client.get("/api/me/materias", headers=h).json()) == 1
    r = client.put("/api/me/materias", headers=h, json={"materias": [{"plan_id": plan_id, "estado": "pendiente"}]})
    assert r.json() == []
    assert client.get("/api/me", headers={"Authorization": "Bearer x"}).status_code == 401
