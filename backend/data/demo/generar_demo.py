"""Genera datos de DEMOSTRACIÓN con el mismo formato que producen los scrapers.

NO son datos reales de la universidad: sirven para probar la API y el front
sin tener que scrapear. Para usar datos reales correr los scrapers (ver README).

    python data/demo/generar_demo.py
"""
import json
import random
from pathlib import Path

AQUI = Path(__file__).resolve().parent

# (nombre, régimen, hs semanales, correlativas (texto como viene del sitio), semestre sugerido)
PLAN = [
    ("Introducción a la Programación", "Semestral", 8, [], 1),
    ("Taller de Lectura y Escritura", "Semestral", 4, [], 1),
    ("Matemática General", "Semestral", 6, [], 1),
    ("Organización del Computador I", "Semestral", 6, [], 1),
    ("Programación I", "Semestral", 8, ["Introd. a la Programación"], 2),
    ("Álgebra Lineal", "Semestral", 6, ["Matemática General"], 2),
    ("Lógica y Teoría de Números", "Semestral", 6, ["Matemática General"], 2),
    ("Organización del Computador II", "Semestral", 6, ["Organización del Computador I"], 2),
    ("Programación II", "Semestral", 8, ["Programación I"], 3),
    ("Cálculo para Computación", "Semestral", 6, ["Álgebra Lineal"], 3),
    ("Bases de Datos I", "Semestral", 6, ["Programación I"], 3),
    ("Sistemas Operativos y Redes I", "Semestral", 6, ["Organización del Computador II"], 3),
    ("Programación III", "Semestral", 8, ["Programación II"], 4),
    ("Ingeniería de Software I", "Semestral", 6, ["Programación II"], 4),
    ("Probabilidad y Estadística", "Semestral", 6, ["Cálculo para Computación"], 4),
    ("Sistemas Operativos y Redes II", "Semestral", 6, ["Sistemas Operativos y Redes I"], 4),
    ("Bases de Datos II", "Semestral", 8, ["Bases de Datos I", "Programación II"], 5),
    ("Ingeniería de Software II", "Semestral", 6, ["Ingeniería de Software I"], 5),
    ("Especificaciones y Verificación de Software", "Semestral", 6, ["Programación III", "Lógica y Teoría de Números"], 5),
    ("Proyecto Profesional I", "Semestral", 8, ["Ingeniería de Software I", "Bases de Datos I"], 5),
    ("Proyecto Profesional II", "Semestral", 8, ["Proyecto Profesional I", "Ingeniería de Software II"], 6),
    ("Modelado y Optimización", "Semestral", 6, ["Probabilidad y Estadística"], 6),
    ("Teoría de la Computación", "Semestral", 6, ["Programación III", "Lógica y Teoría de Números"], 6),
    ("Informática y Sociedad", "Semestral", 4, [], 6),
    ("Gestión de Proyectos", "Semestral", 6, ["Ingeniería de Software II", "Proyecto Profesional I"], 7),
    ("Seguridad Informática", "Semestral", 6, ["Sistemas Operativos y Redes II"], 7),
    ("Lenguajes Formales y Autómatas", "Semestral", 6, ["Teoría de la Computación"], 7),
    ("Práctica Profesional Supervisada", "Semestral", 8, ["Proyecto Profesional II", "Bases de Datos II"], 8),
    ("Taller de Tesina", "Anual", 4, ["Proyecto Profesional II", "Bases de Datos II"], 8),
]
OTROS = [
    ("Taller de Utilitarios", "Semestral", 2, []),
    ("Inglés Lectocomprensión I", "Semestral", 4, []),
    ("Inglés Lectocomprensión II", "Semestral", 4, ["Inglés Lectocomprensión I"]),
    ("Inglés Lectocomprensión III", "Semestral", 4, ["Inglés Lectocomprensión II"]),
]


def carreras():
    plan = [
        {
            "asignatura": n, "regimen_de_cursada": r, "carga_horaria_semanal": str(h),
            "carga_horaria_total": str(h * 16 * (2 if r == "Anual" else 1)), "correlativas": c,
            "otro_requisito": False,
        }
        for n, r, h, c, _ in PLAN
    ] + [
        {
            "asignatura": n, "regimen_de_cursada": r, "carga_horaria_semanal": str(h),
            "carga_horaria_total": str(h * 16), "correlativas": c, "otro_requisito": True,
        }
        for n, r, h, c in OTROS
    ]

    def itinerario(titulo, inicio):
        semestres, sem, anio = [], inicio, 1
        for orden in range(1, 9):
            semestres.append({
                "orden": orden, "año": anio, "semestre": sem,
                "materias": [n for n, *_, s in PLAN if s == orden],
            })
            sem, anio = (2, anio) if sem == 1 else (1, anio + 1)
        return {"itinerario_titulo": titulo, "semestres": semestres}

    return [{
        "carrera": "Licenciatura en Sistemas",
        "url_plan_estudios": "https://www.ejemplo.edu.ar/carrera/licenciatura-en-sistemas",
        "duracion": "4 años",
        "titulo_oficial": "Licenciado/a en Sistemas",
        "modalidad": "Presencial",
        "ambitos_desempeno": ["Empresas de desarrollo de software", "Organismos públicos", "Investigación"],
        "plan_estudios": plan,
        "itinerario": [
            itinerario("Itinerario sugerido con inicio en el primer semestre", 1),
            itinerario("Itinerario sugerido con inicio en el segundo semestre", 2),
        ],
    }]


DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
FRANJAS_NOCHE = ["18:00 a 22:00"]
FRANJAS_DIA = ["08:00 a 12:00", "09:00 a 13:00", "14:00 a 18:00"]
DOCENTES = ["Laura Benítez", "Martín Sosa", "Carla Medina", "Diego Ferrari", "Paula Ríos", "Hernán Castro",
            "Julieta Vega", "Sergio Luna", "Andrea Molina", "Pablo Ortiz"]


def _comision(rng, hs, franjas, definido, rotacion=None):
    """Una comisión de `hs` horas semanales repartidas en bloques de 4hs (o 2hs)."""
    bloques = []
    k = max(1, min(3, round(hs / 4)))
    if rotacion is None:
        dias = rng.sample(DIAS, k=k)
    else:  # reparte los días de la comisión nocturna principal para que no choquen todas
        dias = [DIAS[(rotacion + j * 2) % 5] for j in range(k)]
    restantes = hs
    for d in sorted(dias, key=DIAS.index):
        franja = rng.choice(franjas)
        if restantes <= 2:
            ini = int(franja[:2])
            franja = f"{ini:02d}:00 a {ini + 2:02d}:00"
        bloques.append({
            "dia": d, "horario": franja if definido else franja.replace(":00", ""),
            "tipo_clase": rng.choice(["Teórica", "Práctica", "Teórico-Práctica"]) if definido else "Presencial",
            "aula": f"Aula {rng.randint(1, 20)}" if definido else "NO ASIGNADO",
            "edificacion": f"Módulo {rng.randint(1, 7)}" if definido else "NO ASIGNADO",
            "compartido_con": "",
        })
        restantes -= 4
    return bloques


def periodo(anio, semestre, definido, semilla):
    rng = random.Random(semilla)
    materias = []
    todas = [(n, h, s) for n, _, h, _, s in PLAN] + [(n, h, 0) for n, _, h, _ in OTROS]
    for i, (nombre, hs, sem_sugerido) in enumerate(todas):
        # Las materias de los primeros años se dictan siempre; las avanzadas sólo en su semestre
        if sem_sugerido >= 5 and (sem_sugerido % 2 == 1) != (semestre == 1) and nombre != "Taller de Tesina":
            if rng.random() < 0.6:
                continue
        if nombre == "Taller de Tesina" and semestre == 2:
            continue  # anual: inicia en el 1er semestre
        n_com = 3 if sem_sugerido <= 2 else (2 if sem_sugerido <= 4 else 1)
        comisiones = []
        for c in range(1, n_com + 1):
            franjas = FRANJAS_NOCHE if c == 1 or rng.random() < 0.4 else FRANJAS_DIA
            if nombre == "Taller de Tesina":
                bloques = [{"dia": "Viernes", "horario": "18:00 a 22:00" if definido else "18 a 22",
                            "tipo_clase": "Taller" if definido else "Presencial",
                            "aula": "Aula 12" if definido else "NO ASIGNADO",
                            "edificacion": "Módulo 2" if definido else "NO ASIGNADO", "compartido_con": ""}]
            elif nombre == "Informática y Sociedad" and c == 1:
                bloques = [{"dia": "Sábado", "horario": "09:00 a 13:00" if definido else "9 a 13",
                            "tipo_clase": "Teórica" if definido else "Presencial",
                            "aula": "Aula 3" if definido else "NO ASIGNADO",
                            "edificacion": "Módulo 1" if definido else "NO ASIGNADO", "compartido_con": ""}]
            else:
                bloques = _comision(rng, hs, franjas, definido, rotacion=(i * 3 + semestre) if c == 1 else None)
            comisiones.append({
                "comision": f"COM-{c:02d}",
                "docentes": rng.sample(DOCENTES, 2) if definido else [],
                "dias": bloques,
            })
        materias.append({
            "codigo_actividad": f"A{1000 + i:04d}",
            "actividad": nombre.upper(),
            "inicio_dictado": f"16/03/{anio}" if semestre == 1 and definido else
                              (f"10/08/{anio}" if definido else "NO ASIGNADO"),
            "fin_dictado": f"04/07/{anio}" if semestre == 1 and definido else
                           (f"05/12/{anio}" if definido else "NO ASIGNADO"),
            "instancia": "Regular" if definido else "",
            "modalidad": "" if definido else "Presencial",
            "comisiones": comisiones,
        })
    return {
        "periodo": {"anio": anio, "semestre": semestre, "titulo": f"Oferta {semestre}° semestre {anio} (DEMO)",
                    "definido": definido, "fuente": None},
        "materias": materias,
    }


if __name__ == "__main__":
    (AQUI / "carreras.json").write_text(json.dumps(carreras(), ensure_ascii=False, indent=2), encoding="utf-8")
    for anio, sem, definido in [(2026, 2, True), (2027, 1, False)]:
        destino = AQUI / f"periodo_{anio}_{sem}.json"
        destino.write_text(json.dumps(periodo(anio, sem, definido, anio * 10 + sem), ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print("Datos demo generados en", AQUI)
