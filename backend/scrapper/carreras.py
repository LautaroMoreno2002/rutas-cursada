"""Scraper de carreras: nombre, URL, duración, título, modalidad, ámbitos,
plan de estudios (con correlativas) e itinerarios sugeridos.

Uso:
    python -m scrapper.carreras                 # menú interactivo
    python -m scrapper.carreras --todas
    python -m scrapper.carreras --carrera "Licenciatura en Sistemas"
"""
import argparse
import json
import re
import time

import requests
from bs4 import BeautifulSoup

from . import config


def es_numero(texto):
    try:
        float(texto)
        return True
    except ValueError:
        return False


def realizar_solicitud_con_reintentos(url):
    """Realiza una solicitud HTTP con reintentos y backoff exponencial."""
    for intento in range(config.MAX_RETRIES):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()  # Lanza un error para códigos 4xx/5xx
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud: {e}. Reintentando ({intento + 1}/{config.MAX_RETRIES})...")
            if intento < config.MAX_RETRIES - 1:
                delay = config.INITIAL_DELAY * (2 ** intento)
                print(f"Esperando {delay} segundos antes del próximo intento...")
                time.sleep(delay)
    raise requests.exceptions.RequestException(
        f"No se pudo completar la solicitud a {url} después de {config.MAX_RETRIES} intentos."
    )


def limpiar_texto(text, label_pattern=r"(.*)", capture_group=1):
    """Limpia y extrae el texto según un patrón. Devuelve "No encontrado" si no matchea."""
    match = re.search(label_pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(capture_group).strip())
    return "No encontrado"


def extraer_correlativas(correlativas_str):
    """Separa el texto de correlativas en una lista de nombres de materias.

    Devuelve siempre una lista (vacía si no tiene correlativas) para que el
    importador no tenga que distinguir entre str y list.
    """
    if not correlativas_str or correlativas_str.strip().lower() in [
        "", "-", "ninguna", "no tiene", "sin correlativas"
    ]:
        return []

    texto = limpiar_texto(correlativas_str)
    if texto == "No encontrado":
        return []

    # Numeral romano pegado a la materia siguiente:
    #   "Programación IIBases de Datos"     -> "Programación II, Bases de Datos"
    #   "Programación IIntroducción a ..."  -> "Programación I, Introducción a ..."
    # (el numeral va precedido de un espacio y seguido de Mayúscula+minúscula)
    texto = re.sub(
        r"(?<=\s)(I{1,3}|IV|VI|V)(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])",
        r"\1, ",
        texto,
    )
    # Separadores raros
    texto = re.sub(r"\s*[□•|→·]\s*", ",", texto)
    # Separadores clásicos
    texto = re.sub(r"\s*[;,\-–]\s*", ",", texto)

    partes = texto.split(",")
    return [p.strip() for p in partes if p.strip() and len(p.strip()) > 3]


def _filas_tabla(tabla):
    for tr in tabla.find_all("tr"):
        yield [td.get_text(strip=True) for td in tr.find_all("td")]


def extraer_tabla_plan_estudios(soup):
    """Busca el encabezado 'Plan de Estudios' y extrae la tabla de materias
    y, si existe, la tabla de 'Otros requisitos académicos'."""
    plan = []

    h1_plan = soup.find("h1", string=re.compile("Plan de Estudios", re.I))
    if not h1_plan:
        return plan

    tabla = h1_plan.find_next("table")
    if not tabla:
        return plan

    for celdas in list(_filas_tabla(tabla))[1:]:  # Salto encabezados
        if len(celdas) >= 5 and celdas[0] != "" and not es_numero(celdas[0]):
            plan.append({
                "asignatura": celdas[0].rstrip(" *"),
                "regimen_de_cursada": celdas[1],
                "carga_horaria_semanal": celdas[2],
                "carga_horaria_total": celdas[3],
                "correlativas": extraer_correlativas(celdas[4]),
                "otro_requisito": False,
            })

    # Otros requisitos académicos (si existe)
    tabla2 = tabla.find_next("table")
    if not tabla2:
        return plan

    for celdas in _filas_tabla(tabla2):
        if (
            len(celdas) >= 5
            and celdas[0] != ""
            and not es_numero(celdas[0])
            and celdas[0] != "Otros requisitos académicos"
        ):
            plan.append({
                "asignatura": celdas[0].rstrip(" *"),
                "regimen_de_cursada": celdas[1],
                "carga_horaria_semanal": celdas[2],
                "carga_horaria_total": celdas[3],  # antes: "carg_horaria_total" (typo)
                "correlativas": extraer_correlativas(celdas[4]),
                "otro_requisito": True,
            })
    return plan


