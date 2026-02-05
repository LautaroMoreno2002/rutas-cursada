CREATE DATABASE IF NOT EXISTS carreras;

USE carreras;

CREATE TABLE IF NOT EXISTS carrera (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  url_plan_estudios TEXT,
  duracion_anios INTEGER,
  titulo_otorgado TEXT,
  modalidad TEXT
);