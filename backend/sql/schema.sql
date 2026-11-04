-- Generado con: python -m app.cli schema-sql (no editar a mano)

CREATE DATABASE IF NOT EXISTS rutas_cursada CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE rutas_cursada;

CREATE TABLE IF NOT EXISTS carrera (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	nombre VARCHAR(200) NOT NULL, 
	titulo_oficial VARCHAR(255), 
	url_plan_estudios VARCHAR(500), 
	duracion VARCHAR(60), 
	modalidad VARCHAR(60), 
	ambitos_desempeno JSON, 
	actualizado DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);

CREATE TABLE IF NOT EXISTS materia (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	codigo VARCHAR(20), 
	nombre VARCHAR(255) NOT NULL, 
	nombre_normalizado VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (codigo), 
	UNIQUE (nombre_normalizado)
);

CREATE TABLE IF NOT EXISTS periodo (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	anio SMALLINT NOT NULL, 
	semestre SMALLINT NOT NULL, 
	titulo VARCHAR(255), 
	definido BOOL NOT NULL, 
	fuente VARCHAR(500), 
	importado DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (anio, semestre)
);

CREATE TABLE IF NOT EXISTS alumno (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	nombre VARCHAR(120) NOT NULL, 
	email VARCHAR(190) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	carrera_id INTEGER, 
	preferencias JSON, 
	creado DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email), 
	FOREIGN KEY(carrera_id) REFERENCES carrera (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS comision (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	periodo_id INTEGER NOT NULL, 
	materia_id INTEGER NOT NULL, 
	nombre VARCHAR(40) NOT NULL, 
	docentes JSON, 
	modalidad VARCHAR(60), 
	inicio_dictado VARCHAR(30), 
	fin_dictado VARCHAR(30), 
	instancia VARCHAR(60), 
	PRIMARY KEY (id), 
	UNIQUE (periodo_id, materia_id, nombre), 
	FOREIGN KEY(periodo_id) REFERENCES periodo (id) ON DELETE CASCADE, 
	FOREIGN KEY(materia_id) REFERENCES materia (id)
);

CREATE TABLE IF NOT EXISTS itinerario (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	carrera_id INTEGER NOT NULL, 
	titulo VARCHAR(255) NOT NULL, 
	semestre_inicio SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(carrera_id) REFERENCES carrera (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plan_estudio (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	carrera_id INTEGER NOT NULL, 
	materia_id INTEGER NOT NULL, 
	orden INTEGER NOT NULL, 
	regimen VARCHAR(40), 
	carga_horaria_semanal FLOAT, 
	carga_horaria_total FLOAT, 
	otro_requisito BOOL NOT NULL, 
	correlativas_texto JSON, 
	correlativas_sin_match JSON, 
	PRIMARY KEY (id), 
	UNIQUE (carrera_id, materia_id), 
	FOREIGN KEY(carrera_id) REFERENCES carrera (id) ON DELETE CASCADE, 
	FOREIGN KEY(materia_id) REFERENCES materia (id)
);

CREATE TABLE IF NOT EXISTS alumno_materia (
	alumno_id INTEGER NOT NULL, 
	plan_id INTEGER NOT NULL, 
	estado VARCHAR(15) NOT NULL, 
	nota FLOAT, 
	comision_id INTEGER, 
	actualizado DATETIME NOT NULL, 
	PRIMARY KEY (alumno_id, plan_id), 
	FOREIGN KEY(alumno_id) REFERENCES alumno (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES plan_estudio (id) ON DELETE CASCADE, 
	FOREIGN KEY(comision_id) REFERENCES comision (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS correlativa (
	plan_id INTEGER NOT NULL, 
	requiere_plan_id INTEGER NOT NULL, 
	PRIMARY KEY (plan_id, requiere_plan_id), 
	FOREIGN KEY(plan_id) REFERENCES plan_estudio (id) ON DELETE CASCADE, 
	FOREIGN KEY(requiere_plan_id) REFERENCES plan_estudio (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS horario_comision (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	comision_id INTEGER NOT NULL, 
	dia SMALLINT, 
	hora_desde SMALLINT, 
	hora_hasta SMALLINT, 
	dia_texto VARCHAR(30), 
	horario_texto VARCHAR(60), 
	tipo_clase VARCHAR(60), 
	aula VARCHAR(60), 
	edificacion VARCHAR(100), 
	compartido_con VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(comision_id) REFERENCES comision (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS itinerario_semestre (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	itinerario_id INTEGER NOT NULL, 
	orden SMALLINT NOT NULL, 
	anio SMALLINT NOT NULL, 
	semestre SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(itinerario_id) REFERENCES itinerario (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS itinerario_materia (
	itinerario_semestre_id INTEGER NOT NULL, 
	plan_id INTEGER NOT NULL, 
	PRIMARY KEY (itinerario_semestre_id, plan_id), 
	FOREIGN KEY(itinerario_semestre_id) REFERENCES itinerario_semestre (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES plan_estudio (id) ON DELETE CASCADE
);

