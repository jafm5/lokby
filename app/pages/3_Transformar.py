import pandas as pd
import streamlit as st

import estado
from lokbi import geo
from lokbi.consultas import consultar_sql
from lokbi.estadistica import AGREGACIONES, agregar, deflactar, tasa_por_habitantes
from lokbi.ingesta import dane
from lokbi.limpieza import a_fecha, a_numero, codigo_divipola

st.set_page_config(page_title="Transformar · lokbi", page_icon="🧹", layout="wide")
st.title("🧹 Transformar")
st.markdown(
    "Cada paso queda registrado y aparece al pie de las gráficas, para que cualquiera "
    "sepa exactamente cómo se procesó el dato."
)

df = estado.exigir_datos()
estado.encabezado()
estado.mostrar_aviso()

c1, c2 = st.columns([1, 5])
if c1.button("↩️ Deshacer", disabled=not estado.pasos()):
    paso = estado.deshacer()
    st.toast(f"Deshecho: {paso}")
    st.rerun()
c2.caption(f"{len(df):,} filas × {df.shape[1]} columnas")

columnas = list(df.columns)
numericas = list(df.select_dtypes("number").columns)
fechas = list(df.select_dtypes("datetime").columns)


@st.cache_data(ttl=86400, show_spinner="Descargando IPC del DANE…")
def cargar_ipc():
    return dane.ipc()


@st.cache_data(ttl=86400, show_spinner="Descargando proyecciones de población del DANE…")
def cargar_poblacion(nivel: str):
    return dane.poblacion(nivel)


@st.cache_data(ttl=86400, show_spinner="Descargando DIVIPOLA…")
def cargar_divipola():
    return geo.departamentos()


def ejecutar(funcion):
    """Ejecuta una transformación mostrando errores legibles."""
    try:
        funcion()
    except Exception as e:
        st.error(f"No se pudo aplicar: {e}")


# ---------------- Tipos ----------------
with st.expander("🔢 Convertir texto a número"):
    st.caption("Para montos como \"$ 1.234.567,89\" o coordenadas \"-75,50\". Lo que no se pueda convertir queda vacío.")
    cols = st.multiselect("Columnas", columnas, key="num_cols")
    decimal = st.radio("Separador decimal", ["auto", ",", "."], horizontal=True,
                       help="auto: lo detecta por columna; si es ambiguo usa la coma (convención colombiana)")
    if cols and st.button("Convertir a número"):
        def _():
            nuevo = df.copy()
            perdidos = []
            for c in cols:
                nuevo[c] = a_numero(df[c], decimal)
                n = int(nuevo[c].isna().sum() - df[c].isna().sum())
                if n:
                    perdidos.append(f"{c}: {n:,}")
            estado.aplicar(nuevo, f"número({', '.join(cols)})")
            if perdidos:
                estado.aviso("Valores que no se pudieron convertir → " + "; ".join(perdidos))
            st.rerun()
        ejecutar(_)

with st.expander("📅 Convertir texto a fecha"):
    st.caption("Acepta formato ISO (2024-12-31) y día/mes/año (31/12/2024).")
    cols = st.multiselect("Columnas", columnas, key="fecha_cols")
    if cols and st.button("Convertir a fecha"):
        def _():
            nuevo = df.copy()
            for c in cols:
                nuevo[c] = a_fecha(df[c])
            estado.aplicar(nuevo, f"fecha({', '.join(cols)})")
            st.rerun()
        ejecutar(_)

# ---------------- Filas ----------------
with st.expander("🔍 Filtrar filas"):
    st.caption("Condición SQL sobre la tabla. Ej.: `departamento = 'ANTIOQUIA' AND valor > 1000000`")
    condicion = st.text_input("WHERE", key="filtro")
    if condicion and st.button("Filtrar"):
        def _():
            nuevo = consultar_sql(df, f"SELECT * FROM datos WHERE {condicion}")
            estado.aplicar(nuevo, f"filtro({condicion}) → {len(nuevo):,} filas")
            st.rerun()
        ejecutar(_)

with st.expander("🧮 Agrupar"):
    st.caption("Resume la tabla: p. ej. suma del valor de los contratos por departamento y año.")
    por = st.multiselect("Agrupar por", columnas, key="agr_por")
    funcion = st.selectbox("Cálculo", list(AGREGACIONES), key="agr_fun")
    valor = None
    if AGREGACIONES[funcion] != "count":
        valor = st.selectbox("Columna a calcular", numericas or ["(no hay columnas numéricas)"], key="agr_val")
    if por and st.button("Agrupar"):
        def _():
            nuevo = agregar(df, por, valor, AGREGACIONES[funcion])
            detalle = "filas" if AGREGACIONES[funcion] == "count" else valor
            estado.aplicar(nuevo, f"{funcion.lower()} de {detalle} por {', '.join(por)}")
            st.rerun()
        ejecutar(_)

