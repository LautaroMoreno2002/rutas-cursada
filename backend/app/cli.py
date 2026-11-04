"""Comandos de administración.

    python -m app.cli init-db
    python -m app.cli importar-carreras data/carreras.json
    python -m app.cli importar-periodo data/materias_del_periodo.json [--anio 2026 --semestre 1]
    python -m app.cli demo            # crea tablas y carga los datos de demostración
    python -m app.cli schema-sql      # imprime el DDL MySQL generado desde los modelos
"""
import argparse
import json
from pathlib import Path

from .database import SessionLocal, crear_tablas, engine
from .services.importador import cargar_json, importar_carreras, importar_periodo

DEMO = Path(__file__).resolve().parent.parent / "data" / "demo"


def schema_sql() -> str:
    from sqlalchemy.dialects import mysql
    from sqlalchemy.schema import CreateTable

    from . import models  # noqa: F401
    from .database import Base

    partes = [
        "-- Generado con: python -m app.cli schema-sql (no editar a mano)",
        "CREATE DATABASE IF NOT EXISTS rutas_cursada CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "USE rutas_cursada;",
    ]
    for tabla in Base.metadata.sorted_tables:
        ddl = str(CreateTable(tabla).compile(dialect=mysql.dialect())).strip()
        partes.append(ddl.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1) + ";")
    return "\n\n".join(partes) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    sub.add_parser("demo")
    sub.add_parser("schema-sql")
    c = sub.add_parser("importar-carreras")
    c.add_argument("archivo")
    per = sub.add_parser("importar-periodo")
    per.add_argument("archivo")
    per.add_argument("--anio", type=int)
    per.add_argument("--semestre", type=int, choices=[1, 2])
    args = p.parse_args(argv)

    if args.cmd == "schema-sql":
        print(schema_sql())
        return

    crear_tablas()
    print(f"Base: {engine.url.render_as_string(hide_password=True)}")
    with SessionLocal() as db:
        if args.cmd == "importar-carreras":
            print(json.dumps(importar_carreras(db, cargar_json(args.archivo)), ensure_ascii=False, indent=2))
        elif args.cmd == "importar-periodo":
            r = importar_periodo(db, cargar_json(args.archivo), args.anio, args.semestre)
            print(json.dumps(r, ensure_ascii=False, indent=2))
        elif args.cmd == "demo":
            print(importar_carreras(db, cargar_json(DEMO / "carreras.json")))
            for f in sorted(DEMO.glob("periodo_*.json")):
                r = importar_periodo(db, cargar_json(f))
                print(f.name, {k: v for k, v in r.items() if k != "horarios_sin_parsear"})


if __name__ == "__main__":
    main()
