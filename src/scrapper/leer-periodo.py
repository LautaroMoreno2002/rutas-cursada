import json
import os
import re
import sys

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Excel generado por extractor-periodo.py y JSON de salida.
PERIODO_EXCEL_FILENAME = os.getenv("PERIODO_EXCEL_FILENAME") or "data/periodo.xlsx"
PERIODO_CON_MATERIAS_FILENAME = os.getenv("PERIODO_CON_MATERIAS_FILENAME") or "data/periodo_con_materias.json"


def valor(celda):
    """Celda vacía -> ""."""
    return "" if pd.isna(celda) else celda


def obtener_comision(comision_con_codigo):
    match = re.search(r"COM-\d+", comision_con_codigo)
    return match.group() if match else None


def extraer_codigo_y_actividad(nombre_actividad):
    """
    Separa el código del nombre de la actividad.
    Ej: 'ADMINISTRACIÓN ... (A0075)' -> ('A0075', 'ADMINISTRACIÓN ...')
    """
    if not nombre_actividad:
        return "", ""

    match = re.search(r"\(([^)]+)\)$", nombre_actividad.strip())
    if match:
        actividad = re.sub(r"\s*\([^)]+\)$", "", nombre_actividad).strip()
        return match.group(1), actividad

    return "", nombre_actividad.strip()


def guardar_json(resultado):
    carpeta = os.path.dirname(PERIODO_CON_MATERIAS_FILENAME)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    with open(PERIODO_CON_MATERIAS_FILENAME, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=4)
    print(f"JSON generado correctamente en {PERIODO_CON_MATERIAS_FILENAME}")


def extraer_periodo_definido(df):
    """
    Período con aulas asignadas (13 columnas). Estructura del JSON:
    {
        codigo_actividad, actividad, inicio_dictado, fin_dictado, instancia,
        comisiones: [
            {
                comision, docentes: [] o "",
                dias: [{dia, horario, tipo_clase, aula, edificacion, compartido_con}]
            }
        ]
    }
    """
    resultado = []

    # Elimino las filas de encabezado que se repiten en cada página
    patrones = "Sede Campus:|Códig"
    df = df[~df.astype(str).apply(lambda fila: fila.str.contains(patrones, case=False, na=False)).any(axis=1)]

    # Agrupo por código y materia
    for (codigo, actividad), df_materia in df.groupby([0, 1]):
        if codigo == "Códig o Activid ad" or actividad == "Actividad":
            continue

        materia_json = {
            "codigo_actividad": codigo,
            "actividad": re.sub(r"\s*\(.*?\)\s*", "", actividad).strip(),
            "inicio_dictado": df_materia[3].iloc[0],
            "fin_dictado": df_materia[4].iloc[0],
            "instancia": df_materia[11].iloc[0],
            "comisiones": [],
        }

        # Agrupo por comisión
        for comision, df_comision in df_materia.groupby(2):
            # Docentes de todas las filas, sin repetir y en orden de aparición
            docentes = []
            for celda in df_comision[7].dropna():
                docentes.extend(d.strip() for d in celda.split(","))
            docentes = list(dict.fromkeys(docentes))

            materia_json["comisiones"].append({
                "comision": obtener_comision(comision),
                "docentes": docentes or "",
                "dias": [
                    {
                        "dia": valor(fila[5]),
                        "horario": valor(fila[6]),
                        "tipo_clase": valor(fila[11]),
                        "aula": valor(fila[8]),
                        "edificacion": valor(fila[9]),
                        "compartido_con": valor(fila[10]),
                    }
                    for _, fila in df_comision.iterrows()
                ],
            })

        resultado.append(materia_json)

    guardar_json(resultado)


def extraer_periodo_no_definido(df):
    """
    Período sin aulas asignadas (5 columnas). Estructura del JSON
    (una entrada por cada actividad y comisión):
    {
        codigo_actividad, actividad,
        inicio_dictado: "NO ASIGNADO", fin_dictado: "NO ASIGNADO", modalidad,
        comisiones: [
            {
                comision, docentes: "",
                dias: [{dia, horario, tipo_clase, aula: "NO ASIGNADA",
                        edificacion: "NO ASIGNADA", compartido_con: ""}]
            }
        ]
    }
    """
    resultado = []

    # Elimino encabezados intermedios
    for encabezado in ("Oferta Académica", "Materias Semestrales", "Actividad"):
        df = df[~df[0].astype(str).str.contains(encabezado, na=False)]
    df = df.copy()

    # Propago Actividad, Comisión y Modalidad a las filas que vienen vacías
    df[[0, 1]] = df[[0, 1]].ffill()
    df[4] = df[4].ffill()

    # Agrupo por materia y comisión
    for (nombre_actividad, comision), df_materia in df.groupby([0, 1]):
        codigo, actividad = extraer_codigo_y_actividad(nombre_actividad)
        materia_json = {
            "codigo_actividad": codigo,
            "actividad": actividad,
            "inicio_dictado": "NO ASIGNADO",
            "fin_dictado": "NO ASIGNADO",
            "modalidad": df_materia[4].iloc[0],
            "comisiones": [],
        }

        comision_json = {"comision": comision, "docentes": "", "dias": []}
        for _, fila in df_materia.iterrows():
            comision_json["dias"].append({
                "dia": valor(fila[2]),
                "horario": valor(fila[3]),
                "tipo_clase": valor(fila[4]),
                "aula": "NO ASIGNADA",
                "edificacion": "NO ASIGNADA",
                "compartido_con": "",
            })
            # Se agrega una vez por cada día, como en la versión anterior
            materia_json["comisiones"].append(comision_json)

        resultado.append(materia_json)

    guardar_json(resultado)


def leer_periodo():
    if not os.path.exists(PERIODO_EXCEL_FILENAME):
        sys.exit(f"❌ No existe {PERIODO_EXCEL_FILENAME}. Ejecutá antes extractor-periodo.py")

    df = pd.read_excel(PERIODO_EXCEL_FILENAME)
    df = df.iloc[2:].reset_index(drop=True)  # Quita las primeras 2 filas
    df = df.replace("\n", " ", regex=True)

    if len(df.columns) <= 5:
        print("Leyendo periodo no definido")
        extraer_periodo_no_definido(df)
    else:
        print("Leyendo periodo definido")
        extraer_periodo_definido(df)


if __name__ == "__main__":
    leer_periodo()