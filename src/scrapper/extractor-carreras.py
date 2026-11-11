import json
import os
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Configuración leída del .env. Solo URL_CARRERAS es obligatoria;
# el resto usa estos valores por defecto si no está definido.
URL_CARRERAS = os.getenv("URL_CARRERAS")
URL_BASE = os.getenv("URL_BASE") or URL_CARRERAS
MAX_RETRIES = int(os.getenv("MAX_RETRIES") or 3)
INITIAL_DELAY = int(os.getenv("INITIAL_DELAY") or 5)
DELAY_BETWEEN_CAREERS = int(os.getenv("DELAY_BETWEEN_CAREERS") or 15)
CARRERAS_FILENAME = os.getenv("CARRERAS_FILENAME") or "data/carreras.json"


def es_numero(texto):
    try:
        float(texto)
        return True
    except ValueError:
        return False


def realizar_solicitud_con_reintentos(url):
    """Realiza una solicitud HTTP con reintentos en caso de fallo temporal."""
    for intento in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()  # Lanza un error para códigos 4xx/5xx
            return response
        except requests.exceptions.RequestException as e:
            if intento == MAX_RETRIES:
                raise
            delay = INITIAL_DELAY * (2 ** (intento - 1))
            print(f"Error en la solicitud: {e}. Reintentando ({intento + 1}/{MAX_RETRIES}) en {delay} segundos...")
            time.sleep(delay)


# ============================================================
# PLAN DE ESTUDIOS
# ============================================================

def extraer_correlativas(correlativas_str):
    """Devuelve la lista de correlativas, o 'No tiene correlativas'."""
    texto = re.sub(r"\s+", " ", correlativas_str or "").strip()
    if texto.lower() in ("", "ninguna", "no tiene", "sin correlativas"):
        return "No tiene correlativas"

    # Numeral romano pegado a la materia siguiente: "Programación IÁlgebra"
    texto = re.sub(r"(?<![IVX])(I{1,3}|IV|V|VI)(?![IVX])(?=[A-ZÁÉÍÓÚÑ])", r"\1, ", texto)

    partes = re.split(r"\s*[□•|→·;,\-–]\s*", texto)
    return [p.strip() for p in partes if len(p.strip()) > 3]


def extraer_materias(filas):
    """Convierte las filas de una tabla del plan en materias."""
    materias = []
    for tr in filas:
        celdas = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(celdas) < 5:
            continue
        nombre = celdas[0]
        if nombre == "" or es_numero(nombre) or nombre == "Otros requisitos académicos":
            continue
        materias.append({
            "asignatura": nombre.rstrip(" *"),
            "regimen_de_cursada": celdas[1],
            "carga_horaria_semanal": celdas[2],
            "carga_horaria_total": celdas[3],
            "correlativas": extraer_correlativas(celdas[4]),
        })
    return materias


def extraer_tabla_plan_estudios(soup):
    """
    Busca el encabezado 'Plan de Estudios' y extrae la tabla de materias
    y, si existe, la tabla de 'Otros requisitos académicos'.
    """
    h1_plan = soup.find("h1", string=re.compile("Plan de Estudios", re.I))
    tabla = h1_plan.find_next("table") if h1_plan else None
    if not tabla:
        return []

    plan = extraer_materias(tabla.find_all("tr")[1:])  # se saltea el encabezado

    # La tabla siguiente son los otros requisitos, salvo que ya sea la del itinerario.
    tabla2 = tabla.find_next("table")
    h1_it = soup.find("h1", string=re.compile("Itinerario", re.I))
    tabla_itinerario = h1_it.find_next("table") if h1_it else None
    if tabla2 and tabla2 is not tabla_itinerario:
        plan += extraer_materias(tabla2.find_all("tr"))

    return plan


# ============================================================
# ITINERARIO
# ============================================================

def extraer_itinerario(soup):
    """
    Extrae los itinerarios sugeridos (hasta dos tablas: inicio en el
    primer o en el segundo semestre). Cada celda con una lista es un
    semestre; los semestres alternan entre 1 y 2 y el año sube después
    de cada segundo semestre.

    Devuelve:
    [{itinerario_titulo, semestres: [{orden, año, semestre, materias}]}]
    """
    itinerarios = []

    h1_it = soup.find("h1", string=re.compile("Itinerario", re.I))
    if not h1_it:
        return itinerarios

    for tabla in h1_it.find_all_next("table", limit=2):
        itinerario_titulo = None
        semestres = []
        semestre_actual = 1
        año_actual = 1

        for tr in tabla.find_all("tr"):
            # La primera fila con un <span> es el título del itinerario
            if itinerario_titulo is None:
                span = tr.find("span")
                if span:
                    itinerario_titulo = span.get_text(strip=True)
                    if "segundo semestre" in itinerario_titulo.lower():
                        semestre_actual = 2
                    continue

            for td in tr.find_all("td"):
                ul = td.find("ul")
                materias = [li.get_text(strip=True) for li in ul.find_all("li")] if ul else []
                if not materias:
                    continue

                semestres.append({
                    "orden": len(semestres) + 1,
                    "año": año_actual,
                    "semestre": semestre_actual,
                    "materias": materias,
                })

                if semestre_actual == 1:
                    semestre_actual = 2
                else:
                    semestre_actual = 1
                    año_actual += 1

        if itinerario_titulo and semestres:
            itinerarios.append({
                "itinerario_titulo": itinerario_titulo,
                "semestres": semestres,
            })

    return itinerarios


# ============================================================
# LISTADO DE CARRERAS
# ============================================================

