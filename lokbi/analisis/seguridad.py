"""Cálculos de la historia "Seguridad en Colombia: los últimos dos años".

Funciones puras sobre DataFrames (sin descargas) para poder probarlas.
El script `analisis/seguridad_2026.py` las usa con los datos reales.

Ventanas de comparación: tres periodos de 12 meses que terminan en el último
mes COMPLETO. Comparar 12 meses contra 12 meses evita el efecto de temporada
(diciembre no se compara con febrero) y usa toda la información disponible.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Periodo:
    nombre: str
    inicio: pd.Timestamp  # primer día del primer mes
    fin: pd.Timestamp  # primer día del último mes (inclusive)

    @property
    def etiqueta(self) -> str:
        meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        f = lambda t: f"{meses[t.month - 1]}-{t.year}"
        return f"{f(self.inicio)} a {f(self.fin)}"

    def contiene(self, meses: pd.Series) -> pd.Series:
        return (meses >= self.inicio) & (meses <= self.fin)


def ultimo_mes_completo(meses: pd.Series) -> pd.Timestamp:
    """El último mes publicado suele estar incompleto (registros tardíos): se descarta."""
    return pd.Timestamp(meses.max()) - pd.DateOffset(months=1)


def periodos(corte: pd.Timestamp, n: int = 3) -> list[Periodo]:
    """n ventanas consecutivas de 12 meses que terminan en `corte`, de la más antigua a la más reciente."""
    salida = []
    for i in range(n - 1, -1, -1):
        fin = corte - pd.DateOffset(months=12 * i)
        inicio = fin - pd.DateOffset(months=11)
        salida.append(Periodo(f"P{n - 1 - i}", pd.Timestamp(inicio), pd.Timestamp(fin)))
    return salida


def total_por_periodo(df: pd.DataFrame, ps: list[Periodo], por: list[str] | None = None) -> pd.DataFrame:
    """Suma `cantidad` en cada periodo. Columnas: [por...] + una por periodo."""
    por = por or []
    partes = []
    for p in ps:
        sub = df[p.contiene(df["mes"])]
        s = sub.groupby(por)["cantidad"].sum() if por else pd.Series({"total": sub["cantidad"].sum()})
        partes.append(s.rename(p.nombre))
    tabla = pd.concat(partes, axis=1).fillna(0)
    return tabla.reset_index(names=por or ["_"]).drop(columns=["_"], errors="ignore")


def variacion(nuevo: pd.Series, anterior: pd.Series) -> pd.Series:
    """Variación % (vacía si el valor anterior es 0)."""
    return (nuevo / anterior.where(anterior != 0) - 1) * 100


def acumulado_12_meses(df: pd.DataFrame) -> pd.DataFrame:
    """Serie nacional mensual con la suma móvil de los últimos 12 meses (quita la estacionalidad)."""
    nac = df.groupby("mes", as_index=False)["cantidad"].sum().sort_values("mes")
    nac["ultimos_12_meses"] = nac["cantidad"].rolling(12).sum()
    return nac


def resumen_delito(df: pd.DataFrame, ps: list[Periodo], poblacion_total: float) -> dict:
    """Totales por periodo, variaciones y tasa por 100.000 habitantes del periodo más reciente."""
    t = total_por_periodo(df, ps).iloc[0]
    ultimo, penultimo, primero = ps[-1].nombre, ps[-2].nombre, ps[0].nombre
    return {
        **{p.nombre: float(t[p.nombre]) for p in ps},
        "var_ultimo_vs_anterior_pct": float(variacion(pd.Series([t[ultimo]]), pd.Series([t[penultimo]])).iloc[0]),
        "var_ultimo_vs_primero_pct": float(variacion(pd.Series([t[ultimo]]), pd.Series([t[primero]])).iloc[0]),
        "tasa_100k_ultimo": float(t[ultimo] / poblacion_total * 100_000),
    }


def por_departamento(
    df: pd.DataFrame, ps: list[Periodo], poblacion: pd.DataFrame, anio_poblacion: int, minimo_casos: int = 20
) -> pd.DataFrame:
    """Totales por departamento, tasa por 100.000 hab. del último periodo y variación.

    La variación solo se calcula si el periodo anterior tiene al menos `minimo_casos`:
    con pocos casos, pasar de 2 a 4 es "+100 %" y no significa nada.
    """
    t = total_por_periodo(df, ps, ["cod_dpto"])
    pob = poblacion[poblacion["anio"] == anio_poblacion].set_index("codigo")
    ultimo, penultimo = ps[-1].nombre, ps[-2].nombre
    t["departamento"] = t["cod_dpto"].map(pob["nombre"])
    t["poblacion"] = t["cod_dpto"].map(pob["poblacion"])
    t["tasa_100k"] = t[ultimo] / t["poblacion"] * 100_000
    var = variacion(t[ultimo], t[penultimo])
    t["variacion_pct"] = var.where(t[penultimo] >= minimo_casos)
    return t.sort_values("tasa_100k", ascending=False).reset_index(drop=True)


def contraste_fuentes(policia_anual: pd.Series, medicina_legal: pd.DataFrame) -> pd.DataFrame:
    """Homicidios por año: Policía vs Medicina Legal y diferencia %."""
    ml = medicina_legal.set_index("anio")["cantidad"]
    t = pd.DataFrame({"policia": policia_anual, "medicina_legal": ml}).dropna()
    t["diferencia_pct"] = (t["policia"] / t["medicina_legal"] - 1) * 100
    return t.reset_index(names="anio")
