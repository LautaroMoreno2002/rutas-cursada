"""Descarga el PDF de la oferta del período y lo convierte en filas / Excel / JSON.

Uso:
    python -m scrapper.periodo                       # descarga, detecta año/semestre y genera JSON
    python -m scrapper.periodo --pdf archivo.pdf --anio 2026 --semestre 1
    python -m scrapper.periodo --excel               # además guarda el Excel crudo (para depurar)
"""
import argparse
import json
import re
from urllib.parse import urljoin

import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup

from . import config
from .lector_periodo import leer_periodo_desde_filas


def extraer_periodo(url_periodo):
    """Devuelve (url_pdf, titulo) del primer <h2><a> de la página del período."""
    try:
        response = requests.get(url_periodo, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        titulo = soup.find("h2")
        a = titulo.find("a") if titulo else None
        if not a or not a.get("href"):
            # Fallback: primer link a un PDF de la página
            a = soup.find("a", href=re.compile(r"\.pdf($|\?)", re.I))
        if not a:
            print("No se encontró el link al PDF del período.")
            return None, None
        texto = (titulo.get_text(" ", strip=True) if titulo else "") or a.get_text(" ", strip=True)
        return urljoin(url_periodo, a["href"]), texto
    except Exception as e:  # noqa: BLE001
        print(f"Error al obtener el período: {e}")
        return None, None


_ORDINALES = {
    "primer": 1, "primero": 1, "1": 1, "1°": 1, "1º": 1, "1er": 1, "i": 1,
    "segundo": 2, "2": 2, "2°": 2, "2º": 2, "2do": 2, "ii": 2,
}


def detectar_anio_semestre(texto):
    """Intenta deducir (año, semestre) del título/URL. Ej: '1° semestre 2026', 'segundo cuatrimestre 2025'."""
    if not texto:
        return None, None
    t = texto.lower()
    anio = None
    m = re.search(r"(20\d{2})", t)
    if m:
        anio = int(m.group(1))
    semestre = None
    m = re.search(r"(primer|primero|segundo|1er|2do|[12]\s*[°º]?|ii|i)\s*(?:semestre|cuatrimestre)", t)
    if m:
        semestre = _ORDINALES.get(m.group(1).replace(" ", ""))
    return anio, semestre


def descargar_pdf(url_pdf, destino):
    resp = requests.get(url_pdf, timeout=60)
    resp.raise_for_status()
    with open(destino, "wb") as f:
        f.write(resp.content)
    return destino


def pdf_a_filas(ruta_pdf):
    """Extrae todas las filas de todas las tablas del PDF (igual que la conversión original a xlsx)."""
    filas = []
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                filas.extend(tabla)
    return filas


def convertir_pdf_a_xlsx(ruta_pdf, destino=None):
    destino = destino or config.ruta("PERIODO_EXCEL_FILENAME", "periodo.xlsx")
    pd.DataFrame(pdf_a_filas(ruta_pdf)).to_excel(destino, index=False)
    return destino


def procesar_pdf(ruta_pdf, anio=None, semestre=None, titulo=None, fuente=None):
    """PDF -> dict {periodo: {...}, materias: [...]} listo para importar."""
    filas = pdf_a_filas(ruta_pdf)
    materias, definido = leer_periodo_desde_filas(filas)
    a, s = detectar_anio_semestre(f"{titulo or ''} {fuente or ''}")
    return {
        "periodo": {
            "anio": anio or a,
            "semestre": semestre or s,
            "titulo": titulo,
            "definido": definido,
            "fuente": fuente,
        },
        "materias": materias,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Descarga y procesa el PDF de oferta del período.")
    parser.add_argument("--pdf", help="Usar un PDF local en lugar de descargarlo")
    parser.add_argument("--anio", type=int)
    parser.add_argument("--semestre", type=int, choices=[1, 2])
    parser.add_argument("--excel", action="store_true", help="Guardar también el Excel crudo")
    parser.add_argument("--salida", help="JSON de salida")
    args = parser.parse_args(argv)

    titulo = fuente = None
    ruta_pdf = args.pdf
    if not ruta_pdf:
        if not config.URL_PERIODO:
            raise SystemExit("❌ Falta URL_PERIODO en el .env (o pasá --pdf)")
        fuente, titulo = extraer_periodo(config.URL_PERIODO)
        if not fuente:
            raise SystemExit("❌ No se pudo obtener el PDF del período")
        ruta_pdf = config.ruta("PERIODO_PDF_FILENAME", "periodo.pdf")
        print(f"⬇️  Descargando {fuente}")
        descargar_pdf(fuente, ruta_pdf)

    if args.excel:
        print(f"📄 Excel crudo: {convertir_pdf_a_xlsx(ruta_pdf)}")

    resultado = procesar_pdf(ruta_pdf, args.anio, args.semestre, titulo, fuente)
    p = resultado["periodo"]
    if not p["anio"] or not p["semestre"]:
        print("⚠️  No se pudo deducir año/semestre: usá --anio y --semestre antes de importar.")

    salida = args.salida or config.ruta("PERIODO_CON_MATERIAS_FILENAME", "materias_del_periodo.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=4)
    tipo = "definido (con aulas/docentes)" if p["definido"] else "no definido (sin aulas/docentes)"
    print(f"✅ {len(resultado['materias'])} materias, período {tipo} -> {salida}")
    return resultado


if __name__ == "__main__":
    main()
