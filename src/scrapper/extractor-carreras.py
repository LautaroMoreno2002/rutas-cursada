import requests
from bs4 import BeautifulSoup
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

def scrapear_carreras(url_carreras):
  """
  Esta función realiza web scraping en el link de las carreras de una universidad

  Args:
        url (str): La URL de la página con la oferta académica.

    Returns:
        list: Una lista de diccionarios con la estructura 
              [{"carrera": "Nombre de la Carrera", "url": "URL del Plan de Estudios"}].
  """
  links_carreras = []

  try:
    print(f"-------- Accediendo a la URL de las carreras: {url_carreras} --------")
    response = requests.get(url_carreras, timeout=15) # Realiza una solicitud GET a la URL con un tiempo de espera de 15 segundos
    response.raise_for_status() # Verifica que la solicitud fue exitosa (código 200)

    resultado = BeautifulSoup(response.content, 'html.parser') # Parsea el contenido HTML de la página

    # En esta página de categoría, las carreras suelen estar listadas como
    # artículos (artículos de blog/noticias) o cards, con enlaces <a> hacia el detalle.
    # Buscamos todos los contenedores de artículos que suelen tener la información de una carrera
    # Clases comunes en WordPress/Blogs: 'post', 'article', 'hentry'  

    contenedores_carreras = resultado.find_all('article', class_=re.compile(r'post|hentry|career-item')) # Buscar artículos con clases comunes
    if not contenedores_carreras:
        # Si no se encuentran artículos, busco enlaces en el contenido general.
        print("Aviso: No se encontraron contenedores de artículos. Buscando enlaces directos...")
        contenido_principal = resultado.find('div', id='content') or resultado.find('main') or resultado
        # Busco enlaces con texto y que apunten a planes de estudio.
        enlaces = contenido_principal.find_all('a', href=re.compile(r'/carrera/'))
    else:
        # Si se encuentran contenedores, extrae el enlace y el título de cada uno
        enlaces = []
        for contenedor in contenedores_carreras:
            # Busco el título del artículo (h2 o h1) y el enlace principal (<a>)
            etiqueta_titulo = contenedor.find('h2') or contenedor.find('h1')
            etiqueta_enlace = contenedor.find('a', href=re.compile(r'/carrera/'))

            if etiqueta_enlace and etiqueta_titulo:
                enlaces.append(etiqueta_enlace) # Uso el <a> directamente 
      
    urls_extraidas = set() # Uso un conjunto para evitar duplicados

    for enlace in enlaces:
        nombre_carrera = enlace.get_text(strip=True) # Obtengo el texto del enlace y limpio espacios
        url_relativa = enlace['href'] # Obtengo el atributo href del enlace
        url_completa = url_relativa if url_relativa.startswith('http') else os.getenv('URL_BASE', 'https://www.ungs.edu.ar') + url_relativa # Construyo la URL completa
        
        if url_completa not in urls_extraidas: # Verifico si la URL ya fue extraída
            urls_extraidas.add(url_completa)
            links_carreras.append({
                "carrera": nombre_carrera,
                "url": url_completa
            })  
  except requests.RequestException as e:
    print(f"Error al acceder a la URL {url_carreras}: {e}")
  except Exception as e:
    print(f"Error al procesar la página {url_carreras}: {e}")
  return links_carreras

if __name__ == "__main__":
   carreras_extraidas = scrapear_carreras(os.getenv('URL_CARRERAS'))
   if carreras_extraidas:
      print(f"Se han extraído {len(carreras_extraidas)} carreras.")
      print(f"Las carreras extraídas son: {carreras_extraidas}")