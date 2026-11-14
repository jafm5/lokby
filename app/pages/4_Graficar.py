import pandas as pd
import streamlit as st

import estado
from lokbi import geo, graficas
from lokbi.estadistica import AGREGACIONES, agregar
from lokbi.limpieza import codigo_divipola

st.set_page_config(page_title="Graficar · lokbi", page_icon="📊", layout="wide")
st.title("📊 Graficar")

df = estado.exigir_datos()
estado.encabezado()

CONTEO = "(conteo de filas)"
columnas = list(df.columns)
numericas = list(df.select_dtypes("number").columns)
fechas = list(df.select_dtypes("datetime").columns)
CONFIG = {"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2, "filename": "lokbi"}}


@st.cache_data(ttl=86400, show_spinner="Descargando límites departamentales…")
def cargar_geojson():
    return geo.geojson_departamentos()


@st.cache_data(ttl=86400, show_spinner="Descargando DIVIPOLA…")
def cargar_divipola(nivel: str):
    return geo.departamentos() if nivel == "departamento" else geo.municipios()


def resumir(por: list[str], valor: str, funcion: str) -> tuple[pd.DataFrame, str]:
    """Agrupa y devuelve (tabla, nombre de la columna resultante)."""
    if valor == CONTEO:
        return agregar(df_graf, por, None, "count"), "conteo"
    return agregar(df_graf, por, valor, AGREGACIONES[funcion]), valor


tipo = st.radio(
    "Tipo de gráfica",
    ["Barras", "Líneas", "Dispersión", "Mapa por departamento", "Mapa por municipio"],
    horizontal=True,
    help="Barras: comparar categorías · Líneas: evolución en el tiempo · Dispersión: relación entre dos números · Mapas: comparar territorios",
)

df_graf = df
tabla = None
fig = None
pasos = estado.pasos()

try:
    if tipo in ("Barras", "Líneas"):
        c1, c2, c3, c4 = st.columns(4)
        x = c1.selectbox("Eje X (categoría o fecha)", columnas)
        y = c2.selectbox("Valor", [CONTEO] + numericas)
        funcion = c3.selectbox("Cálculo", [k for k in AGREGACIONES if k != "Conteo"], disabled=y == CONTEO)
        color = c4.selectbox("Separar por color (opcional)", ["(ninguno)"] + [c for c in columnas if c != x])
        color = None if color == "(ninguno)" else color

        if x in fechas:
            periodo = st.select_slider("Agrupar fechas por", ["Día", "Mes", "Trimestre", "Año"], value="Mes")
            codigo = {"Día": "D", "Mes": "M", "Trimestre": "Q", "Año": "Y"}[periodo]
            df_graf = df.assign(**{x: df[x].dt.to_period(codigo).dt.to_timestamp()})

        tabla, col_y = resumir([x, color], y, funcion)
        horizontal = False
        if tipo == "Barras":
            c1, c2 = st.columns(2)
            horizontal = c1.toggle("Barras horizontales", value=x not in fechas and tabla[x].nunique() > 6)
            top = c2.number_input("Mostrar solo los N mayores (0 = todos)", 0, 500, 15 if x not in fechas else 0)
            if top and not color:
                tabla = tabla.nlargest(int(top), col_y)
            elif top and color:
                mayores = tabla.groupby(x)[col_y].sum().nlargest(int(top)).index
                tabla = tabla[tabla[x].isin(mayores)]
        titulo_auto = f"{'Número de filas' if y == CONTEO else f'{funcion} de {y}'} por {x}"
        titulo = st.text_input("Título", titulo_auto)
        fig = graficas.grafica(
            tabla, "barras" if tipo == "Barras" else "lineas", x, col_y, color,
            titulo, estado.fuente(), pasos, horizontal=horizontal,
        )

    elif tipo == "Dispersión":
        if len(numericas) < 2:
            st.info("Se necesitan al menos dos columnas numéricas.")
            st.stop()
        c1, c2, c3 = st.columns(3)
        x = c1.selectbox("Eje X", numericas)
        y = c2.selectbox("Eje Y", [c for c in numericas if c != x])
        color = c3.selectbox("Color (máx. 3 grupos)", ["(ninguno)"] + columnas)
        color = None if color == "(ninguno)" else color
        titulo = st.text_input("Título", f"{y} frente a {x}")
        tabla = df[[c for c in {x, y, color} if c]]
        fig = graficas.grafica(tabla, "dispersion", x, y, color, titulo, estado.fuente(), pasos)
        st.caption("Correlación no implica causalidad: que dos cosas se muevan juntas no prueba que una cause la otra.")

    elif tipo == "Mapa por departamento":
        c1, c2, c3 = st.columns(3)
        col_dpto = c1.selectbox("Columna de departamento (nombre o código)", columnas,
                                index=columnas.index("cod_dpto") if "cod_dpto" in columnas else 0)
        y = c2.selectbox("Valor", [CONTEO] + numericas)
        funcion = c3.selectbox("Cálculo", [k for k in AGREGACIONES if k != "Conteo"], disabled=y == CONTEO)
        divipola, _ = cargar_divipola("departamento")
        df_graf = df.assign(_cod=geo.codigo_departamento(df[col_dpto], divipola))
        excluidas = df_graf["_cod"].isna()
        if excluidas.any():
            sin = df_graf.loc[excluidas & df_graf[col_dpto].notna(), col_dpto].unique()
            detalle = f": {', '.join(map(str, sin[:15]))}" if len(sin) else " (sin departamento)"
            st.warning(f"{int(excluidas.sum()):,} filas excluidas del mapa por no tener departamento reconocible{detalle}")
        tabla, col_y = resumir(["_cod"], y, funcion)
        nombres = divipola.set_index("codigo_departamento")["nombre_departamento"]
        tabla = tabla.assign(departamento=tabla["_cod"].map(nombres)).rename(columns={"_cod": "cod_dpto"})
        titulo = st.text_input("Título", f"{'Número de filas' if y == CONTEO else f'{funcion} de {y}'} por departamento")
        geojson, geo_proc = cargar_geojson()
        fig = graficas.mapa_departamentos(tabla, "cod_dpto", col_y, geojson, "departamento", titulo, estado.fuente(), pasos)
        if not col_y.endswith("_por_100k"):
            st.caption("💡 Si el valor es un conteo, considera convertirlo en tasa por 100.000 habitantes (página Transformar).")

    else:  # Mapa por municipio
        c1, c2, c3 = st.columns(3)
        col_mpio = c1.selectbox("Columna con código DIVIPOLA de municipio (5 dígitos)", columnas)
        y = c2.selectbox("Valor", [CONTEO] + numericas)
        funcion = c3.selectbox("Cálculo", [k for k in AGREGACIONES if k != "Conteo"], disabled=y == CONTEO)
        df_graf = df.assign(_cod=codigo_divipola(df[col_mpio], 5))
        tabla, col_y = resumir(["_cod"], y, funcion)
        municipios, _ = cargar_divipola("municipio")
        tabla = tabla.merge(
            municipios[["cod_mpio", "nom_mpio", "dpto", "latitud", "longitud"]],
            left_on="_cod", right_on="cod_mpio", how="left",
        ).drop(columns="_cod")
        tabla["municipio"] = tabla["nom_mpio"] + " (" + tabla["dpto"] + ")"
        sin = int(tabla["latitud"].isna().sum())
        if sin:
            st.warning(f"{sin} códigos sin coordenadas en DIVIPOLA, excluidos del mapa.")
        titulo = st.text_input("Título", f"{'Número de filas' if y == CONTEO else f'{funcion} de {y}'} por municipio")
        fig = graficas.mapa_municipios(tabla, "latitud", "longitud", col_y, "municipio", titulo, estado.fuente(), pasos)

except Exception as e:
    st.error(f"No se pudo construir la gráfica: {e}")

if fig is not None:
    st.plotly_chart(fig, width="stretch", config=CONFIG, theme=None)
    st.caption("📷 Para descargar la imagen usa el ícono de cámara en la esquina de la gráfica. La fuente queda incluida en la imagen.")
    with st.expander("Ver datos de la gráfica"):
        st.dataframe(tabla, width="stretch", hide_index=True)
        st.download_button(
            "Descargar datos (CSV)",
            tabla.to_csv(index=False).encode("utf-8-sig"),
            "lokbi_grafica.csv",
            "text/csv",
        )
