import requests
import os
import pandas as pd
# import openpyxl
import re
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def extraer_periodo_definido(df):
    """
    ESTRUCTURA DEL JSON (para el periodo definido con aulas)
    {
        codigo_actividad: "",
        actividad: "",
        inicio_dictado: "",
        fin_dictado: "",
        instancia: "",
        comisiones: [
            {
                comision: "",
                docentes: [""]
                dias: [
                    {
                        dia: "",
                        horario: "",
                        tipo_clase: "",
                        aula: "",
                        edificacion: "",
                        compartido_con: ""                    
                    }
                ]
            }
        ]
    }
    """
    resultado = []

    # Agrupo por código y materia
    for (codigo, actividad), df_materia in df.groupby([0, 1]):
        if codigo != "Códig o Activid ad" and actividad != "Actividad":
            actividad = re.sub(r'\s*\(.*?\)\s*', '', actividad).strip()
            materia_json = {
                "codigo_actividad": codigo,
                "actividad": actividad,
                "inicio_dictado": df_materia[3].iloc[0],
                "fin_dictado": df_materia[4].iloc[0],
                "instancia": df_materia[12].iloc[0],
                "comisiones": []
            }
            # Agrupo por comisión
            for (comision), df_comision in df_materia.groupby(2):
                docentes = []
                for valor in df_comision[7].dropna():
                    partes = [d.strip() for d in valor.split(",")]
                    docentes.extend(partes)

                docentes = list(set(docentes))  # quitar repetidos

                comision_json = {
                    "comision": comision,
                    "docentes": "" if len(docentes) <= 0 else docentes,
                    "dias": []
                }
                # Recorro los días y horarios
                for _, fila in df_comision.iterrows():
                    dia_json = {
                        "dia": "" if pd.isna(fila[5]) else fila[5],
                        "horario": "" if pd.isna(fila[6]) else fila[6],
                        "tipo_clase": "" if pd.isna(fila[11]) else fila[11],
                        "aula": "" if pd.isna(fila[8]) else fila[8],
                        "edificacion": "" if pd.isna(fila[9]) else fila[9],
                        "compartido_con": "" if pd.isna(fila[10]) else fila[10]
                    }

                    comision_json["dias"].append(dia_json)

                materia_json["comisiones"].append(comision_json)

            resultado.append(materia_json)

    with open(os.getenv("PERIODO_CON_MATERIAS_FILENAME"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=4)

def extraer_codigo_y_actividad(nombre_actividad):
    """
    Extrae el código de la actividad desde el nombre.
    Ej: 'ADMINISTRACIÓN ... (A0075)'
    """
    if not nombre_actividad:
        return "", ""

    match = re.search(r"\(([^)]+)\)$", nombre_actividad.strip())
    if match:
        codigo = match.group(1)
        actividad = re.sub(r"\s*\([^)]+\)$", "", nombre_actividad).strip()
        return codigo, actividad

    return "", nombre_actividad.strip()

def extraer_periodo_no_definido(df):
    """
    ESTRUCTURA DEL JSON (para el periodo no definido)
    {
        codigo_actividad: "",
        actividad: "",
        inicio_dictado: "NO DEFINIDO",
        fin_dictado: "NO DEFINIDO",
        instancia: "NO DEFINIDO",
        modalidad: "",
        comisiones: [
            {
                comision: "",
                docentes: ["NO DEFINIDO"]
                dias: [
                    {
                        dia: "",
                        horario: "",
                        aula: "NO DEFINIDO",
                        edificacion: "NO DEFINIDO",
                        compartido_con: "NO DEFINIDO"                    
                    }
                ]
            }
        ]
    }
    """
    resultado = []
    # Propaga Actividad y Comisión
    df[[0, 1]] = df[[0, 1]].ffil()

    # Opcional: si modalidad también viene vacía
    df[4] = df[4].ffill()
    
    # Elimina encabezados intermedios
    df = df[~df[0].astype(str).str.contains("Oferta Académica", na=False)]
    df = df[~df[0].astype(str).str.contains("Actividad", na=False)]

    # Agrupo por materia
    for (actividad, comision), df_materia in df.groupby([0, 1]):
        (codigo, actividad) = extraer_codigo_y_actividad(actividad)
        materia_json = {
            "codigo_actividad": codigo,
            "actividad": actividad,
            "inicio_dictado": "NO ASIGNADO",
            "fin_dictado": "NO ASIGNADO",
            "comisiones": []
        }
        
        

    # Realizo múltiples copias para ir depurando los resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    df.to_excel(
        f"oferta_expandida_{timestamp}.xlsx",
        index=False
    )

    with open(os.getenv("PERIODO_CON_MATERIAS_FILENAME"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=4)

    print("JSON generado correctamente")

df = pd.read_excel("./src/data/periodo.xlsx")
df = df.iloc[2:].reset_index(drop=True)  # Quita las primeras 2 filas
df = df.replace("\n", " ", regex=True)
extraer_periodo_no_definido(df)