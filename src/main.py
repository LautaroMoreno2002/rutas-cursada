import json

with open("src/data/carreras.json", "r", encoding="utf-8") as f:
    carreras = json.load(f)

with open("src/data/materias_del_periodo.json", "r", encoding="utf-8") as f:
    materias_periodo = json.load(f)

carrera_buscada = "Tecnicatura universitaria en informática"

# 1. Buscar la carrera
carrera_obj = None
for c in carreras:
    if c["carrera"].lower() == carrera_buscada.lower():
        carrera_obj = c
        break

if not carrera_obj:
    print("Carrera no encontrada")
    exit()

print("Carrera encontrada:", carrera_obj["carrera"])

# 2. Sacar las materias del plan de estudios
materias_plan = {
    m["asignatura"].strip().lower()
    for m in carrera_obj["plan_estudios"]
}

# 3. Filtrar materias del período que pertenezcan a la carrera
materias_de_la_carrera = [
    m for m in materias_periodo
    if m["actividad"].strip().lower() in materias_plan
]

print(f"Materias del período para {carrera_buscada}: {len(materias_de_la_carrera)}")

for m in materias_de_la_carrera:
    print("-", m["actividad"], "|", m["codigo_actividad"])
