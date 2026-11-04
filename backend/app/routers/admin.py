"""Carga de datos scrapeados. Requiere el header X-Admin-Token = ADMIN_TOKEN."""
import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..auth import solo_admin
from ..database import get_db
from ..models import Periodo
from ..services.importador import importar_carreras, importar_periodo

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(solo_admin)])


async def _json(archivo: UploadFile):
    try:
        return json.loads((await archivo.read()).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(400, f"JSON inválido: {e}")


@router.post("/carreras/importar")
async def importar_carreras_endpoint(archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    """Sube el carreras.json generado por `python -m scrapper.carreras`."""
    data = await _json(archivo)
    if not isinstance(data, list):
        raise HTTPException(400, "Se esperaba una lista de carreras")
    return importar_carreras(db, data)


@router.post("/periodos/importar")
async def importar_periodo_endpoint(
    archivo: UploadFile = File(..., description="PDF de la oferta o materias_del_periodo.json"),
    anio: int | None = Form(default=None),
    semestre: int | None = Form(default=None),
    titulo: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Importa (o reimporta) la oferta de un período desde el PDF original o desde el JSON."""
    nombre = (archivo.filename or "").lower()
    if nombre.endswith(".pdf"):
        from scrapper.periodo import procesar_pdf

        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "periodo.pdf"
            ruta.write_bytes(await archivo.read())
            data = procesar_pdf(ruta, anio, semestre, titulo or archivo.filename, archivo.filename)
    else:
        data = await _json(archivo)
    try:
        return importar_periodo(db, data, anio, semestre, titulo)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/periodos/{periodo_id}", status_code=204)
def borrar_periodo(periodo_id: int, db: Session = Depends(get_db)):
    periodo = db.get(Periodo, periodo_id)
    if periodo is None:
        raise HTTPException(404, "Período no encontrado")
    db.delete(periodo)
    db.commit()
