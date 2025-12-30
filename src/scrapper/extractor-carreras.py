import time
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

def limpiar_texto(text, label_pattern=r"(.*)", capture_group=1):
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

def extraer_correlativas(correlativas_str):
    if not correlativas_str or correlativas_str.lower() in [
        '', 'ninguna', 'no tiene', 'sin correlativas'
    ]:
        return 'No tiene correlativas'

    texto = limpiar_texto(correlativas_str)

    if texto == "No encontrado":
        return 'No tiene correlativas'

    # 1️⃣ Separar materias pegadas por números romanos
    texto = re.sub(
        r"(I{1,3}|IV|V|VI)(?=[A-ZÁÉÍÓÚÑ])",
        r"\1, ",
        texto
    )

    # 2️⃣ Separar materias pegadas tipo:
    #     "ExactasTaller", "EscrituraTaller"
    texto = re.sub(
        r"([a-záéíóúñ])([A-ZÁÉÍÓÚÑ][a-záéíóúñ])",
        r"\1, \2",
        texto
    )

    # 3️⃣ Normalizar separadores clásicos
    texto = re.sub(r"\s*[;,\-]\s*", ",", texto)

    # 4️⃣ Split final
    partes = texto.split(",")

    # 5️⃣ Limpieza final
    correlativas_limpias = [
        p.strip()
        for p in partes
        if p.strip() and len(p.strip()) > 3
    ]

    return correlativas_limpias

    
def extraer_tabla_plan_estudios(soup):
    """
    Busca el encabezado 'Plan de Estudios' y extrae la tabla completa
    con las materias y sus datos.
    """
    plan = []

    # Buscar título
    h1_plan = soup.find("h1", string=re.compile("Plan de Estudios", re.I))
    if not h1_plan:
        return plan

    # Buscar la tabla que aparece después del h1
    tabla = h1_plan.find_next("table")
    if not tabla:
        return plan

    rows = tabla.find_all("tr")

    # Saltar encabezados
    for tr in rows[1:]:
        celdas = [td.get_text(strip=True) for td in tr.find_all("td")]

        if len(celdas) >= 5:
            plan.append({
                "asignatura": celdas[0],
                "regimen": celdas[1],
                "carga_horaria_semanal": celdas[2],
                "carga_horaria_total": celdas[3],
                "correlativas": extraer_correlativas(celdas[4])
            })

    return plan

def extraer_itinerario(soup):
    """
    Extrae TODAS las tablas del itinerario (1° y 2° tabla completa).
    Devuelve un diccionario con estructura limpia.
    """
    itinerarios = []

    # Buscar el título principal
    h1_it = soup.find("h1", string=re.compile("Itinerario", re.I))
    if not h1_it:
        return itinerarios

    # Buscar todas las tablas después del título
    tablas = h1_it.find_all_next("table")

    for tabla in tablas:
        tabla_data = []
        for tr in tabla.find_all("tr"):
            fila = []
            for td in tr.find_all(["td", "th"]):
                # Algunos TD contienen listas ul/li → convertir a texto plano
                if td.find("ul"):
                    li_items = [li.get_text(strip=True) for li in td.find_all("li")]
                    fila.append(li_items)
                else:
                    fila.append(td.get_text(strip=True))
            tabla_data.append(fila)

        itinerarios.append(tabla_data)

    return itinerarios

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
           url_completa = url_relativa if url_relativa.startswith(('http://', 'https://')) else os.getenv('URL_BASE') + url_relativa # Construyo la URL completa
           nombre_limpio = re.sub(r'\s+', ' ', nombre_carrera).strip() # Limpio el nombre de la carrera
        
        if url_completa not in urls_extraidas: # Verifico si la URL ya fue extraída
            urls_extraidas.add(url_completa)
            links_carreras.append({
                "carrera": nombre_limpio,
                "url_plan_estudios": url_completa
            })
    print(f"Carrera encontrada: {nombre_carrera} - URL: {url_completa}") 

  except requests.RequestException as e:
    print(f"Error al acceder a la URL {url_carreras}: {e}")
  except Exception as e:
    print(f"Error al procesar la página {url_carreras}: {e}")

  return links_carreras