def extraer_itinerario(soup):
    """Extrae los itinerarios sugeridos (hasta dos tablas: inicio en 1er o 2do semestre).

    Cada <td> con una <ul> es un semestre. El semestre alterna 1/2 y el año
    se incrementa al cerrar un 2do semestre.

    Devuelve:
    [{ itinerario_titulo, semestres: [{orden, año, semestre, materias: [str]}] }]
    """
    itinerarios = []

    h1_it = soup.find("h1", string=re.compile("Itinerario", re.I))
    if not h1_it:
        return itinerarios

    for tabla in h1_it.find_all_next("table", limit=2):
        itinerario_titulo = None
        semestres = []
        orden = 0
        semestre_actual = 1
        anio_actual = 1

        for tr in tabla.find_all("tr"):
            if itinerario_titulo is None:
                span = tr.find("span")
                if span:
                    itinerario_titulo = span.get_text(strip=True)
                    if "segundo semestre" in itinerario_titulo.lower():
                        semestre_actual = 2
                    continue

            for td in tr.find_all("td"):
                ul = td.find("ul")
                if not ul:
                    continue
                materias = [li.get_text(strip=True) for li in ul.find_all("li")]
                if not materias:
                    continue

                orden += 1
                semestres.append({
                    "orden": orden,
                    "año": anio_actual,
                    "semestre": semestre_actual,
                    "materias": materias,
                })
                if semestre_actual == 1:
                    semestre_actual = 2
                else:
                    semestre_actual = 1
                    anio_actual += 1

        if itinerario_titulo and semestres:
            itinerarios.append({"itinerario_titulo": itinerario_titulo, "semestres": semestres})

    return itinerarios


def _enlaces_carreras(soup):
    contenedores = soup.find_all("article", class_=re.compile(r"post|hentry|career-item"))
    if contenedores:
        enlaces = []
        for cont in contenedores:
            a = cont.find("a", href=re.compile(r"/carrera/"))
            if a:
                enlaces.append(a)
        return enlaces
    print("Aviso: No se encontraron contenedores de artículos. Buscando enlaces directos...")
    contenido = soup.find("div", id="content") or soup.find("main") or soup
    return contenido.find_all("a", href=re.compile(r"/carrera/"))


def scrapear_carreras(url_carreras):
    """Devuelve [{carrera, url_plan_estudios}] de la página de oferta académica."""
    links_carreras = []
    urls_extraidas = set()

    try:
        print(f"-------- Accediendo a la URL de las carreras: {url_carreras} --------")
        response = realizar_solicitud_con_reintentos(url_carreras)
        soup = BeautifulSoup(response.content, "html.parser")

        for enlace in _enlaces_carreras(soup):
            nombre_carrera = re.sub(r"\s+", " ", enlace.get_text(strip=True)).strip()
            url_relativa = enlace.get("href")
            # Antes este bloque quedaba fuera del if y podía usar variables de la
            # iteración anterior (o no definidas).
            if not (nombre_carrera and url_relativa and len(nombre_carrera) > 10):
                continue
            url_completa = (
                url_relativa if url_relativa.startswith(("http://", "https://"))
                else config.URL_BASE + url_relativa
            )
            if url_completa not in urls_extraidas:
                urls_extraidas.add(url_completa)
                links_carreras.append({"carrera": nombre_carrera, "url_plan_estudios": url_completa})
                print(f"Carrera encontrada: {nombre_carrera} - URL: {url_completa}")

    except requests.RequestException as e:
        print(f"Error al acceder a la URL {url_carreras}: {e}")
    except Exception as e:  # noqa: BLE001
        print(f"Error al procesar la página {url_carreras}: {e}")

    return links_carreras


