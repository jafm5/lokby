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


AGREGACIONES = {"Suma": "sum", "Promedio": "mean", "Mediana": "median", "Conteo": "count", "Máximo": "max", "Mínimo": "min"}


def agregar(df: pd.DataFrame, por: list[str], valor: str | None, funcion: str = "sum") -> pd.DataFrame:
    """Agrupa por columnas. Con `funcion='count'` o sin `valor` cuenta filas."""
    por = [p for p in por if p]
    if not por:
        raise ValueError("Indica al menos una columna para agrupar")
    if valor is None or funcion == "count":
        return df.groupby(por, dropna=False).size().reset_index(name="conteo")
    return df.groupby(por, dropna=False)[valor].agg(funcion).reset_index()


def deflactar(
    valores: pd.Series,
    fechas: pd.Series,
    ipc: pd.DataFrame,
    fecha_base: pd.Timestamp | str | None = None,
) -> pd.Series:
    """Convierte pesos corrientes a pesos constantes de `fecha_base`.

    valor_real = valor_nominal × IPC(base) / IPC(mes de la fecha)

    `ipc` debe tener columnas `fecha` (primer día del mes) e `indice`
    (como devuelve `lokbi.ingesta.dane.ipc`). `fecha_base` por defecto es el
    último mes publicado; si es un año ("2025"), se usa diciembre de ese año
    o el último mes disponible de ese año. Fechas sin IPC publicado quedan vacías.
    """
    indice = ipc.set_index(pd.to_datetime(ipc["fecha"]))["indice"].sort_index()
    if fecha_base is None:
        base = indice.iloc[-1]
    else:
        fb = pd.Timestamp(str(fecha_base))
        if len(str(fecha_base)) == 4:  # solo año
            del_anio = indice[indice.index.year == fb.year]
            if del_anio.empty:
                raise ValueError(f"No hay IPC para el año {fecha_base}")
            base = del_anio.iloc[-1]
        else:
            fb = fb.to_period("M").to_timestamp()
            if fb not in indice.index:
                raise ValueError(f"No hay IPC para {fb:%Y-%m}")
            base = indice[fb]
    meses = pd.to_datetime(fechas).dt.to_period("M").dt.to_timestamp()
    ipc_fecha = meses.map(indice)
    return valores.astype(float) * base / ipc_fecha


def tasa_por_habitantes(conteo: pd.Series, poblacion: pd.Series, por: int = 100_000) -> pd.Series:
    """Tasa por cada `por` habitantes (por defecto 100.000)."""
    return conteo.astype(float) / poblacion.astype(float) * por


def variacion_porcentual(actual: float, anterior: float) -> float:
    """Variación % entre dos valores. Lanza ValueError si el anterior es 0."""
    if anterior == 0:
        raise ValueError("No se puede calcular variación con valor anterior 0")
    return (actual - anterior) / abs(anterior) * 100
