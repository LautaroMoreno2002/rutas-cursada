import requests
import os
import pandas as pd
import openpyxl
import re
import json


df = pd.read_excel("./src/data/periodo.xlsx")
df = df.iloc[2:].reset_index(drop=True)  # Quita las primeras 2 filas
df = df.replace("\n", " ", regex=True)
print(df)

print(df[1])

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
            "docentes": df_comision[7].dropna().unique().tolist(),
            "dias": []
        }
        # Recorro los días y horarios
        for _, fila in df_comision.iterrows():
            compartido = "" if pd.isna(fila[10]) else fila[10]
            dia_json = {
                "dia": fila[5],
                "horario": fila[6],
                "tipo_clase": fila[11],
                "aula": fila[8],
                "edificacion": fila[9],
                "compartido_con": compartido
            }

            comision_json["dias"].append(dia_json)

        materia_json["comisiones"].append(comision_json)

        print(df_comision)
    

    resultado.append(materia_json)

with open("materias.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=4)