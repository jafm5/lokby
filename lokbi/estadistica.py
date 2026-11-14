"""Resúmenes estadísticos para la página Explorar."""

from __future__ import annotations

import pandas as pd


def perfil_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por columna: tipo, nulos, valores únicos y un ejemplo."""
    total = len(df)
    filas = []
    for col in df.columns:
        serie = df[col]
        nulos = int(serie.isna().sum())
        no_nulos = serie.dropna()
        filas.append(
            {
                "columna": col,
                "tipo": str(serie.dtype),
                "nulos": nulos,
                "% nulos": round(100 * nulos / total, 1) if total else 0.0,
                "únicos": int(serie.nunique(dropna=True)),
                "ejemplo": str(no_nulos.iloc[0]) if len(no_nulos) else "",
            }
        )
    return pd.DataFrame(filas)


def descriptivos(df: pd.DataFrame) -> pd.DataFrame:
    """Estadística descriptiva de columnas numéricas, con nombres en español."""
    numericas = df.select_dtypes("number")
    if numericas.empty:
        return pd.DataFrame()
    resumen = numericas.describe().T
    resumen["mediana"] = numericas.median()
    resumen = resumen.rename(
        columns={
            "count": "n",
            "mean": "media",
            "std": "desv. estándar",
            "min": "mínimo",
            "25%": "p25",
            "50%": "p50",
            "75%": "p75",
            "max": "máximo",
        }
    )
    return resumen.drop(columns="p50")


def variacion_porcentual(actual: float, anterior: float) -> float:
    """Variación % entre dos valores. Lanza ValueError si el anterior es 0."""
    if anterior == 0:
        raise ValueError("No se puede calcular variación con valor anterior 0")
    return (actual - anterior) / abs(anterior) * 100
