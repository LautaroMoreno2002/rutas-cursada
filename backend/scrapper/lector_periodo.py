"""Convierte las filas del PDF de oferta en materias con comisiones.

Hay dos formatos de PDF:

* Período DEFINIDO (13 columnas, con aulas y docentes):
  0 código | 1 actividad | 2 comisión | 3 inicio | 4 fin | 5 día | 6 horario |
  7 docentes | 8 aula | 9 edificación | 10 compartido con | 11 tipo clase | 12 instancia

* Período NO DEFINIDO (≤5 columnas, principio/mitad de año, sin aulas ni docentes):
  0 "ACTIVIDAD (CÓDIGO)" | 1 comisión | 2 día | 3 horario | 4 modalidad

Ambos se devuelven con la misma estructura:
{
    codigo_actividad, actividad, inicio_dictado, fin_dictado, instancia, modalidad,
    comisiones: [{ comision, docentes: [str], dias: [{dia, horario, tipo_clase, aula,
                                                       edificacion, compartido_con}] }]
}
"""
import json
import re

import pandas as pd

COLUMNAS_DEFINIDO = [
    "codigo_actividad", "actividad", "comision", "inicio_dictado", "fin_dictado", "dia",
    "horario", "docentes", "aula", "edificacion", "compartido_con", "tipo_clase", "instancia",
]

PATRONES_ENCABEZADO = [
    "Sede Campus:", "Códig", "Oferta Académica", "Materias Semestrales", "Materias Anuales",
]

NO_ASIGNADO = "NO ASIGNADO"


def obtener_comision(comision_con_codigo):
    """'A0075-COM-01' -> 'COM-01'. Si no matchea devuelve el texto original."""
    if comision_con_codigo is None or (isinstance(comision_con_codigo, float) and pd.isna(comision_con_codigo)):
        return ""
    texto = str(comision_con_codigo).strip()
    match = re.search(r"COM-?\s*\d+", texto, re.I)
    return match.group().upper().replace(" ", "") if match else texto


def extraer_codigo_y_actividad(nombre_actividad):
    """'ADMINISTRACIÓN ... (A0075)' -> ('A0075', 'ADMINISTRACIÓN ...')."""
    if not nombre_actividad:
        return "", ""
    texto = str(nombre_actividad).strip()
    match = re.search(r"\(([^)]+)\)\s*$", texto)
    if match:
        return match.group(1).strip(), re.sub(r"\s*\([^)]+\)\s*$", "", texto).strip()
    return "", texto