# ---------------- Comparaciones justas ----------------
with st.expander("💰 Pesos constantes (descontar la inflación)"):
    st.markdown(
        "Un peso de 2015 no vale lo mismo que uno de 2025. Para comparar montos de "
        "distintos años se llevan todos a pesos de un mismo año con el IPC del DANE:  \n"
        "`valor_real = valor × IPC(base) / IPC(mes del valor)`"
    )
    if not numericas or not fechas:
        st.info("Necesitas una columna numérica (monto) y una de fecha. Conviértelas arriba.")
    else:
        c1, c2, c3 = st.columns(3)
        col_valor = c1.selectbox("Monto", numericas, key="def_val")
        col_fecha = c2.selectbox("Fecha del monto", fechas, key="def_fecha")
        ipc_df, ipc_proc = cargar_ipc()
        anios = sorted(ipc_df["fecha"].dt.year.unique(), reverse=True)
        base = c3.selectbox("Pesos de", [str(a) for a in anios], key="def_base",
                            help="Se usa diciembre de ese año, o el último mes publicado si el año está en curso")
        if st.button("Calcular pesos constantes"):
            def _():
                nuevo = df.copy()
                nombre = f"{col_valor}_pesos_{base}"
                nuevo[nombre] = deflactar(df[col_valor], df[col_fecha], ipc_df, base)
                sin_ipc = int(nuevo[nombre].isna().sum() - df[col_valor].isna().sum())
                estado.aplicar(nuevo, f"{col_valor} en pesos de {base} (IPC DANE)")
                if sin_ipc:
                    estado.aviso(f"{sin_ipc:,} filas sin IPC publicado para su fecha (antes de 2003 o meses recientes).")
                st.rerun()
            ejecutar(_)
        st.caption(f"IPC: {ipc_proc.texto()}")

with st.expander("🗺️ Código DIVIPOLA de departamento"):
    st.caption("Traduce nombres (\"Bogotá D.C.\", \"NARIÑO\", \"Valle\") al código oficial de 2 dígitos. Necesario para mapas y población.")
    col_nombre = st.selectbox("Columna con el departamento", columnas, key="dpto_col")
    if st.button("Agregar código"):
        def _():
            divipola, _ = cargar_divipola()
            nuevo = df.copy()
            nuevo["cod_dpto"] = geo.codigo_departamento(df[col_nombre], divipola)
            sin = df.loc[nuevo["cod_dpto"].isna() & df[col_nombre].notna(), col_nombre].unique()
            estado.aplicar(nuevo, f"cod_dpto desde {col_nombre}")
            if len(sin):
                estado.aviso(f"Sin reconocer ({len(sin)}): " + ", ".join(map(str, sin[:20])))
            st.rerun()
        ejecutar(_)

with st.expander("👥 Población y tasa por 100.000 habitantes"):
    st.markdown(
        "Comparar conteos entre territorios engaña: Bogotá siempre tendrá más casos que "
        "Vaupés. La tasa por habitante permite comparar. Población: proyecciones DANE (CNPV 2018)."
    )
    nivel = st.radio("Nivel", ["departamento", "municipio"], horizontal=True)
    c1, c2, c3 = st.columns(3)
    col_cod = c1.selectbox(
        "Columna con el código DIVIPOLA", columnas, key="pob_cod",
        help="2 dígitos para departamento, 5 para municipio",
    )
    opciones_anio = ["(año fijo)"] + columnas
    col_anio = c2.selectbox("Columna con el año", opciones_anio, key="pob_anio")
    anio_fijo = c2.number_input("Año fijo", 2018, 2042, 2025, key="pob_anio_fijo") if col_anio == "(año fijo)" else None
    col_conteo = c3.selectbox("Valor a convertir en tasa (opcional)", ["(ninguno)"] + numericas, key="pob_val")
    if st.button("Agregar población"):
        def _():
            pob, pob_proc = cargar_poblacion(nivel)
            nuevo = df.copy()
            digitos = 2 if nivel == "departamento" else 5
            clave = codigo_divipola(nuevo[col_cod], digitos)
            if anio_fijo:
                anio = pd.Series(anio_fijo, index=nuevo.index)
            elif pd.api.types.is_datetime64_any_dtype(nuevo[col_anio]):
                anio = nuevo[col_anio].dt.year
            else:
                anio = pd.to_numeric(nuevo[col_anio], errors="coerce")
            indice = pob.set_index(["codigo", "anio"])["poblacion"]
            llaves = pd.MultiIndex.from_arrays([clave, anio.astype("Int64")])
            nuevo["poblacion"] = indice.reindex(llaves).to_numpy()
            paso = f"población {nivel} (DANE)"
            if col_conteo != "(ninguno)":
                nuevo[f"{col_conteo}_por_100k"] = tasa_por_habitantes(nuevo[col_conteo], nuevo["poblacion"])
                paso += f"; {col_conteo} por 100.000 hab."
            sin = int(nuevo["poblacion"].isna().sum())
            estado.aplicar(nuevo, paso)
            if sin:
                estado.aviso(f"{sin:,} filas sin población: revisa el código (¿{digitos} dígitos?) o el año (proyecciones 2018 en adelante).")
            st.rerun()
        ejecutar(_)

st.subheader("Vista previa")
st.dataframe(df.head(200), width="stretch")
st.download_button(
    "Descargar tabla transformada (CSV)",
    df.to_csv(index=False).encode("utf-8-sig"),
    "lokbi_transformado.csv",
    "text/csv",
    help="Útil también para llevar los datos limpios a Power BI o Looker Studio",
)
