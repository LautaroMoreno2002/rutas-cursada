from scrapper.carreras import extraer_correlativas, parsear_detalle_carrera
from scrapper.lector_periodo import extraer_codigo_y_actividad, obtener_comision
from scrapper.periodo import detectar_anio_semestre, procesar_pdf
from tests.fixtures.generar_pdfs import DEFINIDO, NO_DEFINIDO, generar

HTML = """
<html><body><article>
<ul><li>Duración: 5 años</li><li>Título: Licenciado/a en Sistemas</li><li>Modalidad: Presencial</li></ul>
<h1>Ámbitos de desempeño</h1><ul><li>Empresas</li><li>Investigación</li></ul>
<h1>Plan de Estudios</h1>
<table>
 <tr><td>Asignatura</td><td>Régimen</td><td>Semanal</td><td>Total</td><td>Correlativas</td></tr>
 <tr><td>1</td><td></td><td></td><td></td><td></td></tr>
 <tr><td>Programación I *</td><td>Semestral</td><td>8</td><td>128</td><td>Introducción a la Programación</td></tr>
 <tr><td>Programación II</td><td>Semestral</td><td>8</td><td>128</td><td>Programación IIntroducción a la Programación</td></tr>
</table>
<table>
 <tr><td>Otros requisitos académicos</td><td></td><td></td><td></td><td></td></tr>
 <tr><td>Inglés I</td><td>Semestral</td><td>4</td><td>64</td><td></td></tr>
</table>
<h1>Itinerario</h1>
<table>
 <tr><td><span>Inicio en el primer semestre</span></td></tr>
 <tr><td><ul><li>Programación I</li></ul></td><td><ul><li>Programación II</li></ul></td>
     <td><ul><li>Inglés I</li></ul></td></tr>
</table>
<table>
 <tr><td><span>Inicio en el segundo semestre</span></td></tr>
 <tr><td><ul><li>Programación I</li></ul></td><td><ul><li>Programación II</li></ul></td></tr>
</table>
</article></body></html>
"""


def test_parsear_detalle_carrera():
    c = parsear_detalle_carrera(HTML, {"carrera": "Lic. en Sistemas"})
    assert c["duracion"] == "5 años" and c["modalidad"] == "Presencial"
    assert c["ambitos_desempeno"] == ["Empresas", "Investigación"]
    nombres = [m["asignatura"] for m in c["plan_estudios"]]
    assert nombres == ["Programación I", "Programación II", "Inglés I"]
    assert c["plan_estudios"][1]["correlativas"] == ["Programación I", "Introducción a la Programación"]
    assert c["plan_estudios"][2]["otro_requisito"] is True
    assert c["plan_estudios"][2]["carga_horaria_total"] == "64"
    it1, it2 = c["itinerario"]
    assert [(s["año"], s["semestre"]) for s in it1["semestres"]] == [(1, 1), (1, 2), (2, 1)]
    assert [(s["año"], s["semestre"]) for s in it2["semestres"]] == [(1, 2), (2, 1)]


def test_correlativas_sin_datos():
    assert extraer_correlativas("") == []
    assert extraer_correlativas("Ninguna") == []
    assert extraer_correlativas("Bases de Datos I – Programación II") == ["Bases de Datos I", "Programación II"]


def test_helpers_periodo():
    assert obtener_comision("A0101-COM-02") == "COM-02"
    assert extraer_codigo_y_actividad("BASES DE DATOS II (A0101)") == ("A0101", "BASES DE DATOS II")
    assert detectar_anio_semestre("Oferta 1° semestre 2026") == (2026, 1)
    assert detectar_anio_semestre("Segundo cuatrimestre 2025") == (2025, 2)
    assert detectar_anio_semestre("oferta-2do-semestre-2027.pdf".replace("-", " ")) == (2027, 2)


def test_pdf_definido(tmp_dir):
    r = procesar_pdf(generar(tmp_dir / "d.pdf", DEFINIDO), titulo="Oferta 1° semestre 2026")
    assert r["periodo"] == {"anio": 2026, "semestre": 1, "titulo": "Oferta 1° semestre 2026",
                            "definido": True, "fuente": None}
    bd, prob = r["materias"]
    assert bd["actividad"] == "BASES DE DATOS II" and bd["instancia"] == "Regular"
    assert [c["comision"] for c in bd["comisiones"]] == ["COM-01", "COM-02"]
    assert bd["comisiones"][0]["docentes"] == ["Juan Pérez", "Ana Gómez"]
    assert [d["dia"] for d in bd["comisiones"][0]["dias"]] == ["Lunes", "Jueves"]
    # Fila con celdas combinadas (código/actividad vacíos) se asigna a la materia anterior
    assert [d["dia"] for d in prob["comisiones"][0]["dias"]] == ["Martes", "Jueves"]


def test_pdf_no_definido_sin_duplicados(tmp_dir):
    r = procesar_pdf(generar(tmp_dir / "n.pdf", NO_DEFINIDO))
    assert r["periodo"]["definido"] is False
    assert [m["codigo_actividad"] for m in r["materias"]] == ["A0101", "A0200"]  # antes se duplicaban
    bd = r["materias"][0]
    assert [c["comision"] for c in bd["comisiones"]] == ["COM-01", "COM-02"]
    assert len(bd["comisiones"][0]["dias"]) == 2
    assert bd["comisiones"][0]["dias"][0]["aula"] == "NO ASIGNADO"