def _texto(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return re.sub(r"\s+", " ", str(valor)).strip()


def _separar_docentes(valores):
    docentes = []
    for valor in valores:
        for d in re.split(r"[,;/]", _texto(valor)):
            d = d.strip()
            if d and d not in docentes:  # sin repetidos, manteniendo el orden
                docentes.append(d)
    return docentes


def _limpiar(df):
    df = df.copy()
    df = df.map(lambda v: _texto(v) if v is not None else "")
    df = df.replace("", pd.NA)
    # Elimino filas que sean encabezados o títulos repetidos en cada página
    patron = "|".join(re.escape(p) for p in PATRONES_ENCABEZADO)
    es_encabezado = df.astype(str).apply(
        lambda fila: fila.str.contains(patron, case=False, na=False)
    ).any(axis=1)
    return df[~es_encabezado]


def _columnas_con_datos(df):
    return [c for c in df.columns if df[c].replace("", pd.NA).notna().any()]


def extraer_periodo_definido(df):
    df = _limpiar(df)
    df = df.reindex(columns=range(13))
    # Encabezado "Actividad"/"Día" y títulos sin día ni horario
    df = df[~df[1].astype(str).str.fullmatch(r"(?i)actividad", na=False)]
    df = df[df[5].notna() | df[6].notna()]
    df = df[~df[5].astype(str).str.fullmatch(r"(?i)d[ií]a", na=False)]
    # Celdas combinadas en el PDF -> vienen vacías en las filas siguientes
    df[[0, 1, 2, 3, 4, 12]] = df[[0, 1, 2, 3, 4, 12]].ffill()

    resultado = []
    for (codigo, actividad), df_materia in df.groupby([0, 1], sort=False):
        actividad = re.sub(r"\s*\(.*?\)\s*", " ", str(actividad)).strip()
        materia = {
            "codigo_actividad": _texto(codigo),
            "actividad": actividad,
            "inicio_dictado": _texto(df_materia[3].iloc[0]) or NO_ASIGNADO,
            "fin_dictado": _texto(df_materia[4].iloc[0]) or NO_ASIGNADO,
            "instancia": _texto(df_materia[12].iloc[0]),  # antes leía la col. 11 (tipo de clase)
            "modalidad": "",
            "comisiones": [],
        }
        for comision, df_comision in df_materia.groupby(2, sort=False):
            materia["comisiones"].append({
                "comision": obtener_comision(comision),
                "docentes": _separar_docentes(df_comision[7].dropna()),
                "dias": [
                    {
                        "dia": _texto(fila[5]),
                        "horario": _texto(fila[6]),
                        "tipo_clase": _texto(fila[11]),
                        "aula": _texto(fila[8]),
                        "edificacion": _texto(fila[9]),
                        "compartido_con": _texto(fila[10]),
                    }
                    for _, fila in df_comision.iterrows()
                ],
            })
        resultado.append(materia)
    return resultado


def extraer_periodo_no_definido(df):
    df = _limpiar(df)
    df = df.reindex(columns=range(5))
    df = df[~df[0].astype(str).str.fullmatch(r"(?i)actividad", na=False)]
    df = df[df[2].notna() | df[3].notna()]
    df = df[~df[2].astype(str).str.fullmatch(r"(?i)d[ií]a", na=False)]
    df[[0, 1, 4]] = df[[0, 1, 4]].ffill()

    resultado = []
    # Antes se agrupaba por (actividad, comisión) y se agregaba la materia una vez
    # por fila, generando materias duplicadas. Ahora: materia -> comisiones -> días.
    for actividad_raw, df_materia in df.groupby(0, sort=False):
        codigo, actividad = extraer_codigo_y_actividad(actividad_raw)
        materia = {
            "codigo_actividad": codigo,
            "actividad": actividad,
            "inicio_dictado": NO_ASIGNADO,
            "fin_dictado": NO_ASIGNADO,
            "instancia": "",
            "modalidad": _texto(df_materia[4].iloc[0]),
            "comisiones": [],
        }
        for comision, df_comision in df_materia.groupby(1, sort=False):
            materia["comisiones"].append({
                "comision": obtener_comision(comision),
                "docentes": [],
                "dias": [
                    {
                        "dia": _texto(fila[2]),
                        "horario": _texto(fila[3]),
                        "tipo_clase": _texto(fila[4]),
                        "aula": NO_ASIGNADO,
                        "edificacion": NO_ASIGNADO,
                        "compartido_con": "",
                    }
                    for _, fila in df_comision.iterrows()
                ],
            })
        resultado.append(materia)
    return resultado


def es_periodo_definido(df):
    return len(_columnas_con_datos(df)) > 5


def leer_periodo_desde_dataframe(df):
    """Devuelve (materias, definido)."""
    if es_periodo_definido(df):
        return extraer_periodo_definido(df), True
    return extraer_periodo_no_definido(df), False


def leer_periodo_desde_filas(filas):
    df = pd.DataFrame([f for f in filas if f])
    if df.empty:
        return [], False
    return leer_periodo_desde_dataframe(df)


def leer_periodo_desde_excel(ruta_excel):
    """Compatibilidad con el flujo original (PDF -> periodo.xlsx -> JSON)."""
    df = pd.read_excel(ruta_excel, header=None)
    return leer_periodo_desde_dataframe(df)


if __name__ == "__main__":
    import sys

    from . import config

    ruta_excel = sys.argv[1] if len(sys.argv) > 1 else config.ruta("PERIODO_EXCEL_FILENAME", "periodo.xlsx")
    materias, definido = leer_periodo_desde_excel(ruta_excel)
    salida = config.ruta("PERIODO_CON_MATERIAS_FILENAME", "materias_del_periodo.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"periodo": {"definido": definido}, "materias": materias}, f, ensure_ascii=False, indent=4)
    print(f"JSON generado correctamente: {len(materias)} materias -> {salida}")
