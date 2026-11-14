"""Consultas SQL sobre DataFrames con DuckDB.

DuckDB ejecuta SQL directamente sobre tablas de pandas o archivos Parquet/CSV,
sin servidor. Es mucho más rápido que pandas para agrupaciones sobre millones
de filas (por ejemplo, SECOP).
"""

from __future__ import annotations

import duckdb
import pandas as pd


def consultar_sql(df: pd.DataFrame, sql: str, nombre: str = "datos") -> pd.DataFrame:
    """Ejecuta `sql` donde la tabla `nombre` es `df`. Conexión aislada en memoria."""
    con = duckdb.connect()
    try:
        con.register(nombre, df)
        return con.execute(sql).df()
    finally:
        con.close()
