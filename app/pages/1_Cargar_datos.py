from datetime import date

import streamlit as st

import estado
from lokbi.ingesta import banrep, dane, socrata
from lokbi.ingesta.archivos import FORMATOS_SOPORTADOS, hojas_excel, leer_archivo

st.set_page_config(page_title="Cargar datos · lokbi", page_icon="📥", layout="wide")
st.title("📥 Cargar datos")


def guardar(df, nombre: str, fuente: str) -> None:
    """Deja la tabla disponible para las demás páginas."""
    estado.cargar(df, nombre, fuente)
    st.success(f"**{nombre}**: {len(df):,} filas × {df.shape[1]} columnas")
    st.caption(f"Fuente: {fuente}")
    st.dataframe(df.head(100), width="stretch")
    c1, c2, c3 = st.columns(3)
    c1.page_link("pages/2_Explorar.py", label="Explorar →", icon="🔎")
    c2.page_link("pages/3_Transformar.py", label="Transformar →", icon="🧹")
    c3.page_link("pages/4_Graficar.py", label="Graficar →", icon="📊")


def con_errores(funcion, *args, **kwargs):
    """Ejecuta una descarga mostrando un error legible si la fuente falla."""
    try:
        with st.spinner("Descargando…"):
            return funcion(*args, **kwargs)
    except Exception as e:
        st.error(f"No se pudo obtener el dato: {e}")
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_datasets(texto: str):
    return socrata.buscar(texto)


@st.cache_data(ttl=3600, show_spinner=False)
def info_dataset(dataset_id: str):
    return socrata.info(dataset_id)


tab_archivo, tab_socrata, tab_banrep, tab_dane = st.tabs(
    ["📄 Archivo propio", "🏛️ datos.gov.co", "🏦 Banco de la República", "📈 DANE"]
)

# ---------------- Archivo propio ----------------
with tab_archivo:
    archivo = st.file_uploader("Sube un archivo", type=list(FORMATOS_SOPORTADOS))
    fuente = st.text_input(
        "Fuente del dato (URL o descripción)",
        placeholder="https://... — descargado el dd/mm/aaaa",
        help="Anótala siempre: sin fuente, el análisis no es verificable.",
    )
    if archivo is not None:
        datos = archivo.getvalue()
        opciones = {}
        if archivo.name.lower().endswith((".xlsx", ".xls")):
            hojas = hojas_excel(datos)
            if len(hojas) > 1:
                opciones["hoja"] = st.selectbox("Hoja", hojas)
        df = con_errores(leer_archivo, datos, nombre=archivo.name, **opciones)
        if df is not None:
            guardar(df, archivo.name, fuente or "⚠️ sin fuente registrada")

# ---------------- datos.gov.co ----------------
with tab_socrata:
    st.markdown(
        "Portal de datos abiertos del Estado. Cada dataset tiene un **id** de 9 caracteres "
        "que aparece en su URL (ej. `datos.gov.co/d/32sa-8pi3`)."
    )
    texto = st.text_input("Buscar datasets", placeholder="secop, homicidios, presupuesto…")
    if texto:
        resultados = con_errores(buscar_datasets, texto)
        if resultados is not None:
            st.dataframe(resultados, width="stretch", hide_index=True)

    opciones_conocidas = {f"{v} ({k})": k for k, v in socrata.CONOCIDOS.items()}
    elegido = st.selectbox("Datasets frecuentes", ["—"] + list(opciones_conocidas))
    dataset_id = st.text_input(
        "Id del dataset",
        value=opciones_conocidas.get(elegido, ""),
        max_chars=9,
    ).strip()

    with st.expander("Filtros SoQL (opcional)"):
        st.caption("SQL simplificado de Socrata. Ver https://dev.socrata.com/docs/queries/")
        select = st.text_input("$select (columnas)", placeholder="nombre_entidad, valor_del_contrato")
        where = st.text_input("$where (condición)", placeholder="fecha_de_firma >= '2024-01-01'")
        group = st.text_input("$group (agrupar en el servidor)", placeholder="departamento",
                              help="Con $select usa funciones como sum(valor_del_contrato) o count(*)")
        order = st.text_input("$order (orden)", placeholder="fecha_de_firma DESC")
    limite = st.number_input("Máximo de filas", 100, 1_000_000, 10_000, step=10_000)

    if dataset_id and st.button("Descargar de datos.gov.co", type="primary"):
        meta = con_errores(info_dataset, dataset_id)
        if meta:
            st.markdown(f"**{meta.nombre}** · {meta.entidad} · actualizado {meta.actualizado}")
            r = con_errores(
                socrata.consultar, dataset_id, select or None, where or None, order or None, int(limite),
                group=group or None,
            )
            if r:
                df, proc = r
                guardar(df, meta.nombre, proc.texto())

# ---------------- Banco de la República ----------------
with tab_banrep:
    st.markdown("Series oficiales del Banco de la República (API SDMX). *No incluye el IPC: está en la pestaña DANE.*")
    nombre_serie = st.selectbox("Serie", list(banrep.SERIES))
    c1, c2 = st.columns(2)
    inicio = c1.date_input("Desde", date(date.today().year - 5, 1, 1), min_value=date(1960, 1, 1))
    fin = c2.date_input("Hasta", date.today())
    if st.button("Descargar serie", type="primary"):
        r = con_errores(banrep.serie, nombre_serie, inicio, fin)
        if r:
            df, proc = r
            guardar(df, nombre_serie, proc.texto())

# ---------------- DANE ----------------
with tab_dane:
    st.markdown(
        "**IPC (inflación)**: índice mensual total nacional desde 2003 con variaciones "
        "mensual, anual y año corrido, tomado del último anexo publicado."
    )
    if st.button("Descargar IPC", type="primary"):
        r = con_errores(dane.ipc)
        if r:
            df, proc = r
            guardar(df, "IPC total nacional", proc.texto())

    st.divider()
    url = st.text_input(
        "Otro anexo Excel del DANE (URL)",
        placeholder="https://www.dane.gov.co/files/operaciones/....xlsx",
    )
    if url and st.button("Descargar anexo"):
        r = con_errores(dane.descargar_excel, url)
        if r:
            df, proc = r
            guardar(df, url.rsplit("/", 1)[-1], proc.texto())
