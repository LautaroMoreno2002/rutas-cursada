# Proyecto de Scraping Académico en Python

Este proyecto permite extraer información de carreras universitarias, incluyendo planes de estudio, correlativas, itinerarios y ámbitos de desempeño. Además, descarga un archivo PDF con información de períodos académicos y lo convierte a formato Excel.

---

## Requisitos previos

Es necesario contar con Python 3.9 o superior instalado y acceso a una terminal (CMD, PowerShell, Git Bash o terminal en Linux/Mac).

---

## Creación del entorno virtual

Desde la raíz del proyecto, ejecutar el siguiente comando:

```bash
python -m venv venv
```

Luego, activar el entorno virtual.

En Windows:

```bash
venv\Scripts\activate.bat
```

En Linux o Mac:

```bash
source venv/bin/activate
```

---

## Instalación de dependencias

Con el entorno virtual activo, instalar las dependencias principales del proyecto:

```bash
pip install -r requirements.txt
```

Para ejecutar el script de extracción de períodos académicos, también es necesario instalar las siguientes dependencias adicionales:

```bash
pip install pdfplumber pandas openpyxl
```

---

## Configuración de variables de entorno

Crear un archivo `.env` en la raíz del proyecto y definir las variables necesarias. Un ejemplo de configuración es el siguiente:

```env
URL_BASE=https://www.ejemplo.edu.ar
URL_CARRERAS=https://www.ejemplo.edu.ar/carreras
OUTPUT_FILENAME=carreras.json

MAX_RETRIES=3
INITIAL_DELAY=2
DELAY_BETWEEN_CAREERS=15

URL_PERIODO=https://www.ejemplo.edu.ar/periodo
PERIODO_PDF_FILENAME=periodo.pdf
PERIODO_EXCEL_FILENAME=periodo.xlsx
```

Las URLs deben ajustarse según el sitio web de la universidad que se desea analizar.

---

## Ejecución de los scripts

Para extraer las carreras y sus planes de estudio, ejecutar:

```bash
python extractor-carreras.py
```

El script generará un archivo JSON con toda la información obtenida.

Para descargar el período académico y convertir el PDF a Excel, ejecutar:

```bash
python extractor-periodo.py
```

Como resultado se obtendrá el archivo PDF descargado y un archivo Excel con los datos extraídos.

---

## Archivos del proyecto

El script `extractor-carreras.py` se encarga del scraping de las carreras y sus planes de estudio. El script `extractor-periodo.py` descarga el PDF del período académico y lo convierte a Excel. El archivo `requirements.txt` contiene las dependencias principales del proyecto y el archivo `.env` almacena la configuración del entorno.

---

## Recomendaciones

Se recomienda respetar los tiempos de espera configurados para evitar sobrecargar el servidor, verificar periódicamente la estructura HTML del sitio en caso de fallos y ejecutar siempre los scripts con el entorno virtual activado.

---

Este proyecto tiene fines educativos y académicos.
