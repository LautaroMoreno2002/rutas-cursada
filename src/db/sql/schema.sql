-- ============================================================
-- rutas-cursada · 01 · Creación de la base de datos y las tablas
-- MySQL 8.0 o superior
--
-- Orden de ejecución (sobre una base vacía):
--   mysql -u root -p < 01_crear_tablas.sql
--   mysql -u root -p < 02_claves.sql
--
-- Este script crea solo las tablas con sus columnas, tipos y
-- validaciones (CHECK). Las claves primarias, únicas y foráneas se
-- agregan en 02_claves.sql.
--
-- Para empezar de cero:  
DROP DATABASE rutas_cursada;
-- ============================================================

-- El archivo está en UTF-8: sin esta línea, los acentos ('Miércoles',
-- 'Sábado') se guardan mal cuando el cliente usa otra codificación.
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS rutas_cursada
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;   -- compara sin distinguir mayúsculas ni acentos

USE rutas_cursada;

-- ============================================================
-- BLOQUE 1 · CARRERAS Y PLANES DE ESTUDIO  (origen: carreras.json)
-- ============================================================

CREATE TABLE carrera (
    id              INT UNSIGNED  NOT NULL,
    nombre          VARCHAR(150)  NOT NULL,
    url             VARCHAR(255)  NOT NULL,
    duracion        VARCHAR(30)   NULL,              -- "5 años"
    titulo_oficial  VARCHAR(200)  NULL,
    modalidad       VARCHAR(30)   NULL               -- "Presencial"
) ENGINE = InnoDB;

CREATE TABLE carrera_ambito (
    id           INT UNSIGNED       NOT NULL,
    carrera_id   INT UNSIGNED       NOT NULL,
    orden        SMALLINT UNSIGNED  NOT NULL,        -- posición en la lista de la página
    descripcion  TEXT               NOT NULL
) ENGINE = InnoDB;

-- Plan aprobado por una resolución. Agrupa las materias y el itinerario.
CREATE TABLE plan_estudios (
    id                    INT UNSIGNED       NOT NULL,
    carrera_id            INT UNSIGNED       NOT NULL,
    resolucion            VARCHAR(100)       NULL,   -- "Resolución (CS) Nº7016/18"
    resolucion_url        VARCHAR(500)       NULL,
    anio                  SMALLINT UNSIGNED  NULL,   -- año de aprobación
    carga_horaria_total   SMALLINT UNSIGNED  NULL,
    cantidad_asignaturas  SMALLINT UNSIGNED  NULL,
    vigente               BOOLEAN            NOT NULL DEFAULT TRUE
) ENGINE = InnoDB;

-- Una materia tal como figura en UN plan de estudios.
CREATE TABLE materia (
    id                     INT UNSIGNED       NOT NULL,
    plan_estudios_id       INT UNSIGNED       NOT NULL,
    nombre                 VARCHAR(200)       NOT NULL,
    orden                  SMALLINT UNSIGNED  NOT NULL,   -- posición en la tabla del plan
    regimen                VARCHAR(20)        NULL,       -- "Semestral", "Anual"
    carga_horaria_semanal  SMALLINT UNSIGNED  NULL,
    carga_horaria_total    SMALLINT UNSIGNED  NULL,
    -- Correlativas que no son una materia: "14 (catorce) materias de la carrera"
    requisito_adicional    VARCHAR(255)       NULL
) ENGINE = InnoDB;

-- Para cursar materia_id hay que tener correlativa_id (ambas del mismo plan).
CREATE TABLE correlativa (
    materia_id      INT UNSIGNED  NOT NULL,
    correlativa_id  INT UNSIGNED  NOT NULL,
    CONSTRAINT ck_correlativa_distinta CHECK (materia_id <> correlativa_id)
) ENGINE = InnoDB;

-- Secuencia de cursado sugerida para un plan
-- ("iniciando la carrera en el primer semestre del año").
CREATE TABLE itinerario (
    id                INT UNSIGNED      NOT NULL,
    plan_estudios_id  INT UNSIGNED      NOT NULL,
    titulo            VARCHAR(200)      NOT NULL,
    semestre_inicio   TINYINT UNSIGNED  NOT NULL,    -- 1 o 2
    CONSTRAINT ck_itinerario_semestre_inicio CHECK (semestre_inicio IN (1, 2))
) ENGINE = InnoDB;

-- Cada paso del itinerario: posición dentro de la carrera, no fecha del calendario.
CREATE TABLE itinerario_semestre (
    id             INT UNSIGNED      NOT NULL,
    itinerario_id  INT UNSIGNED      NOT NULL,
    orden          TINYINT UNSIGNED  NOT NULL,       -- 1, 2, 3... dentro del itinerario
    anio           TINYINT UNSIGNED  NOT NULL,       -- año de la carrera
    semestre       TINYINT UNSIGNED  NOT NULL,       -- 1 o 2
    CONSTRAINT ck_itsem_semestre CHECK (semestre IN (1, 2))
) ENGINE = InnoDB;

