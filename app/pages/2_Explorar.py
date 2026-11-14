import plotly.express as px
import streamlit as st

from lokbi.consultas import consultar_sql
from lokbi.estadistica import descriptivos, perfil_columnas

st.set_page_config(page_title="Explorar · lokbi", page_icon="🔎", layout="wide")
st.title("🔎 Explorar")

if "df" not in st.session_state:
    st.warning("Primero carga un archivo.")
    st.page_link("pages/1_Cargar_datos.py", label="Ir a Cargar datos", icon="📥")
    st.stop()

df = st.session_state["df"]
st.caption(
    f"Archivo: **{st.session_state['df_nombre']}** · "
    f"Fuente: {st.session_state.get('df_fuente') or '⚠️ sin fuente registrada'}"
)

c1, c2, c3 = st.columns(3)
c1.metric("Filas", f"{len(df):,}")
c2.metric("Columnas", df.shape[1])
c3.metric("Celdas vacías", f"{int(df.isna().sum().sum()):,}")

st.subheader("Columnas")
st.dataframe(perfil_columnas(df), width="stretch", hide_index=True)

st.subheader("Estadística descriptiva (columnas numéricas)")
desc = descriptivos(df)
if desc.empty:
    st.info("No hay columnas numéricas. Si hay montos guardados como texto, habrá que limpiarlos.")
else:
    st.dataframe(desc.style.format("{:,.2f}"), width="stretch")

    st.subheader("Distribución")
    col = st.selectbox("Columna", list(desc.index))
    st.plotly_chart(px.histogram(df, x=col, nbins=40), width="stretch")

st.subheader("Consulta SQL")
st.caption("Escribe SQL sobre la tabla `datos` (motor DuckDB). Ej.: agrupar, filtrar, sumar.")
columnas = ", ".join(f'"{c}"' for c in df.columns[:3])
sql = st.text_area("SQL", f"SELECT {columnas}\nFROM datos\nLIMIT 20", height=120)
if st.button("Ejecutar"):
    try:
        resultado = consultar_sql(df, sql)
        st.dataframe(resultado, width="stretch")
        st.download_button(
            "Descargar resultado (CSV)",
            resultado.to_csv(index=False).encode("utf-8-sig"),
            "resultado.csv",
            "text/csv",
        )
    except Exception as e:
        st.error(f"Error en la consulta: {e}")
