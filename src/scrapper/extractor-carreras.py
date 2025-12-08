from time import time
import requests
from bs4 import BeautifulSoup
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

def realizar_solicitud_con_reintentos(url_carreras):
  """
  Realiza una solicitud HTTP con reintentos en caso de fallo temporal.
  """
  for intento in range(int(os.getenv('MAX_RETRIES'))):
    try: 
      response = requests.get(url_carreras, timeout=15)
      response.raise_for_status() # Lanza un error para códigos de estado 4xx/5xx
      return response
    except requests.exceptions.RequestException as e:
      print(f"Error en la solicitud: {e}. Reintentando ({intento + 1}/{os.getenv('MAX_RETRIES')})...")
      if intento < int(os.getenv('MAX_RETRIES')) - 1:
        delay = int(os.getenv('INITIAL_DELAY')) * (2 ** intento)
        print(f"Esperando {delay} segundos antes del próximo intento...")
        time.sleep(delay)
      else:
        raise Exception("No se pudo completar la solicitud después de varios intentos.")
  return None

def limpiar_texto(text, label_pattern, capture_group):
  """
  Limpia y extrae el texto basado en un patrón de etiqueta dado.
  Args:
    text (str): El texto a limpiar.
    label_pattern (str): El patrón regex para buscar la etiqueta.
    capture_group (int): El grupo de captura a extraer.
  Returns:
    str: El texto limpio o "No encontrado" si no se encuentra.
  """
  match = re.search(label_pattern, text, re.IGNORECASE | re.DOTALL)
  if match:
    return re.sub(r'\s+', ' ', match.group(capture_group).strip())
  return "No encontrado"

def scrapear_carreras(url_carreras):
  """
  Esta función realiza web scraping en el link de las carreras de una universidad

  Args:
        url (str): La URL de la página con la oferta académica.
  """
  links_carreras = [] # Lista para almacenar los enlaces de las carreras
  urls_extraidas = set() # Conjunto para evitar duplicados

  try:
    print(f"-------- Accediendo a la URL de las carreras: {url_carreras} --------")
    response = realizar_solicitud_con_reintentos(url_carreras)

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
            link_tag = contenedor.find('a', href=re.compile(r'/carrera/'))
            if link_tag:
                enlaces.append(link_tag) # Uso el <a> directamente 

    for enlace in enlaces:
        nombre_carrera = enlace.get_text(strip=True) # Obtengo el texto del enlace y limpio espacios
        url_relativa = enlace['href'] # Obtengo el atributo href del enlace
        if nombre_carrera and url_relativa and len(nombre_carrera) > 10:
           url_completa = url_relativa if url_relativa.startswith(('http://', 'https://')) else os.getenv('URL_BASE', 'https://www.ungs.edu.ar') + url_relativa # Construyo la URL completa
           nombre_limpio = re.sub(r'\s+', ' ', nombre_carrera).strip() # Limpio el nombre de la carrera
        
        if url_completa not in urls_extraidas: # Verifico si la URL ya fue extraída
            urls_extraidas.add(url_completa)
            links_carreras.append({
                "carrera": nombre_carrera,
                "url": url_completa
            })
    print(f"Carrera encontrada: {nombre_carrera} - URL: {url_completa}") 

  except requests.RequestException as e:
    print(f"Error al acceder a la URL {url_carreras}: {e}")
  except Exception as e:
    print(f"Error al procesar la página {url_carreras}: {e}")
    
  return links_carreras

if __name__ == "__main__":
   carreras_extraidas = scrapear_carreras(os.getenv('URL_CARRERAS'))

    