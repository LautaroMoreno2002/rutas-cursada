-- ============================================================
-- rutas-cursada · 02 · Claves primarias, únicas y foráneas
-- Ejecutar después de 01_crear_tablas.sql
--
--   1. Claves primarias (PK). Los id se numeran solos (AUTO_INCREMENT).
--   2. Claves únicas (UK): valores que no se pueden repetir.
--   3. Claves foráneas (FK): relaciones entre tablas.
--
-- Reglas de borrado de las FK:
--   · CASCADE: al borrar el padre se borran sus hijos (una carrera
--     arrastra sus planes, materias, itinerarios...).
--   · RESTRICT: no se puede borrar un catálogo que está en uso
--     (una actividad con comisiones, un aula con horarios...).
-- ============================================================

SET NAMES utf8mb4;
USE rutas_cursada;

-- ============================================================
-- 1 · CLAVES PRIMARIAS
-- ============================================================

-- Tablas con id propio
ALTER TABLE carrera
    ADD CONSTRAINT pk_carrera PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE carrera_ambito
    ADD CONSTRAINT pk_carrera_ambito PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE plan_estudios
    ADD CONSTRAINT pk_plan_estudios PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE materia
    ADD CONSTRAINT pk_materia PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE itinerario
    ADD CONSTRAINT pk_itinerario PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE itinerario_semestre
    ADD CONSTRAINT pk_itinerario_semestre PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE actividad
    ADD CONSTRAINT pk_actividad PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE semestre
    ADD CONSTRAINT pk_semestre PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE comision
    ADD CONSTRAINT pk_comision PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE docente
    ADD CONSTRAINT pk_docente PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE edificio
    ADD CONSTRAINT pk_edificio PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE aula
    ADD CONSTRAINT pk_aula PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE tipo_clase
    ADD CONSTRAINT pk_tipo_clase PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE horario
    ADD CONSTRAINT pk_horario PRIMARY KEY (id),
    MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

-- Tablas intermedias (muchos a muchos): la PK es el par de FK,
-- así no se puede cargar dos veces la misma relación.
ALTER TABLE correlativa
    ADD CONSTRAINT pk_correlativa PRIMARY KEY (materia_id, correlativa_id);

ALTER TABLE itinerario_materia
    ADD CONSTRAINT pk_itinerario_materia PRIMARY KEY (itinerario_semestre_id, materia_id);

ALTER TABLE materia_actividad
    ADD CONSTRAINT pk_materia_actividad PRIMARY KEY (materia_id, actividad_id);

ALTER TABLE comision_docente
    ADD CONSTRAINT pk_comision_docente PRIMARY KEY (comision_id, docente_id);

-- ============================================================
-- 2 · CLAVES ÚNICAS
-- ============================================================

ALTER TABLE carrera
    ADD CONSTRAINT uq_carrera_nombre UNIQUE (nombre),
    ADD CONSTRAINT uq_carrera_url    UNIQUE (url);

-- Un ítem por posición dentro de la carrera
ALTER TABLE carrera_ambito
    ADD CONSTRAINT uq_ambito_carrera_orden UNIQUE (carrera_id, orden);

-- Una misma resolución no se carga dos veces para la carrera
ALTER TABLE plan_estudios
    ADD CONSTRAINT uq_plan_carrera_resolucion UNIQUE (carrera_id, resolucion);

-- Una materia no se repite dentro del plan
ALTER TABLE materia
    ADD CONSTRAINT uq_materia_plan_nombre UNIQUE (plan_estudios_id, nombre);

ALTER TABLE itinerario
    ADD CONSTRAINT uq_itinerario_plan_titulo UNIQUE (plan_estudios_id, titulo);

-- Un solo paso por posición dentro del itinerario
ALTER TABLE itinerario_semestre
    ADD CONSTRAINT uq_itsem_itinerario_orden UNIQUE (itinerario_id, orden);

ALTER TABLE actividad
    ADD CONSTRAINT uq_actividad_codigo UNIQUE (codigo);

-- Un solo registro por semestre del calendario (2026 · 2)
ALTER TABLE semestre
    ADD CONSTRAINT uq_semestre_anio_numero UNIQUE (anio, numero);

