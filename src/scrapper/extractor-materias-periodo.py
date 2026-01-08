import requests
import os
import pandas as pd
import openpyxl
import re


df = pd.read_excel("./src/data/periodo.xlsx")
df = df.iloc[2:].reset_index(drop=True)  # Quita las primeras 2 filas
df = df.replace("\n", " ", regex=True)
print(df)

print(df)