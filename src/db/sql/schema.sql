CREATE DATABASE IF NOT EXISTS carreras;

USE carreras;

CREATE TABLE IF NOT EXISTS carrera (
  id_carrera SERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  url_plan_estudios TEXT,
  cantidad_materias TINYINT,
  duracion_anios INTEGER,
  titulo TEXT,
  modalidad TEXT
);

CREATE TABLE IF NOT EXISTS materia (
  id_materia SERIAL PRIMARY KEY,
  codigo INTEGER NOT NULL UNIQUE,
  nombre TEXT,
  regimen_cursada VARCHAR(40),
  carga_horaria_semanal TINYINT,
  carga_horaria_total TINYINT,
);

CREATE TABLE IF NOT EXISTS comision (
  id_comision SERIAL PRIMARY KEY,
  numero_comision TEXT,
  dia TEXT,
  horario TEXT,
  edificacion TEXT,
  aula TEXT,
  tipo_clase TEXT
);

CREATE TABLE IF NOT EXISTS periodo  (
  id_periodo SERIAL PRIMARY KEY,
  inicio_dictado TEXT,
  fin_dictado TEXT,
  /* SEMESTRE (?) */
);