-- "A0452 COM-01" existe una sola vez en cada semestre
ALTER TABLE comision
    ADD CONSTRAINT uq_comision_semestre_actividad_nombre UNIQUE (semestre_id, actividad_id, nombre);

ALTER TABLE docente
    ADD CONSTRAINT uq_docente_nombre UNIQUE (nombre);

ALTER TABLE edificio
    ADD CONSTRAINT uq_edificio_nombre UNIQUE (nombre);

ALTER TABLE aula
    ADD CONSTRAINT uq_aula_nombre UNIQUE (nombre);

ALTER TABLE tipo_clase
    ADD CONSTRAINT uq_tipo_clase_nombre UNIQUE (nombre);

-- ============================================================
-- 3 · CLAVES FORÁNEAS
-- ============================================================

-- ---------- Bloque 1 · Carreras y planes ----------

ALTER TABLE carrera_ambito
    ADD CONSTRAINT fk_ambito_carrera
        FOREIGN KEY (carrera_id) REFERENCES carrera (id) ON DELETE CASCADE;

ALTER TABLE plan_estudios
    ADD CONSTRAINT fk_plan_carrera
        FOREIGN KEY (carrera_id) REFERENCES carrera (id) ON DELETE CASCADE;

ALTER TABLE materia
    ADD CONSTRAINT fk_materia_plan
        FOREIGN KEY (plan_estudios_id) REFERENCES plan_estudios (id) ON DELETE CASCADE;

ALTER TABLE correlativa
    ADD CONSTRAINT fk_correlativa_materia
        FOREIGN KEY (materia_id) REFERENCES materia (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_correlativa_requerida
        FOREIGN KEY (correlativa_id) REFERENCES materia (id) ON DELETE CASCADE;

ALTER TABLE itinerario
    ADD CONSTRAINT fk_itinerario_plan
        FOREIGN KEY (plan_estudios_id) REFERENCES plan_estudios (id) ON DELETE CASCADE;

ALTER TABLE itinerario_semestre
    ADD CONSTRAINT fk_itsem_itinerario
        FOREIGN KEY (itinerario_id) REFERENCES itinerario (id) ON DELETE CASCADE;

ALTER TABLE itinerario_materia
    ADD CONSTRAINT fk_itmat_semestre
        FOREIGN KEY (itinerario_semestre_id) REFERENCES itinerario_semestre (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_itmat_materia
        FOREIGN KEY (materia_id) REFERENCES materia (id) ON DELETE CASCADE;

-- ---------- Puente entre los bloques ----------

ALTER TABLE materia_actividad
    ADD CONSTRAINT fk_matact_materia
        FOREIGN KEY (materia_id) REFERENCES materia (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_matact_actividad
        FOREIGN KEY (actividad_id) REFERENCES actividad (id) ON DELETE CASCADE;

-- ---------- Bloque 2 · Oferta por semestre ----------

ALTER TABLE comision
    ADD CONSTRAINT fk_comision_semestre
        FOREIGN KEY (semestre_id) REFERENCES semestre (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_comision_actividad
        FOREIGN KEY (actividad_id) REFERENCES actividad (id) ON DELETE RESTRICT;

ALTER TABLE comision_docente
    ADD CONSTRAINT fk_comdoc_comision
        FOREIGN KEY (comision_id) REFERENCES comision (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_comdoc_docente
        FOREIGN KEY (docente_id) REFERENCES docente (id) ON DELETE RESTRICT;

ALTER TABLE aula
    ADD CONSTRAINT fk_aula_edificio
        FOREIGN KEY (edificio_id) REFERENCES edificio (id) ON DELETE RESTRICT;

ALTER TABLE horario
    ADD CONSTRAINT fk_horario_comision
        FOREIGN KEY (comision_id) REFERENCES comision (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_horario_tipo_clase
        FOREIGN KEY (tipo_clase_id) REFERENCES tipo_clase (id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_horario_aula
        FOREIGN KEY (aula_id) REFERENCES aula (id) ON DELETE RESTRICT;