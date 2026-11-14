import streamlit as st

st.set_page_config(page_title="lokbi · Datos de Colombia", page_icon="📊", layout="wide")

st.title("📊 lokbi")
st.subheader("Datos públicos de Colombia, analizados de forma verificable")

st.markdown(
    """
Este sitio analiza datos **oficiales** (datos.gov.co, DANE, Banco de la República)
y archivos propios. Cada análisis indica:

1. **Fuente**: enlace al dato original y fecha de descarga.
2. **Método**: qué limpieza y cálculos se hicieron (el código es público).
3. **Limitaciones**: lo que el dato *no* permite concluir.

Si una cifra no se puede verificar, no se publica.
"""
)

st.info("Empieza en **Cargar datos** (menú lateral) y luego ve a **Explorar**.")
