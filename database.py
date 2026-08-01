"""
Conexión a la MISMA base de datos del ERP principal (PostgreSQL en Neon).
Esta app no crea tablas nuevas — usa las tablas 'empleados', 'ubicaciones'
y 'horas' que ya existen, creadas por el ERP.
"""
import os
from contextlib import contextmanager
import pandas as pd

try:
    import streamlit as st
except ImportError:
    st = None


def _get_database_url():
    if st is not None:
        try:
            url = st.secrets.get("database_url")
            if url:
                return url
        except Exception:
            pass
    return os.environ.get("DATABASE_URL")


DATABASE_URL = _get_database_url()


@contextmanager
def get_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "No se encontró 'database_url' en los Secrets. Esta app necesita conectarse "
            "a la misma base de datos PostgreSQL que usa el ERP."
        )
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def execute(conn, sql: str, params=None):
    import psycopg2.extras
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql.replace("?", "%s"), params or ())
    return cur


def read_sql_query(sql: str, conn, params=None) -> pd.DataFrame:
    sql_t = sql.replace("?", "%s")
    if params is not None:
        return pd.read_sql_query(sql_t, conn, params=params)
    return pd.read_sql_query(sql_t, conn)


def get_config(clave, default=""):
    with get_connection() as conn:
        row = execute(conn, "SELECT valor FROM configuracion WHERE clave=?", (clave,)).fetchone()
        return row["valor"] if row else default


def get_ubicaciones():
    with get_connection() as conn:
        rows = execute(conn, "SELECT * FROM ubicaciones ORDER BY nombre").fetchall()
        return [dict(r) for r in rows]
