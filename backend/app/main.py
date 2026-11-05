"""API de Rutas de Cursada.

    uvicorn app.main:app --reload        (desde la carpeta backend/)
    Documentación interactiva: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .database import crear_tablas
from .routers import admin, alumnos, carreras, rutas

FRONT_DIST = config.BACKEND_DIR.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    crear_tablas()
    yield


app = FastAPI(title="Rutas de Cursada", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (carreras.router, alumnos.router, rutas.router, admin.router):
    app.include_router(r, prefix="/api")


@app.get("/api/salud")
def salud():
    return {"ok": True}


# Si el front está compilado (npm run build), se sirve desde el mismo servidor
if FRONT_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONT_DIST / "assets"), name="assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    def spa(ruta: str):
        archivo = FRONT_DIST / ruta
        if ruta and archivo.is_file() and Path(archivo).resolve().is_relative_to(FRONT_DIST.resolve()):
            return FileResponse(archivo)
        return FileResponse(FRONT_DIST / "index.html")