def scrapear_carrera(carrera_data):
  """
  """
  detalle_carrera = []
  
  for item, carrera in enumerate(carrera_data): # Recorro cada carrera extraída
      url = carrera['url_plan_estudios']
      print(f"--> {item + 1}/{len(carrera_data)} Accediendo a la carrera: {carrera['carrera']} - URL: {url}")

      try: 
        response = realizar_solicitud_con_reintentos(url)
        if not response:
          raise requests.exceptions.RequestException("No se recibió respuesta válida.")
        resultado = BeautifulSoup(response.content, 'html.parser') # Parsea el contenido HTML de la página

        # El contenido relevante suele estar dentro de <article> o <main>
        contenedor_principal = resultado.find('article') or resultado.find('main') or resultado.find('div', id='content') or resultado
        contenedor_texto = contenedor_principal.get_text()
        texto_normalizado = re.sub(r'\s+', ' ', contenedor_texto).strip()
        
       # ============================================================
       # EXTRACCIÓN DE ITEMS PRINCIPALES (Duración, Título, Modalidad)
       # ============================================================

        items = resultado.find_all("li")

        duracion = "No encontrado"
        titulo = "No encontrado"
        modalidad = "No encontrado"

        for li in items:
            texto = li.get_text(strip=True)

            if texto.lower().startswith("duración"):
                duracion = texto.replace("Duración:", "").strip()

            elif texto.lower().startswith("título"):
                titulo = texto.replace("Título:", "").strip()

            elif texto.lower().startswith("modalidad"):
                modalidad = texto.replace("Modalidad:", "").strip()

        carrera["duracion"] = duracion
        carrera["titulo_oficial"] = titulo
        carrera["modalidad"] = modalidad

        # ============================================================
        # EXTRACCIÓN DE "Ámbitos de desempeño"
        # ============================================================
        ambitos = []

        # Buscar el h1 que contiene el título
        titulo_ambitos = resultado.find("h1", string=re.compile("ámbitos|ambitos", re.I))

        if titulo_ambitos:
            # Buscar la lista que viene inmediatamente después
            ul = titulo_ambitos.find_next("ul")
            if ul:
                ambitos = [li.get_text(strip=True) for li in ul.find_all("li")]

        # Guardarlo en tu objeto
        carrera["ambitos_desempeno"] = ambitos

        print("Ámbitos encontrados:", ambitos)

        # ============================================================
        # EXTRACCIÓN DEL PLAN DE ESTUDIOS
        # ============================================================
        plan_estudios = extraer_tabla_plan_estudios(resultado)
        carrera["plan_estudios"] = plan_estudios
        print(f"Plan de estudios: {len(plan_estudios)} materias extraídas.")


        # ============================================================
        # EXTRACCIÓN DEL ITINERARIO
        # ============================================================
        itinerario = extraer_itinerario(resultado)
        carrera["itinerario"] = itinerario
        print(f"Itinerarios encontrados: {len(itinerario)} tablas.")

      except requests.exceptions.RequestException as e:
            print(f"--- Error al acceder a {url}: {e} (Se registra como error)")
            error_msg = "Error de Conexión/Extracción"
            carrera['titulo_oficial'] = error_msg
      except Exception as e:
          print(f"--- Error general al procesar {url}: {e} (Se registra como error)")
          error_msg = "Error de Extracción"
          carrera['titulo_oficial'] = error_msg
            
      detalle_carrera.append(carrera)

       # --- PAUSA OBLIGATORIA DE 15 SEGUNDOS ---
      if item < len(carrera_data) - 1:
          print(f"\n>> ⏳ Pausando por {os.getenv('DELAY_BETWEEN_CAREERS')} segundos para ser cortés con el servidor...\n")

          time.sleep(1)  # Pausa de 15 segundos entre cada solicitud de carrera
  
  return detalle_carrera



if __name__ == "__main__":
   carreras_extraidas = scrapear_carreras(os.getenv('URL_CARRERAS'))
   if not carreras_extraidas:
    print("No se encontraron carreras en la página proporcionada.")
   else:
    print(f"✅ Extracción de {len(carreras_extraidas)} enlaces completada. Iniciando scraping de detalles con pausas...")
      
    # obtengo los detalles de cada carrera
    detalles_carreras = scrapear_carrera(carreras_extraidas)

    print(f"detalles_carreras: {detalles_carreras}")

     # --- Guardar los datos en un archivo JSON ---
    try:
          with open(os.getenv('OUTPUT_FILENAME'), 'w', encoding='utf-8') as f:
              json.dump(detalles_carreras, f, indent=4, ensure_ascii=False)
  
          # Imprimir una muestra en consola (los primeros 3)
          print("--- Muestra de los primeros 3 resultados ---")
          print(json.dumps(detalles_carreras[:3], indent=4, ensure_ascii=False))
          print("\n" + "*"*80)
          print(f"💾 Los datos han sido guardados correctamente en el archivo: {os.getenv('OUTPUT_FILENAME')}")
          print(f"Total de carreras encontradas: {len(detalles_carreras)}")
          print("*"*80)

    except IOError as e:
          print(f"\nError: No se pudo escribir el archivo {os.getenv('OUTPUT_FILENAME')}. {e}")