import streamlit as st

st.set_page_config(page_title="lokbi · Datos de Colombia", page_icon="📊", layout="wide")

st.title("📊 lokbi")
st.subheader("Datos públicos de Colombia, analizados de forma verificable")

st.markdown("### 📰 Análisis publicados")
st.page_link("pages/5_Historias.py", label="Seguridad en Colombia: ¿qué pasó en los últimos dos años?", icon="🛡️")
st.divider()

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

st.markdown(
    """
**Haz tu propio análisis** (menú lateral):
1. **Cargar datos**: archivo propio, datos.gov.co, Banco de la República o DANE.
2. **Explorar**: tipos, vacíos, estadística y consultas SQL.
3. **Transformar**: limpiar, filtrar, agrupar, pesos constantes, tasas por habitante.
4. **Graficar**: barras, líneas, dispersión y mapas, con la fuente incluida en la imagen.
"""
)
