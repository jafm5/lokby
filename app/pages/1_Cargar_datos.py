import streamlit as st

from lokbi.ingesta.archivos import FORMATOS_SOPORTADOS, hojas_excel, leer_archivo

st.set_page_config(page_title="Cargar datos · lokbi", page_icon="📥", layout="wide")
st.title("📥 Cargar datos")

archivo = st.file_uploader("Sube un archivo", type=list(FORMATOS_SOPORTADOS))
fuente = st.text_input(
    "Fuente del dato (URL o descripción)",
    placeholder="https://www.datos.gov.co/... — descargado el 13/11/2026",
    help="Anótala siempre: sin fuente, el análisis no es verificable.",
)

if archivo is not None:
    datos = archivo.getvalue()
    opciones = {}
    if archivo.name.lower().endswith((".xlsx", ".xls")):
        hojas = hojas_excel(datos)
        if len(hojas) > 1:
            opciones["hoja"] = st.selectbox("Hoja", hojas)

    try:
        df = leer_archivo(datos, nombre=archivo.name, **opciones)
    except Exception as e:  # mostrar el error al usuario en vez de romper la página
        st.error(f"No se pudo leer el archivo: {e}")
        st.stop()

    st.session_state["df"] = df
    st.session_state["df_nombre"] = archivo.name
    st.session_state["df_fuente"] = fuente

    st.success(f"**{archivo.name}**: {len(df):,} filas × {df.shape[1]} columnas")
    st.dataframe(df.head(100), use_container_width=True)
    st.page_link("pages/2_Explorar.py", label="Explorar estos datos →", icon="🔎")
elif "df" in st.session_state:
    st.caption(f"Datos cargados actualmente: {st.session_state['df_nombre']}")
