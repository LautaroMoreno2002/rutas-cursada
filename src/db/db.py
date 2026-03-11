import psycopg2
import os

def get_db_connection():
  return psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT", 5432)
  )

def ejecutar_sql(path_sql):
    with open(path_sql, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()

    cur.close()
    conn.close()
    print("Base de datos inicializada correctamente")

if __name__ == "__main__":
    ejecutar_sql("schema.sql")