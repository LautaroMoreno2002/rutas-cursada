import requests
from bs4 import BeautifulSoup
import re
import os
import pdfplumber
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def extraer_periodo(url_periodo):
  try: 
    response = requests.get(url_periodo)
    response.raise_for_status()
    resultado = BeautifulSoup(response.text, 'html.parser')
    titulo = resultado.find("h2")
    print(titulo)
    a = titulo.find("a")
    print(a)
    url_pdf = a['href']
    print(url_pdf)
    return url_pdf

  except Exception as e:
    print(f"Error al obtener el título: {e}")
    return None

def convertir_pdf_a_xlsx(ruta_pdf):
  filas = []

  with pdfplumber.open(ruta_pdf) as pdf:
      for pagina in pdf.pages:
          tablas = pagina.extract_tables()
          for tabla in tablas:
              for fila in tabla:
                  filas.append(fila)

  df = pd.DataFrame(filas)
  df.to_excel(os.getenv("PERIODO_EXCEL_FILENAME"), index=False)


if __name__ == "__main__":
  periodo_extraido = extraer_periodo(os.getenv("URL_PERIODO"))

  pdf_response = requests.get(periodo_extraido)
  with open(os.getenv("PERIODO_PDF_FILENAME"), "wb") as f:
    f.write(pdf_response.content)
  
  convertir_pdf_a_xlsx("periodo.pdf")