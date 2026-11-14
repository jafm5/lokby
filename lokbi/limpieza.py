"""Limpieza de datos con las particularidades colombianas.

- Montos: "$ 1.234.567,89" (punto de miles, coma decimal) conviven con
  "1234567.89" (formato de las APIs).
- Coordenadas DIVIPOLA con coma decimal: "-75,504557037".
- Códigos DIVIPOLA que Excel convierte en número y pierden el cero: 5001 -> "05001".
- Nombres con y sin tildes, mayúsculas o abreviaturas ("BOGOTÁ, D.C.", "Bogota").
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

_NO_NUMERICO = re.compile(r"[^\d,.\-]")


def normalizar_texto(valor) -> str:
    """Mayúsculas, sin tildes ni puntuación, espacios simples. Para cruzar nombres."""
    if pd.isna(valor):
        return ""
    s = unicodedata.normalize("NFKD", str(valor))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s).upper()
    return re.sub(r"\s+", " ", s).strip()


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Nombres de columna en minúscula, sin tildes y con guion bajo: 'Valor Total ($)' -> 'valor_total'."""
    nuevas = [normalizar_texto(c).lower().replace(" ", "_") or f"columna_{i}" for i, c in enumerate(df.columns)]
    return df.set_axis(nuevas, axis=1)


def _detectar_decimal(textos: pd.Series) -> str:
    """Decide el separador decimal de una columna mirando todos sus valores."""
    for t in textos:
        if "," in t and "." in t:
            return "," if t.rfind(",") > t.rfind(".") else "."
    for t in textos:
        # Coma seguida de algo distinto a exactamente 3 dígitos: es decimal
        if re.search(r",(\d{1,2}|\d{4,})$", t):
            return ","
        if re.search(r"\.(\d{1,2}|\d{4,})$", t):
            return "."
    # Ambiguo ("1.234" o "1,234"): convención colombiana, coma decimal
    return ","


def a_numero(serie: pd.Series, decimal: str = "auto") -> pd.Series:
    """Convierte texto con formato de moneda o número a float.

    decimal: "auto" (detecta por columna), "," o ".".
    Valores no convertibles quedan vacíos (NaN).
    """
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)
    textos = serie.astype("string").str.strip().str.replace(_NO_NUMERICO, "", regex=True)
    no_vacios = textos.dropna()
    no_vacios = no_vacios[no_vacios != ""]
    if decimal == "auto":
        decimal = _detectar_decimal(no_vacios)
    miles = "." if decimal == "," else ","
    limpio = textos.str.replace(miles, "", regex=False).str.replace(decimal, ".", regex=False)
    return pd.to_numeric(limpio, errors="coerce")


def a_fecha(serie: pd.Series) -> pd.Series:
    """Convierte a fecha. Acepta ISO (APIs) y día/mes/año (formato colombiano)."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    textos = serie.astype("string").str.strip()
    iso = pd.to_datetime(textos, errors="coerce", format="ISO8601")
    if iso.notna().mean() >= 0.8:
        return iso
    return pd.to_datetime(textos, errors="coerce", dayfirst=True)


def codigo_divipola(serie: pd.Series, digitos: int) -> pd.Series:
    """Rellena con ceros a la izquierda: 2 dígitos (departamento) o 5 (municipio)."""
    textos = serie.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    return textos.str.zfill(digitos).where(textos.notna() & (textos != ""))