-- Materias de cada paso. Una materia anual aparece en dos pasos seguidos.
CREATE TABLE itinerario_materia (
    itinerario_semestre_id  INT UNSIGNED  NOT NULL,
    materia_id              INT UNSIGNED  NOT NULL
) ENGINE = InnoDB;

-- ============================================================
-- BLOQUE 2 · OFERTA POR SEMESTRE  (origen: periodo.xlsx / PDF de comisiones)
-- ============================================================

-- Catálogo de actividades con el código de la universidad (A0452).
CREATE TABLE actividad (
    id      INT UNSIGNED  NOT NULL,
    codigo  VARCHAR(10)   NOT NULL,
    nombre  VARCHAR(255)  NOT NULL
) ENGINE = InnoDB;

-- Puente entre los dos bloques: qué actividad(es) cumplen una materia del plan.
CREATE TABLE materia_actividad (
    materia_id    INT UNSIGNED  NOT NULL,
    actividad_id  INT UNSIGNED  NOT NULL
) ENGINE = InnoDB;

-- Semestre lectivo del calendario (2026 · 2) con su oferta de comisiones.
CREATE TABLE semestre (
    id                INT UNSIGNED       NOT NULL,
    anio              SMALLINT UNSIGNED  NOT NULL,   -- 2026
    numero            TINYINT UNSIGNED   NOT NULL,   -- 1 o 2
    fecha_inicio      DATE               NULL,
    fecha_fin         DATE               NULL,
    url_pdf           VARCHAR(500)       NULL,
    fecha_extraccion  DATETIME           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_semestre_numero CHECK (numero IN (1, 2)),
    CONSTRAINT ck_semestre_fechas CHECK (fecha_inicio <= fecha_fin)
) ENGINE = InnoDB;

CREATE TABLE comision (
    id            INT UNSIGNED  NOT NULL,
    semestre_id   INT UNSIGNED  NOT NULL,
    actividad_id  INT UNSIGNED  NOT NULL,
    nombre        VARCHAR(30)   NOT NULL,            -- "COM-01", "COM-02 (BOLIVAR)"
    instancia     VARCHAR(40)   NULL                 -- "Regularidad/Promoción"
) ENGINE = InnoDB;

CREATE TABLE docente (
    id      INT UNSIGNED  NOT NULL,
    nombre  VARCHAR(100)  NOT NULL                   -- "Apellido Nombre", como en el PDF
) ENGINE = InnoDB;

CREATE TABLE comision_docente (
    comision_id  INT UNSIGNED  NOT NULL,
    docente_id   INT UNSIGNED  NOT NULL
) ENGINE = InnoDB;

CREATE TABLE edificio (
    id      INT UNSIGNED  NOT NULL,
    nombre  VARCHAR(60)   NOT NULL                   -- "MODULO VII", "ROCA"
) ENGINE = InnoDB;

CREATE TABLE aula (
    id           INT UNSIGNED  NOT NULL,
    nombre       VARCHAR(60)   NOT NULL,             -- "AULA 7278", "LABO COM 7116"
    edificio_id  INT UNSIGNED  NULL
) ENGINE = InnoDB;

CREATE TABLE tipo_clase (
    id      INT UNSIGNED  NOT NULL,
    nombre  VARCHAR(40)   NOT NULL                   -- "TEÓRICO/PRÁCTICO", "VT ASINC"
) ENGINE = InnoDB;

-- Una fila del PDF: un día y horario de una comisión en un aula.
--   · Clase virtual asincrónica ("VT ASINC"): dia, horas y aula en NULL,
--     y tipo_clase = 'VT ASINC'.
--   · "Sin definir": todo en NULL.
--   · Una comisión puede tener dos filas con el mismo día y horario
--     en aulas distintas.
CREATE TABLE horario (
    id              INT UNSIGNED  NOT NULL,
    comision_id     INT UNSIGNED  NOT NULL,
    dia             ENUM('Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo') NULL,
    hora_inicio     TIME          NULL,
    hora_fin        TIME          NULL,
    tipo_clase_id   INT UNSIGNED  NULL,
    aula_id         INT UNSIGNED  NULL,
    -- Van por fila porque en el PDF pueden variar dentro de una misma comisión
    fecha_inicio    DATE          NULL,
    fecha_fin       DATE          NULL,
    -- Texto original del PDF: "A0025 COM-02 | A0025 COM-01"
    compartido_con  VARCHAR(255)  NULL,
    CONSTRAINT ck_horario_horas CHECK (hora_inicio < hora_fin),
    CONSTRAINT ck_horario_dia_y_horas CHECK ((dia IS NULL) = (hora_inicio IS NULL) AND (dia IS NULL) = (hora_fin IS NULL)),
    CONSTRAINT ck_horario_fechas CHECK (fecha_inicio <= fecha_fin)
) ENGINE = InnoDB;