"""Datos geográficos: códigos DIVIPOLA (DANE), coordenadas y límites departamentales.

- DIVIPOLA departamentos: datos.gov.co `vcjz-niiq` (DANE).
- DIVIPOLA municipios: datos.gov.co `gdxc-w37w` (DANE), con latitud/longitud.
- Polígonos departamentales: GeoJSON público derivado del Marco Geoestadístico
  del DANE, con el código `DPTO` en cada departamento. El cruce se hace SIEMPRE
  por código, nunca por nombre.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pandas as pd

from lokbi import cache, red
from lokbi.ingesta import socrata
from lokbi.limpieza import a_numero, codigo_divipola, normalizar_texto

URL_GEOJSON_DEPARTAMENTOS = (
    "https://gist.githubusercontent.com/john-guerra/43c7656821069d00dcbc/raw/"
    "be6a6e239cd5b5b803c6e7c2ec405b793a9064dd/Colombia.geo.json"
)
PROPIEDAD_CODIGO = "DPTO"

# Formas comunes de escribir departamentos que no coinciden con DIVIPOLA
ALIAS_DEPARTAMENTOS = {
    "BOGOTA": "11", "BOGOTA D C": "11", "BOGOTA DC": "11", "SANTAFE DE BOGOTA D C": "11",
    "DISTRITO CAPITAL": "11", "DISTRITO CAPITAL DE BOGOTA": "11",
    "SAN ANDRES PROVIDENCIA Y SANTA CATALINA": "88", "SAN ANDRES": "88", "SAN ANDRES Y PROVIDENCIA": "88",
    "ARCHIPIELAGO DE SAN ANDRES": "88", "GUAJIRA": "44", "VALLE": "76", "NORTE SANTANDER": "54",
}

_ANUAL = timedelta(days=30)


def departamentos() -> tuple[pd.DataFrame, cache.Procedencia]:
    """codigo_departamento, nombre_departamento, latitud, longitud."""
    df, proc = socrata.consultar("vcjz-niiq", limite=None, max_edad=_ANUAL)
    df = df.copy()
    df["codigo_departamento"] = codigo_divipola(df["codigo_departamento"], 2)
    for c in ("latitud", "longitud"):
        df[c] = a_numero(df[c], decimal=",")
    return df, proc


def municipios() -> tuple[pd.DataFrame, cache.Procedencia]:
    """cod_dpto, dpto, cod_mpio, nom_mpio, tipo_municipio, latitud, longitud."""
    df, proc = socrata.consultar("gdxc-w37w", limite=None, max_edad=_ANUAL)
    df = df.copy()
    df["cod_dpto"] = codigo_divipola(df["cod_dpto"], 2)
    df["cod_mpio"] = codigo_divipola(df["cod_mpio"], 5)
    for c in ("latitud", "longitud"):
        df[c] = a_numero(df[c], decimal=",")
    return df, proc


def geojson_departamentos() -> tuple[dict, cache.Procedencia]:
    """Polígonos de los 33 departamentos (incluye Bogotá D.C.)."""

    def descargar():
        texto = red.get(URL_GEOJSON_DEPARTAMENTOS).content.decode("utf-8")
        return pd.DataFrame({"geojson": [texto]}), URL_GEOJSON_DEPARTAMENTOS, "Límites departamentales (GeoJSON, MGN DANE)"

    df, proc = cache.obtener("geo-departamentos", descargar, max_edad=timedelta(days=365))
    return json.loads(df.loc[0, "geojson"]), proc


def tabla_nombres_departamento(divipola: pd.DataFrame) -> dict[str, str]:
    """Nombre normalizado -> código de 2 dígitos, incluyendo alias."""
    tabla = {
        normalizar_texto(n): c
        for n, c in zip(divipola["nombre_departamento"], divipola["codigo_departamento"])
    }
    tabla.update(ALIAS_DEPARTAMENTOS)
    return tabla


def codigo_departamento(nombres: pd.Series, divipola: pd.DataFrame | None = None) -> pd.Series:
    """Traduce nombres de departamento a código DIVIPOLA. Los no reconocidos quedan vacíos.

    Si la columna ya trae códigos numéricos (5, "05"), los normaliza a 2 dígitos.
    """
    if divipola is None:
        divipola, _ = departamentos()
    textos = nombres.astype("string").str.strip()
    if textos.dropna().str.fullmatch(r"\d{1,2}(\.0)?").all():
        return codigo_divipola(textos, 2)
    tabla = tabla_nombres_departamento(divipola)
    return nombres.map(lambda n: tabla.get(normalizar_texto(n))).astype("string")
