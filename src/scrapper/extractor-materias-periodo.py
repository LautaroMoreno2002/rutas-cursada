import requests
import os
import pandas as pd
import openpyxl
import re
import json
from dotenv import load_dotenv

load_dotenv()

df = pd.read_excel("./src/data/periodo.xlsx")
df = df.iloc[2:].reset_index(drop=True)  # Quita las primeras 2 filas
df = df.replace("\n", " ", regex=True)

"""
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
            comision_json = {
                "comision": comision,
                "docentes": "" if df_comision[7].size <= 0 else df_comision[7].dropna().unique().tolist(),
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