def scrapear_carreras(url_carreras):
    """
    Descarga la página de carreras y devuelve, sin duplicados:
    [{"carrera": nombre, "url_plan_estudios": url}]
    """
    print(f"🔎 Descubriendo carreras disponibles en: {url_carreras}")
    response = realizar_solicitud_con_reintentos(url_carreras)
    soup = BeautifulSoup(response.content, "html.parser")

    patron_carrera = re.compile(r"/carrera/")
    contenedores = soup.find_all("article", class_=re.compile(r"post|hentry|career-item"))
    if contenedores:
        enlaces = [c.find("a", href=patron_carrera) for c in contenedores]
    else:
        # Sin artículos: se buscan los enlaces directamente en el contenido
        contenido = soup.find("div", id="content") or soup.find("main") or soup
        enlaces = contenido.find_all("a", href=patron_carrera)

    carreras = []
    urls_extraidas = set()
    for enlace in enlaces:
        if enlace is None:
            continue
        nombre = re.sub(r"\s+", " ", enlace.get_text(strip=True)).strip()
        url = urljoin(URL_BASE, enlace["href"])
        if len(nombre) > 10 and url not in urls_extraidas:
            urls_extraidas.add(url)
            carreras.append({"carrera": nombre, "url_plan_estudios": url})

    return carreras


# ============================================================
# DETALLE DE CADA CARRERA
# ============================================================

ETIQUETAS = {"Duración": "duracion", "Título": "titulo_oficial", "Modalidad": "modalidad"}


def extraer_detalle(soup, carrera):
    """Completa la carrera con los datos de su página."""
    # Duración, Título y Modalidad
    for campo in ETIQUETAS.values():
        carrera[campo] = "No encontrado"
    for li in soup.find_all("li"):
        texto = li.get_text(strip=True)
        for etiqueta, campo in ETIQUETAS.items():
            if texto.lower().startswith(etiqueta.lower()):
                carrera[campo] = texto.replace(f"{etiqueta}:", "").strip()

    # Ámbitos de desempeño: la lista que sigue al título
    ambitos = []
    titulo_ambitos = soup.find("h1", string=re.compile("ámbitos|ambitos", re.I))
    ul = titulo_ambitos.find_next("ul") if titulo_ambitos else None
    if ul:
        ambitos = [li.get_text(strip=True) for li in ul.find_all("li")]
    carrera["ambitos_desempeno"] = ambitos

    carrera["plan_estudios"] = extraer_tabla_plan_estudios(soup)
    carrera["itinerario"] = extraer_itinerario(soup)


def scrapear_carrera(carreras):
    """Descarga y extrae cada carrera, con una pausa entre una y otra."""
    for item, carrera in enumerate(carreras):
        url = carrera["url_plan_estudios"]
        print(f"--> {item + 1}/{len(carreras)} {carrera['carrera']}")

        try:
            response = realizar_solicitud_con_reintentos(url)
            extraer_detalle(BeautifulSoup(response.content, "html.parser"), carrera)
            print(f"    {len(carrera['plan_estudios'])} materias, {len(carrera['itinerario'])} itinerarios.")
        except requests.exceptions.RequestException as e:
            print(f"--- Error al acceder a {url}: {e} (Se registra como error)")
            carrera["titulo_oficial"] = "Error de Conexión/Extracción"
        except Exception as e:
            print(f"--- Error general al procesar {url}: {e} (Se registra como error)")
            carrera["titulo_oficial"] = "Error de Extracción"

        # Pausa entre carreras para ser cortés con el servidor
        if item < len(carreras) - 1:
            print(f"\n>> ⏳ Pausando por {DELAY_BETWEEN_CAREERS} segundos...\n")
            time.sleep(DELAY_BETWEEN_CAREERS)

    return carreras


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def mostrar_menu_carreras(carreras):
    print("\n📚 Carreras disponibles:\n")
    print("0 - TODAS las carreras\n")
    for i, carrera in enumerate(carreras, start=1):
        print(f"{i} - {carrera['carrera']}")


if __name__ == "__main__":
    if not URL_CARRERAS:
        sys.exit("❌ Falta URL_CARRERAS en el archivo .env")

    # 1️⃣ Descubrimiento de carreras (una sola solicitud)
    try:
        carreras = scrapear_carreras(URL_CARRERAS)
    except requests.exceptions.RequestException as e:
        sys.exit(f"❌ Error al acceder a {URL_CARRERAS}: {e}")
    if not carreras:
        sys.exit("❌ No se pudieron descubrir carreras.")

    mostrar_menu_carreras(carreras)

    # 2️⃣ Selección del usuario
    try:
        opcion = int(input("\n👉 Seleccione una carrera: "))
    except ValueError:
        sys.exit("❌ Debe ingresar un número.")

    if opcion == 0:
        print("\n🚀 Se scrapearán TODAS las carreras.")
    elif 1 <= opcion <= len(carreras):
        carreras = [carreras[opcion - 1]]
        print(f"\n🎯 Carrera seleccionada: {carreras[0]['carrera']}")
    else:
        sys.exit("❌ Opción inválida.")

    # 3️⃣ Se crea la carpeta de salida si no existe (antes de extraer,
    #    para no perder el trabajo si no se puede crear)
    carpeta = os.path.dirname(CARRERAS_FILENAME)
    if carpeta:
        try:
            os.makedirs(carpeta, exist_ok=True)
        except OSError as e:
            sys.exit(f"❌ No se pudo crear la carpeta {carpeta}: {e}")

    # 4️⃣ Extracción del detalle
    detalles_carreras = scrapear_carrera(carreras)

    # 5️⃣ Guardar JSON
    try:
        with open(CARRERAS_FILENAME, "w", encoding="utf-8") as f:
            json.dump(detalles_carreras, f, indent=4, ensure_ascii=False)
        print(f"\n💾 Datos guardados correctamente en {CARRERAS_FILENAME}")
    except IOError as e:
        print(f"\nError al escribir el archivo: {e}")