def parsear_detalle_carrera(html, carrera):
    """Completa el dict `carrera` con los datos de su página (separado para poder testearlo)."""
    soup = BeautifulSoup(html, "html.parser")

    duracion = titulo = modalidad = "No encontrado"
    for li in soup.find_all("li"):
        texto = li.get_text(strip=True)
        bajo = texto.lower()
        if bajo.startswith("duración"):
            duracion = re.sub(r"^duración:?", "", texto, flags=re.I).strip()
        elif bajo.startswith("título"):
            titulo = re.sub(r"^título:?", "", texto, flags=re.I).strip()
        elif bajo.startswith("modalidad"):
            modalidad = re.sub(r"^modalidad:?", "", texto, flags=re.I).strip()

    carrera["duracion"] = duracion
    carrera["titulo_oficial"] = titulo
    carrera["modalidad"] = modalidad

    ambitos = []
    titulo_ambitos = soup.find("h1", string=re.compile("ámbitos|ambitos", re.I))
    if titulo_ambitos:
        ul = titulo_ambitos.find_next("ul")
        if ul:
            ambitos = [li.get_text(strip=True) for li in ul.find_all("li")]
    carrera["ambitos_desempeno"] = ambitos

    carrera["plan_estudios"] = extraer_tabla_plan_estudios(soup)
    carrera["itinerario"] = extraer_itinerario(soup)
    return carrera


def scrapear_carrera(carrera_data):
    """Scrapea el detalle de cada carrera de la lista (con pausa entre carreras)."""
    detalle_carrera = []

    for item, carrera in enumerate(carrera_data):
        url = carrera["url_plan_estudios"]
        print(f"--> {item + 1}/{len(carrera_data)} {carrera['carrera']} - {url}")
        try:
            response = realizar_solicitud_con_reintentos(url)
            parsear_detalle_carrera(response.content, carrera)
            print(
                f"    Plan: {len(carrera['plan_estudios'])} materias, "
                f"itinerarios: {len(carrera['itinerario'])}"
            )
        except requests.exceptions.RequestException as e:
            print(f"--- Error al acceder a {url}: {e} (Se registra como error)")
            carrera["titulo_oficial"] = "Error de Conexión/Extracción"
        except Exception as e:  # noqa: BLE001
            print(f"--- Error general al procesar {url}: {e} (Se registra como error)")
            carrera["titulo_oficial"] = "Error de Extracción"

        detalle_carrera.append(carrera)

        if item < len(carrera_data) - 1:
            print(f"\n>> ⏳ Pausando {config.DELAY_BETWEEN_CAREERS} segundos para ser cortés con el servidor...\n")
            time.sleep(config.DELAY_BETWEEN_CAREERS)  # antes: time.sleep(1)

    return detalle_carrera


def mostrar_menu_carreras(nombres):
    print("\n📚 Carreras disponibles:\n")
    print("0 - TODAS las carreras\n")
    for i, nombre in enumerate(nombres, start=1):
        print(f"{i} - {nombre}")


def filtrar_carreras_por_nombre(carreras_extraidas, nombres_seleccionados):
    if not nombres_seleccionados:
        return carreras_extraidas
    buscados = {n.lower() for n in nombres_seleccionados}
    return [c for c in carreras_extraidas if c["carrera"].lower() in buscados]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scrapea carreras y planes de estudio.")
    parser.add_argument("--todas", action="store_true", help="Scrapear todas las carreras")
    parser.add_argument("--carrera", action="append", help="Nombre exacto de carrera (repetible)")
    parser.add_argument("--salida", help="Archivo JSON de salida")
    args = parser.parse_args(argv)

    if not config.URL_CARRERAS:
        raise SystemExit("❌ Falta URL_CARRERAS en el .env")

    # Una sola request para descubrir carreras (antes se hacían dos).
    carreras_extraidas = scrapear_carreras(config.URL_CARRERAS)
    if not carreras_extraidas:
        raise SystemExit("❌ No se pudieron descubrir carreras.")

    if args.todas:
        seleccion = carreras_extraidas
    elif args.carrera:
        seleccion = filtrar_carreras_por_nombre(carreras_extraidas, args.carrera)
    else:
        nombres = [c["carrera"] for c in carreras_extraidas]
        mostrar_menu_carreras(nombres)
        try:
            opcion = int(input("\n👉 Seleccione una carrera: "))
        except ValueError:
            raise SystemExit("❌ Debe ingresar un número.")
        if opcion == 0:
            seleccion = carreras_extraidas
        elif 1 <= opcion <= len(nombres):
            seleccion = [carreras_extraidas[opcion - 1]]
        else:
            raise SystemExit("❌ Opción inválida.")

    if not seleccion:
        raise SystemExit("❌ Ninguna carrera coincide con la selección.")

    detalles = scrapear_carrera(seleccion)
    salida = args.salida or config.ruta("CARRERAS_FILENAME", "carreras.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(detalles, f, indent=4, ensure_ascii=False)
    print(f"\n💾 Datos guardados correctamente en {salida}")
    return detalles


if __name__ == "__main__":
    main()
