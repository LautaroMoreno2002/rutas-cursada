import os
import sys
from urllib.parse import urljoin

import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Configuración leída del .env. Solo URL_PERIODO es obligatoria;
# los archivos de salida usan estos valores por defecto si no están definidos.
URL_PERIODO = os.getenv("URL_PERIODO")
PERIODO_PDF_FILENAME = os.getenv("PERIODO_PDF_FILENAME") or "data/periodo.pdf"
PERIODO_EXCEL_FILENAME = os.getenv("PERIODO_EXCEL_FILENAME") or "data/periodo.xlsx"
PERIODO_CSV_FILENAME = os.getenv("PERIODO_CSV_FILENAME") or "data/periodo.csv"

COLUMNAS = [
    "codigo_actividad",
    "actividad",
    "comision",
    "inicio_dictado",
    "fin_dictado",
    "dia",
    "horario",
    "docentes",
    "aula",
    "edificacion",
    "compartido_con",
    "tipo_clase",
    "instancia",
]


def crear_carpeta(ruta_archivo):
    """Crea la carpeta del archivo si no existe."""
    carpeta = os.path.dirname(ruta_archivo)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)


def extraer_periodo(url_periodo):
    """Devuelve la URL del PDF enlazado en el primer <h2> de la página."""
    try:
        response = requests.get(url_periodo, timeout=15)
        response.raise_for_status()
        resultado = BeautifulSoup(response.text, "html.parser")

        titulo = resultado.find("h2")
        a = titulo.find("a") if titulo else None
        if not a or not a.get("href"):
            raise ValueError("no se encontró el enlace al PDF en el primer <h2> de la página")

        url_pdf = urljoin(url_periodo, a["href"])
        print(f"📄 {titulo.get_text(strip=True)}: {url_pdf}")
        return url_pdf

    except Exception as e:
        print(f"Error al obtener el título: {e}")
        return None


def descargar_pdf(url_pdf, ruta_pdf):
    response = requests.get(url_pdf, timeout=60)
    response.raise_for_status()
    crear_carpeta(ruta_pdf)
    with open(ruta_pdf, "wb") as f:
        f.write(response.content)


def convertir_pdf_a_xlsx(ruta_pdf):
    """Vuelca todas las filas de todas las tablas del PDF a un Excel, sin modificarlas."""
    filas = []
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                filas.extend(tabla)

    crear_carpeta(PERIODO_EXCEL_FILENAME)
    pd.DataFrame(filas).to_excel(PERIODO_EXCEL_FILENAME, index=False)


def convertir_pdf_a_csv(ruta_pdf):
    """Extrae las tablas del PDF a un CSV limpio con las 13 columnas de COLUMNAS."""
    filas_limpias = []

    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            tablas = pagina.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 3,
                "join_tolerance": 3,
            })

            for tabla in tablas:
                for fila in tabla:
                    if not fila:
                        continue

                    # Limpiar celdas
                    fila = [celda.replace("\n", " ").strip() if celda else "" for celda in fila]

                    # Ignorar filas vacías
                    if all(c == "" for c in fila):
                        continue

                    # Normalizar cantidad de columnas (completa o recorta)
                    fila = (fila + [""] * len(COLUMNAS))[:len(COLUMNAS)]
                    filas_limpias.append(fila)

    crear_carpeta(PERIODO_CSV_FILENAME)
    pd.DataFrame(filas_limpias, columns=COLUMNAS).to_csv(
        PERIODO_CSV_FILENAME, index=False, encoding="utf-8"
    )


if __name__ == "__main__":
    if not URL_PERIODO:
        sys.exit("❌ Falta URL_PERIODO en el archivo .env")

    url_pdf = extraer_periodo(URL_PERIODO)
    if not url_pdf:
        sys.exit("❌ No se pudo obtener el PDF del período.")

    try:
        descargar_pdf(url_pdf, PERIODO_PDF_FILENAME)
    except requests.exceptions.RequestException as e:
        sys.exit(f"❌ Error al descargar el PDF: {e}")
    print(f"💾 PDF guardado en {PERIODO_PDF_FILENAME}")

    convertir_pdf_a_xlsx(PERIODO_PDF_FILENAME)
    print(f"💾 Excel guardado en {PERIODO_EXCEL_FILENAME}")