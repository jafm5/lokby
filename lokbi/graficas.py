"""Gráficas Plotly con un estilo consistente y la fuente siempre visible.

Reglas de diseño (ver docs/metodologia.md):
- Colores por categoría en ORDEN FIJO (paleta validada para daltonismo); máximo
  8 categorías, el resto se agrupa en "Otros". En dispersión, máximo 3.
- Mapas: una sola gama de azul (claro = poco, oscuro = mucho).
- Un solo eje Y. Nunca dos escalas en la misma gráfica.
- Líneas de 2 px, marcadores de 8 px, cuadrícula tenue.
- La fuente va DENTRO de la imagen: si alguien comparte una captura, la fuente viaja con ella.
"""

from __future__ import annotations

import textwrap

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Paleta categórica validada (modo claro), orden fijo
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GRIS_OTROS = "#8a8984"
# Gama secuencial de un solo tono (azul) para magnitudes en mapas
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
TEXTO_SECUNDARIO = "#52514e"
CUADRICULA = "rgba(128,128,128,0.18)"

MAX_CATEGORIAS = 8
MAX_CATEGORIAS_DISPERSION = 3


def limitar_categorias(df: pd.DataFrame, col: str, valor: str | None, maximo: int = MAX_CATEGORIAS) -> pd.DataFrame:
    """Deja las `maximo - 1` categorías más grandes y agrupa el resto en 'Otros'."""
    if col not in df or df[col].nunique() <= maximo:
        return df
    peso = df.groupby(col)[valor].sum() if valor else df[col].value_counts()
    principales = peso.nlargest(maximo - 1).index
    df = df.copy()
    df[col] = df[col].where(df[col].isin(principales), "Otros")
    return df


def mapa_colores(categorias) -> dict:
    """Color fijo por categoría, según su orden de aparición; 'Otros' siempre gris."""
    reales = [c for c in pd.unique(pd.Series(list(categorias))) if c != "Otros"]
    colores = {c: PALETA[i % len(PALETA)] for i, c in enumerate(reales)}
    colores["Otros"] = GRIS_OTROS
    return colores


def _pie_fuente(fuente: str | None, pasos: list[str] | None = None) -> str:
    partes = [f"Fuente: {fuente}" if fuente else "Fuente: sin registrar"]
    if pasos:
        partes.append("Procesamiento: " + "; ".join(pasos))
    texto = " · ".join(partes)
    return "<br>".join(textwrap.wrap(texto, 150)[:3])


def estilo(fig: go.Figure, titulo: str = "", fuente: str | None = None, pasos: list[str] | None = None) -> go.Figure:
    """Aplica el estilo común y agrega la fuente al pie de la imagen."""
    pie = _pie_fuente(fuente, pasos)
    lineas_pie = pie.count("<br>") + 1
    fig.update_layout(
        title={"text": titulo, "x": 0, "xanchor": "left", "font": {"size": 18}},
        font={"family": "Inter, Segoe UI, Arial, sans-serif", "size": 13},
        margin={"l": 10, "r": 10, "t": 60 if titulo else 30, "b": 60 + 16 * lineas_pie},
        legend={"orientation": "h", "y": -0.15, "x": 0, "title": None},
        hoverlabel={"font_size": 13},
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, ticks="outside", ticklen=4)
    fig.update_yaxes(gridcolor=CUADRICULA, zeroline=False, tickformat=",~r")
    fig.add_annotation(
        text=pie, showarrow=False, xref="paper", yref="paper", x=0, y=0,
        yshift=-(45 + 16 * lineas_pie), xanchor="left", yanchor="top", align="left",
        font={"size": 11, "color": TEXTO_SECUNDARIO},
    )
    return fig


def grafica(
    df: pd.DataFrame,
    tipo: str,
    x: str,
    y: str,
    color: str | None = None,
    titulo: str = "",
    fuente: str | None = None,
    pasos: list[str] | None = None,
    horizontal: bool = False,
    agrupadas: bool = False,
) -> go.Figure:
    """tipo: 'barras', 'lineas' o 'dispersion'. `agrupadas`: barras lado a lado en vez de apiladas."""
    datos = df
    colores = None
    if color:
        maximo = MAX_CATEGORIAS_DISPERSION if tipo == "dispersion" else MAX_CATEGORIAS
        datos = limitar_categorias(df, color, y if tipo != "dispersion" else None, maximo)
        colores = mapa_colores(datos[color])

    comunes = dict(color=color, color_discrete_map=colores, color_discrete_sequence=PALETA)
    if tipo == "barras":
        if horizontal:
            fig = px.bar(datos, x=y, y=x, orientation="h", **comunes)
            fig.update_yaxes(categoryorder="total ascending")
        else:
            fig = px.bar(datos, x=x, y=y, **comunes)
        fig.update_traces(marker_line_width=0)
        if agrupadas:
            fig.update_layout(barmode="group", bargroupgap=0.08)
    elif tipo == "lineas":
        fig = px.line(datos.sort_values(x), x=x, y=y, markers=len(datos) <= 40, **comunes)
        fig.update_traces(line_width=2, marker_size=8)
        fig.update_layout(hovermode="x unified")
    elif tipo == "dispersion":
        fig = px.scatter(datos, x=x, y=y, **comunes)
        fig.update_traces(marker={"size": 8, "line": {"width": 1, "color": "white"}})
    else:
        raise ValueError(f"Tipo de gráfica desconocido: {tipo}")

    if not color:
        fig.update_layout(showlegend=False)
    if horizontal and tipo == "barras":
        fig.update_xaxes(gridcolor=CUADRICULA, showgrid=True, tickformat=",~r")
        fig.update_yaxes(showgrid=False, title=None)
    return estilo(fig, titulo, fuente, pasos)


def mapa_departamentos(
    df: pd.DataFrame,
    codigo: str,
    valor: str,
    geojson: dict,
    nombre: str | None = None,
    titulo: str = "",
    fuente: str | None = None,
    pasos: list[str] | None = None,
) -> go.Figure:
    """Mapa coroplético por departamento. `codigo` = código DIVIPOLA de 2 dígitos."""
    fig = px.choropleth(
        df,
        geojson=geojson,
        locations=codigo,
        featureidkey="properties.DPTO",
        color=valor,
        color_continuous_scale=SECUENCIAL,
        hover_name=nombre,
        hover_data={codigo: True, valor: ":,.2f"},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_traces(marker_line_color="white", marker_line_width=0.6)
    fig.update_layout(height=650, coloraxis_colorbar={"title": None, "thickness": 12, "tickformat": ",~r"})
    return estilo(fig, titulo, fuente, pasos)


def mapa_municipios(
    df: pd.DataFrame,
    lat: str,
    lon: str,
    valor: str,
    nombre: str | None = None,
    titulo: str = "",
    fuente: str | None = None,
    pasos: list[str] | None = None,
) -> go.Figure:
    """Mapa de puntos por municipio: tamaño y color según el valor."""
    datos = df.dropna(subset=[lat, lon, valor])
    datos = datos[datos[valor] > 0]
    fig = px.scatter_map(
        datos,
        lat=lat,
        lon=lon,
        size=valor,
        color=valor,
        color_continuous_scale=SECUENCIAL[2:],
        size_max=35,
        hover_name=nombre,
        hover_data={lat: False, lon: False, valor: ":,.2f"},
        zoom=4.3,
        center={"lat": 4.6, "lon": -74.1},
        map_style="carto-positron",
    )
    fig.update_layout(height=650, coloraxis_colorbar={"title": None, "thickness": 12, "tickformat": ",~r"})
    return estilo(fig, titulo, fuente, pasos)
