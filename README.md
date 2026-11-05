# Rutas de cursada

Sitio para que un alumno cargue las materias que aprobó y las que está cursando, y obtenga **rutas alternativas para terminar la carrera** según la oferta real de comisiones, sus días y horarios disponibles, el turno que prefiere y cuántas materias quiere cursar por semestre. Las rutas se ven en pantalla (grilla semanal por semestre) o se descargan en **Excel, una hoja por ruta**, con el mismo formato que la planilla manual que inspiró el proyecto.

```
scrapers  ──►  carreras.json / materias_del_periodo.json  ──►  MySQL  ──►  API (FastAPI)  ──►  Front (React)
(plan, correlativas,       (PDF de oferta → comisiones,                    planificador de rutas    grilla, rutas,
 itinerarios)               días, horarios, aulas, docentes)                + export a Excel         estado de materias
```

## Estructura

```
backend/
  scrapper/          scrapers (carreras.py, periodo.py, lector_periodo.py)
  app/
    models.py        modelo de datos (SQLAlchemy, MySQL)
    services/
      importador.py  JSON de los scrapers → base (idempotente)
      planificador.py  motor de rutas
      excel.py       export con una hoja por ruta
      texto.py       normalización y matching de nombres de materias
      horarios.py    parseo de días/horarios
    routers/         endpoints REST
    cli.py           comandos (init-db, importar, demo, schema-sql)
  data/demo/         datos de DEMOSTRACIÓN (no son reales) con el formato de los scrapers
  sql/schema.sql     DDL MySQL generado desde los modelos
  tests/             pytest (scrapers, importador, planificador, API)
frontend/            React + Vite
docker-compose.yml   MySQL para desarrollo
```

## Puesta en marcha

Requisitos: Python 3.11+, Node 18+, y MySQL 8 (o Docker). Sin MySQL configurado el backend usa SQLite automáticamente, lo cual alcanza para probar.

```bash
# 1. Backend
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # completar URLs, DB y ADMIN_TOKEN

# (opcional) MySQL con Docker, desde la raíz del repo:
#   docker compose up -d   y en .env: DB_HOST=127.0.0.1 DB_USER=rutas DB_PASSWORD=rutas

python -m app.cli demo            # crea las tablas y carga datos de demostración
uvicorn app.main:app --reload     # API en http://localhost:8000  (docs en /docs)

# 2. Front (otra terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173 (redirige /api al backend)
```

Para servir todo desde un solo proceso: `npm run build` en `frontend/` y el backend sirve `frontend/dist` automáticamente.

## Cargar datos reales

```bash
cd backend
python -m scrapper.carreras --todas                  # o --carrera "Licenciatura en Sistemas" / menú interactivo
python -m scrapper.periodo                           # descarga el PDF, detecta año/semestre y genera el JSON
python -m app.cli importar-carreras data/carreras.json
python -m app.cli importar-periodo data/materias_del_periodo.json   # --anio 2027 --semestre 1 si no se detectó
```

También se puede subir el **PDF de la oferta directamente** a la API (útil cuando a mitad de año el PDF pasa de "sin aulas" a "con aulas"):

```bash
curl -X POST localhost:8000/api/admin/periodos/importar \
  -H "X-Admin-Token: $ADMIN_TOKEN" -F archivo=@oferta.pdf -F anio=2027 -F semestre=1
```

Las importaciones son idempotentes: reimportar actualiza en el lugar y conserva los ids (las comisiones que eligieron los alumnos no se pierden).

### Los dos formatos de PDF

| | Período **definido** | Período **no definido** (principio / mitad de año) |
|---|---|---|
| Columnas | 13: código, actividad, comisión, inicio, fin, día, horario, docentes, aula, edificación, compartido con, tipo de clase, instancia | ≤5: "ACTIVIDAD (CÓDIGO)", comisión, día, horario, modalidad |
| Aulas/docentes | Sí | `NO ASIGNADO` |

`lector_periodo.py` detecta el formato por la cantidad de columnas y devuelve en ambos casos la misma estructura `materia → comisiones → días`.

## Cómo se calculan las rutas

1. **Pendientes**: el plan de la carrera menos lo aprobado (y, opcionalmente, lo que estás cursando).
2. **Oferta por semestre**: si el período ya está cargado se usa tal cual; si no, se **estima con el último período del mismo semestre** (los horarios suelen repetirse año a año). La interfaz y el Excel indican cuándo un horario es estimado.
3. **Cada semestre** se elige la mejor combinación de materias y comisiones (búsqueda *branch & bound*) que:
   - tenga las correlativas aprobadas,
   - no se superponga,
   - entre en tu disponibilidad horaria,
   - respete el máximo de materias y de horas semanales.
   Las anuales ocupan el mismo horario dos semestres y recién habilitan correlativas al terminar.
4. **Prioridades**: camino crítico (cuántos semestres de correlativas cuelgan de la materia), cantidad de materias que destraba, **escasez** (si el semestre que viene no se dicta o no te encaja, postergarla cuesta un año), afinidad con tu turno preferido y orden del itinerario oficial.
5. **Alternativas**: cada estrategia (*Más rápida*, *Itinerario oficial*, *Más liviana*, *Turno preferido*) se simula muchas veces con variaciones y se refina con búsqueda local (probar "postergar la materia X en el semestre Y", que a veces destraba otra). Se devuelven las mejores rutas distintas, ordenadas por cantidad de semestres.

El resultado también informa el **mínimo teórico** (sólo por correlativas) y si cada ruta cumple tu objetivo de años.

## API

| Método | Ruta | Para qué |
|---|---|---|
| POST | `/api/auth/registro`, `/api/auth/login` | Cuenta y token |
| GET/PUT | `/api/me` | Datos del alumno y carrera |
| GET/PUT | `/api/me/materias` | Estado de cada materia (pendiente / cursando + comisión / aprobada) |
| GET | `/api/me/cursando` | Lo que estoy cursando, con mi comisión y cuántos la cursan |
| GET | `/api/carreras`, `/api/carreras/{id}` | Carreras, plan, correlativas, itinerarios |
| GET | `/api/carreras/{id}/oferta?periodo_id=` | Comisiones del período con alumnos cursando en cada una |
| GET | `/api/periodos` | Períodos cargados |
| POST | `/api/rutas` | Calcula rutas (funciona también sin cuenta enviando `carrera_id` y `aprobadas`) |
| POST | `/api/rutas/excel` | Mismo cálculo, devuelto como `.xlsx` |
| POST | `/api/admin/carreras/importar`, `/api/admin/periodos/importar` | Carga de datos (header `X-Admin-Token`) |

Documentación interactiva en `http://localhost:8000/docs`.

## Tests

```bash
cd backend && python -m pytest
```

Incluyen PDFs sintéticos de ambos formatos, el parseo de una página de carrera, importación idempotente, invariantes del planificador (correlativas, superposiciones, disponibilidad, anuales, límite de horas) y el flujo completo de la API.

---

Proyecto con fines educativos. Respetá los tiempos de espera configurados para no sobrecargar el sitio de la universidad.
