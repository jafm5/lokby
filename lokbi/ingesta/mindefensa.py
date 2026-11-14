"""Estadística delictiva del Ministerio de Defensa / Policía Nacional (datos.gov.co).

Cada dataset tiene una fila por registro con `fecha_hecho`, `cod_depto`,
`cod_muni` (DIVIPOLA) y `cantidad`. Algunos traen columnas adicionales
(homicidio: arma_medio, _modalidad_presunta, sexo, zona).

Se agrega en el servidor de datos.gov.co (SoQL `$group`) para no descargar
cientos de miles de filas.

Advertencias (ver docs/fuentes.md):
- Son delitos REGISTRADOS por la Policía: hurto, extorsión, violencia
  intrafamiliar y delitos sexuales dependen de que la víctima denuncie.
- El último mes publicado suele estar incompleto (registros tardíos).
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from lokbi import cache
from lokbi.ingesta import socrata
from lokbi.limpieza import codigo_divipola

DELITOS = {
    "Homicidio": "m8fd-ahd9",
    "Hurto a personas": "4rxi-8m8d",
    "Extorsión": "q2ib-t9am",
    "Secuestro": "d7zw-hpf4",
    "Hurto a residencias": "7mn7-vzqp",
    "Hurto a comercio": "7i2x-h5vp",
    "Hurto a vehículos": "csb4-y6v2",
    "Violencia intrafamiliar": "gepp-dxcs",
    "Delitos sexuales": "bz43-8ahq",
}

_MAX_EDAD = timedelta(days=1)


def mensual_por_departamento(delito: str, desde: str = "2015-01-01") -> tuple[pd.DataFrame, cache.Procedencia]:
    """Conteo mensual por departamento: mes, cod_dpto, cantidad."""
    df, proc = socrata.consultar(
        DELITOS[delito],
        select="date_trunc_ym(fecha_hecho) AS mes, cod_depto, sum(cantidad) AS cantidad",
        where=f"fecha_hecho >= '{desde}'",
        group="mes, cod_depto",
        limite=None,
        max_edad=_MAX_EDAD,
    )
    df = df.assign(
        mes=pd.to_datetime(df["mes"]),
        cod_dpto=codigo_divipola(df["cod_depto"], 2),
        cantidad=pd.to_numeric(df["cantidad"]),
    ).drop(columns="cod_depto")
    return df[["mes", "cod_dpto", "cantidad"]], proc


def por_categoria(
    delito: str, columna: str, desde: str, hasta: str
) -> tuple[pd.DataFrame, cache.Procedencia]:
    """Total por una columna descriptiva (ej. arma_medio) en un periodo [desde, hasta)."""
    df, proc = socrata.consultar(
        DELITOS[delito],
        select=f"{columna}, sum(cantidad) AS cantidad",
        where=f"fecha_hecho >= '{desde}' AND fecha_hecho < '{hasta}'",
        group=columna,
        limite=None,
        max_edad=_MAX_EDAD,
    )
    return df.assign(cantidad=pd.to_numeric(df["cantidad"])), proc


def mensual_por_categoria(
    delito: str, columna: str, valores: list[str], desde: str, hasta: str
) -> tuple[pd.DataFrame, cache.Procedencia]:
    """Conteo mensual nacional de ciertos valores de una columna: mes, valor, cantidad."""
    lista = ", ".join(f"'{v}'" for v in valores)
    df, proc = socrata.consultar(
        DELITOS[delito],
        select=f"date_trunc_ym(fecha_hecho) AS mes, {columna} AS valor, sum(cantidad) AS cantidad",
        where=f"fecha_hecho >= '{desde}' AND fecha_hecho < '{hasta}' AND {columna} IN ({lista})",
        group="mes, valor",
        limite=None,
        max_edad=_MAX_EDAD,
    )
    return df.assign(mes=pd.to_datetime(df["mes"]), cantidad=pd.to_numeric(df["cantidad"])), proc


def registros_y_victimas(delito: str, desde: str, hasta: str, min_victimas: int | None = None) -> dict:
    """Número de registros y suma de víctimas en [desde, hasta).

    Con `min_victimas` cuenta solo registros con al menos esa cantidad (hechos masivos).
    """
    where = f"fecha_hecho >= '{desde}' AND fecha_hecho < '{hasta}'"
    if min_victimas:
        where += f" AND cantidad >= {int(min_victimas)}"
    df, _ = socrata.consultar(
        DELITOS[delito],
        select="count(*) AS registros, sum(cantidad) AS victimas",
        where=where,
        order="registros",
        limite=1,
        max_edad=_MAX_EDAD,
    )
    fila = df.iloc[0] if len(df) else {}
    return {k: float(pd.to_numeric(fila.get(k), errors="coerce") or 0) for k in ("registros", "victimas")}


def medicina_legal_homicidios_anuales() -> tuple[pd.DataFrame, cache.Procedencia]:
    """Presuntos homicidios por año según Medicina Legal (cifras definitivas 2015-2024).

    Fuente independiente de la Policía: sirve para contrastar.
    """
    df, proc = socrata.consultar(
        "vtub-3de2",
        select="a_o_del_hecho AS anio, count(*) AS cantidad",
        group="anio",
        limite=None,
        max_edad=timedelta(days=30),
    )
    return df.assign(anio=pd.to_numeric(df["anio"]), cantidad=pd.to_numeric(df["cantidad"])), proc
