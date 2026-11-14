"""Lectura de archivos en distintos formatos hacia un DataFrame de pandas.

Pensado para los archivos típicos de fuentes colombianas:
- CSV de datos.gov.co (coma, UTF-8) y CSV exportados desde Excel en español
  (punto y coma, codificación latin-1/cp1252).
- Anexos Excel del DANE, que suelen traer títulos y notas antes de la tabla.
- JSON (lista de registros, como devuelve la API de Socrata).
- Parquet.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import BinaryIO, Union

import pandas as pd

Fuente = Union[str, Path, bytes, BinaryIO]

FORMATOS_SOPORTADOS = ("csv", "txt", "tsv", "xlsx", "xls", "json", "parquet")
_CODIFICACIONES = ("utf-8-sig", "cp1252", "latin-1")


class FormatoNoSoportado(ValueError):
    """El archivo tiene una extensión que no sabemos leer."""


def _a_bytes(fuente: Fuente) -> bytes:
    if isinstance(fuente, bytes):
        return fuente
    if isinstance(fuente, (str, Path)):
        return Path(fuente).read_bytes()
    datos = fuente.read()
    return datos if isinstance(datos, bytes) else datos.encode("utf-8")


def _decodificar(datos: bytes) -> tuple[str, str]:
    """Devuelve (texto, codificación usada). latin-1 nunca falla, es el último recurso."""
    for cod in _CODIFICACIONES:
        try:
            return datos.decode(cod), cod
        except UnicodeDecodeError:
            continue
    raise AssertionError("inalcanzable: latin-1 decodifica cualquier byte")


def _detectar_separador(texto: str) -> str:
    muestra = "\n".join(texto.splitlines()[:50])
    try:
        return csv.Sniffer().sniff(muestra, delimiters=",;\t|").delimiter
    except csv.Error:
        # Sin evidencia clara: el más frecuente en la primera línea
        primera = texto.splitlines()[0] if texto else ""
        return max(",;\t|", key=primera.count)


def leer_csv(fuente: Fuente, sep: str | None = None) -> pd.DataFrame:
    texto, _ = _decodificar(_a_bytes(fuente))
    sep = sep or _detectar_separador(texto)
    return pd.read_csv(io.StringIO(texto), sep=sep)


def _fila_encabezado(crudo: pd.DataFrame, max_filas: int = 30) -> int:
    """Primera fila con al menos la mitad de celdas llenas y mayoría de texto.

    Los anexos del DANE ponen logo, título y notas arriba de la tabla real.
    """
    ancho = crudo.shape[1]
    for i in range(min(max_filas, len(crudo))):
        fila = crudo.iloc[i]
        llenas = fila.dropna()
        if len(llenas) >= max(2, ancho / 2) and sum(isinstance(v, str) for v in llenas) >= len(llenas) / 2:
            return i
    return 0


def leer_excel(fuente: Fuente, hoja: str | int = 0, encabezado: int | None = None) -> pd.DataFrame:
    datos = _a_bytes(fuente)
    if encabezado is None:
        crudo = pd.read_excel(io.BytesIO(datos), sheet_name=hoja, header=None)
        encabezado = _fila_encabezado(crudo)
    df = pd.read_excel(io.BytesIO(datos), sheet_name=hoja, header=encabezado)
    df = df.dropna(how="all").dropna(axis=1, how="all")
    return df.reset_index(drop=True)


def hojas_excel(fuente: Fuente) -> list[str]:
    return pd.ExcelFile(io.BytesIO(_a_bytes(fuente))).sheet_names


def leer_json(fuente: Fuente) -> pd.DataFrame:
    texto, _ = _decodificar(_a_bytes(fuente))
    contenido = json.loads(texto)
    if isinstance(contenido, dict):
        # Formas comunes: {"data": [...]} o {"results": [...]}
        for clave in ("data", "results", "records", "items"):
            if isinstance(contenido.get(clave), list):
                contenido = contenido[clave]
                break
        else:
            contenido = [contenido]
    return pd.json_normalize(contenido)


def leer_parquet(fuente: Fuente) -> pd.DataFrame:
    return pd.read_parquet(io.BytesIO(_a_bytes(fuente)))


def leer_archivo(fuente: Fuente, nombre: str | None = None, **opciones) -> pd.DataFrame:
    """Lee cualquier formato soportado según su extensión.

    `nombre` es necesario cuando `fuente` son bytes o un archivo subido
    (para conocer la extensión).
    """
    if nombre is None:
        nombre = str(fuente) if isinstance(fuente, (str, Path)) else getattr(fuente, "name", "")
    ext = Path(nombre).suffix.lower().lstrip(".")
    if ext in ("csv", "txt"):
        return leer_csv(fuente, **opciones)
    if ext == "tsv":
        return leer_csv(fuente, sep="\t")
    if ext in ("xlsx", "xls"):
        return leer_excel(fuente, **opciones)
    if ext == "json":
        return leer_json(fuente)
    if ext == "parquet":
        return leer_parquet(fuente)
    raise FormatoNoSoportado(
        f"Formato '{ext or 'desconocido'}' no soportado. Usa: {', '.join(FORMATOS_SOPORTADOS)}"
    )
