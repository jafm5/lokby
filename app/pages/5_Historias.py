"""Historia: Seguridad en Colombia, los últimos dos años.

Todas las cifras del texto se calculan desde datos/historias/seguridad/*.csv,
generados por analisis/seguridad_2026.py. No hay números escritos a mano.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from lokbi import geo, graficas

st.set_page_config(page_title="Seguridad en Colombia · lokbi", page_icon="🛡️", layout="wide")

DATOS = Path(__file__).resolve().parents[2] / "datos" / "historias" / "seguridad"
REPO = "https://github.com/jafm5/lokby/blob/main"
CONFIG = {"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2, "filename": "lokbi_seguridad"}}


@st.cache_data
def leer(nombre: str) -> pd.DataFrame:
    return pd.read_csv(DATOS / nombre, dtype={"cod_dpto": str})


@st.cache_data
def leer_meta() -> dict:
    return json.loads((DATOS / "metadatos.json").read_text(encoding="utf-8"))


@st.cache_data(ttl=86400, show_spinner="Cargando mapa…")
def cargar_geojson():
    return geo.geojson_departamentos()[0]


def num(x: float, dec: int = 0) -> str:
    """Formato colombiano: 1.234,5"""
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x: float, dec: int = 1) -> str:
    return ("+" if x > 0 else "") + num(x, dec) + " %"


def cambio(x: float, umbral: float = 2.0) -> str:
    """Describe una variación sin exagerar: por debajo del umbral es 'casi igual'."""
    if abs(x) < umbral:
        return f"se mantuvo prácticamente igual ({pct(x)})"
    return f"{'aumentó' if x > 0 else 'disminuyó'} {num(abs(x), 1)} %"


meta = leer_meta()
P = meta["periodos"]
resumen = leer("resumen.csv").set_index("delito")
mensual = leer("mensual_nacional.csv").assign(mes=lambda d: pd.to_datetime(d["mes"]))
deptos = leer("departamentos.csv")
carac = leer("homicidio_caracteristicas.csv")
modal = leer("homicidio_modalidad_mensual.csv").assign(mes=lambda d: pd.to_datetime(d["mes"]))
secuestro = leer("secuestro.csv").set_index("periodo")
contraste = leer("contraste_medicina_legal.csv")

fuente_policia = "Ministerio de Defensa / Policía Nacional (datos.gov.co)"
fuente_pob = "proyecciones de población DANE"

# ======================= Encabezado =======================
st.title("🛡️ Seguridad en Colombia: ¿qué pasó en los últimos dos años?")
st.caption(
    f"Datos oficiales hasta {P['P2'].split(' a ')[1]} · Generado el {meta['generado'][:10]} · "
    f"[Código del análisis]({REPO}/analisis/seguridad_2026.py)"
)

st.markdown(
    f"""
Comparamos tres periodos de 12 meses con los registros oficiales de la Policía Nacional:

| | Periodo |
|---|---|
| **Hace dos años** | {P['P0']} |
| **Año anterior** | {P['P1']} |
| **Último año** | {P['P2']} |

Comparar 12 meses contra 12 meses evita que la temporada distorsione (diciembre no se compara con febrero).
"""
)

# ======================= Resumen =======================
st.header("En resumen")
h, hp, ex = resumen.loc["Homicidio"], resumen.loc["Hurto a personas"], resumen.loc["Extorsión"]
sec_var = (secuestro.loc["P2", "registros"] / secuestro.loc["P1", "registros"] - 1) * 100
sec_var_2 = (secuestro.loc["P2", "registros"] / secuestro.loc["P0", "registros"] - 1) * 100
_otros_2 = [h["var_ultimo_vs_primero_pct"], hp["var_ultimo_vs_primero_pct"], ex["var_ultimo_vs_primero_pct"]]
nota_secuestro = " Es el cambio más grande de los cuatro delitos." if abs(sec_var_2) > max(map(abs, _otros_2)) else ""

cols = st.columns(4)
cols[0].metric("Homicidios", num(h["P2"]), pct(h["var_ultimo_vs_anterior_pct"]), delta_color="inverse",
               help=f"{num(h['tasa_100k_ultimo'], 1)} por cada 100.000 habitantes")
cols[1].metric("Hurtos a personas", num(hp["P2"]), pct(hp["var_ultimo_vs_anterior_pct"]), delta_color="inverse")
cols[2].metric("Extorsiones", num(ex["P2"]), pct(ex["var_ultimo_vs_anterior_pct"]), delta_color="inverse")
cols[3].metric("Secuestros (hechos registrados)", num(secuestro.loc["P2", "registros"]), pct(sec_var), delta_color="inverse",
               help=f"{num(secuestro.loc['P2', 'victimas'])} víctimas")
st.caption("Último año frente al año anterior. En rojo, aumento; en verde, disminución.")

st.markdown(
    f"""
- **Homicidios**: {num(h['P2'])} en el último año, unos {num(h['promedio_mensual_ultimo'])} al mes
  ({num(h['tasa_100k_ultimo'], 1)} por cada 100.000 habitantes). Frente al año anterior {cambio(h['var_ultimo_vs_anterior_pct'])};
  frente a hace dos años {cambio(h['var_ultimo_vs_primero_pct'])}.
- **Hurto a personas**: {cambio(hp['var_ultimo_vs_anterior_pct'])} frente al año anterior y
  {cambio(hp['var_ultimo_vs_primero_pct'])} frente a hace dos años. *Ojo: el hurto depende de que la gente denuncie
  (ver "¿Podemos confiar en estas cifras?").*
- **Extorsión**: {cambio(ex['var_ultimo_vs_anterior_pct'])} frente al año anterior y
  {cambio(ex['var_ultimo_vs_primero_pct'])} frente a hace dos años.
- **Secuestro**: los hechos registrados pasaron de {num(secuestro.loc['P0', 'registros'])} hace dos años a
  {num(secuestro.loc['P1', 'registros'])} y luego a {num(secuestro.loc['P2', 'registros'])}
  ({pct(sec_var_2, 0)} en dos años).{nota_secuestro}
"""
)

# ======================= Tendencia =======================
st.header("La tendencia larga")
st.markdown(
    "Dos años son poco para entender una tendencia. Cada punto es el **total de los 12 meses anteriores**, "
    "lo que suaviza los picos de temporada. Un punto alto significa que ese año fue peor."
)
desde = mensual["mes"].max() - pd.DateOffset(years=8)
c = st.columns(2)
for i, delito in enumerate(["Homicidio", "Hurto a personas", "Extorsión", "Secuestro"]):
    d = mensual[(mensual["delito"] == delito) & (mensual["mes"] >= desde)].dropna(subset=["ultimos_12_meses"])
    fig = graficas.grafica(d, "lineas", "mes", "ultimos_12_meses", titulo=f"{delito}: total de los últimos 12 meses",
                           fuente=fuente_policia)
    fig.update_layout(height=340, yaxis_title=None, xaxis_title=None, yaxis_rangemode="tozero")
    c[i % 2].plotly_chart(fig, width="stretch", config=CONFIG, theme=None)
st.caption("El eje vertical empieza en cero para no exagerar los cambios. En 2020 varios delitos bajan por el confinamiento de la pandemia, sobre todo el hurto.")

# ======================= Territorio =======================
st.header("¿Dónde?")
st.markdown(
    "Comparar el número de casos entre departamentos engaña: Bogotá siempre tendrá más que Vaupés porque tiene más gente. "
    f"Por eso el mapa muestra la **tasa por cada 100.000 habitantes** ({fuente_pob} {meta['anio_poblacion']})."
)
delito = st.selectbox("Delito", ["Homicidio", "Hurto a personas", "Extorsión", "Secuestro"])
d = deptos[deptos["delito"] == delito].copy()
fig = graficas.mapa_departamentos(
    d, "cod_dpto", "tasa_100k", cargar_geojson(), "departamento",
    titulo=f"{delito}: casos por cada 100.000 habitantes, {P['P2']}",
    fuente=f"{fuente_policia}; {fuente_pob}",
)
c1, c2 = st.columns([3, 2])
c1.plotly_chart(fig, width="stretch", config=CONFIG, theme=None)
tabla = d[["departamento", "P1", "P2", "tasa_100k", "variacion_pct"]].rename(columns={
    "P1": "Año anterior", "P2": "Último año", "tasa_100k": "Tasa por 100.000", "variacion_pct": "Cambio %"})
c2.dataframe(
    tabla.style.format({"Año anterior": "{:,.0f}", "Último año": "{:,.0f}", "Tasa por 100.000": "{:,.1f}", "Cambio %": "{:+.1f}"}, na_rep="—"),
    hide_index=True, width="stretch", height=560,
)
c2.caption("“—” en Cambio %: menos de 20 casos el año anterior; con tan pocos casos, el porcentaje no dice nada (pasar de 2 a 4 es “+100 %”).")

# ======================= Homicidios =======================
st.header("Homicidios: cómo ocurren")


def comparar(categoria: str, top: int = 7) -> pd.DataFrame:
    t = carac[carac["categoria"] == categoria].copy()
    principales = t[t["periodo"] == "P2"].nlargest(top, "cantidad")["valor"]
    t = t[t["valor"].isin(principales)]
    t["periodo"] = t["periodo"].map({"P1": f"Año anterior ({P['P1']})", "P2": f"Último año ({P['P2']})"})
    t["valor"] = t["valor"].str.capitalize()
    return t


arma = carac[(carac["categoria"] == "arma") & (carac["periodo"] == "P2")]
fuego = arma.loc[arma["valor"] == "ARMA DE FUEGO", "cantidad"].sum() / arma["cantidad"].sum() * 100
zona = carac[(carac["categoria"] == "zona") & (carac["periodo"] == "P2")]
rural = zona.loc[zona["valor"] == "RURAL", "cantidad"].sum() / zona["cantidad"].sum() * 100
sexo = carac[(carac["categoria"] == "sexo") & (carac["periodo"] == "P2")]
hombres = sexo.loc[sexo["valor"] == "MASCULINO", "cantidad"].sum() / sexo["cantidad"].sum() * 100
st.markdown(
    f"En el último año, **{num(fuego, 0)} %** de los homicidios fueron con arma de fuego, "
    f"**{num(hombres, 0)} %** de las víctimas fueron hombres y **{num(rural, 0)} %** ocurrieron en zona rural."
)
fig = graficas.grafica(comparar("modalidad"), "barras", "valor", "cantidad", "periodo",
                       titulo="Homicidios por modalidad presunta", fuente=fuente_policia, horizontal=True, agrupadas=True)
fig.update_layout(height=430, xaxis_title=None, yaxis_title=None)
st.plotly_chart(fig, width="stretch", config=CONFIG, theme=None)

# ---- ¿Más ataques de grupos armados? ----
st.subheader("¿Más homicidios por grupos armados, o un cambio de clasificación?")
m = modal.copy()
m["valor"] = m["valor"].map({"SICARIATO": "Sicariato", "ATACADOS POR GAO O GAO-R": "Atacados por grupos armados (GAO)"})
p = m.pivot_table(index="mes", columns="valor", values="cantidad").fillna(0)
gao_col, sic_col = "Atacados por grupos armados (GAO)", "Sicariato"
anio_reciente = p.index.max().year
antes = p[p.index.year == anio_reciente - 1].tail(3).mean()
despues = p[p.index.year == anio_reciente].head(3).mean()
gao_tot = carac[(carac["categoria"] == "modalidad") & (carac["valor"] == "ATACADOS POR GAO O GAO-R")].set_index("periodo")["cantidad"]
veces = gao_tot["P2"] / gao_tot["P1"]
st.markdown(
    f"""
Los homicidios clasificados como **“atacados por grupos armados organizados”** pasan de {num(gao_tot['P1'])} a
{num(gao_tot['P2'])} entre el año anterior y el último ({num(veces, 1)} veces más), mientras el sicariato baja.
Pero mes a mes aparece algo importante: el salto es **abrupto en enero de {anio_reciente}**. Comparando el último trimestre de
{anio_reciente - 1} con el primero de {anio_reciente}:

- “Grupos armados” pasa de unos **{num(antes[gao_col])}** a **{num(despues[gao_col])}** al mes.
- “Sicariato” pasa de unos **{num(antes[sic_col])}** a **{num(despues[sic_col])}** al mes.
- La **suma de ambos** pasa de {num(antes.sum())} a {num(despues.sum())} al mes: no sube, incluso baja un poco.

Si los ataques de grupos armados hubieran aumentado de verdad, se esperaría que el total de homicidios subiera. En cambio,
el aumento de una categoría aparece de golpe en un mes exacto, justo cuando la otra cae en una cantidad parecida.
**Lo más probable es un cambio en cómo se clasifican los casos**, no necesariamente más ataques. Con estos datos no se
puede saber con certeza; habría que pedir a la Policía la nota metodológica.
"""
)
fig = graficas.grafica(m, "lineas", "mes", "cantidad", "valor", titulo="Homicidios al mes según modalidad presunta",
                       fuente=fuente_policia)
fig.update_layout(height=380, yaxis_title=None, xaxis_title=None, yaxis_rangemode="tozero")
st.plotly_chart(fig, width="stretch", config=CONFIG, theme=None)

# ======================= Secuestro =======================
st.header("Secuestro: atención a cómo se cuenta")
st.markdown(
    f"""
Hasta 2024 cada registro de secuestro correspondía a **una víctima**. Desde 2025 aparecen registros con **varias víctimas**
(hechos masivos, como retenciones de grupos). Si se comparan víctimas, una parte del aumento viene de ese cambio de registro.
Por eso comparamos **hechos registrados**:

| | Hace dos años | Año anterior | Último año |
|---|---|---|---|
| Hechos registrados | {num(secuestro.loc['P0', 'registros'])} | {num(secuestro.loc['P1', 'registros'])} | {num(secuestro.loc['P2', 'registros'])} |
| Víctimas | {num(secuestro.loc['P0', 'victimas'])} | {num(secuestro.loc['P1', 'victimas'])} | {num(secuestro.loc['P2', 'victimas'])} |
| Víctimas en hechos de 5 o más personas | {num(secuestro['victimas_en_masivos'].fillna(0)['P0'])} | {num(secuestro['victimas_en_masivos'].fillna(0)['P1'])} | {num(secuestro['victimas_en_masivos'].fillna(0)['P2'])} |

Aun contando solo hechos, el secuestro registrado **{cambio(sec_var_2)}** en dos años: el aumento es real y no se explica
solo por unos pocos hechos masivos.
"""
)

# ======================= Confianza =======================
st.header("¿Podemos confiar en estas cifras?")
ultimo = contraste.iloc[-1]
_menos = contraste.loc[contraste["diferencia_pct"] < 0, "anio"]
if len(_menos) and (contraste["diferencia_pct"] > 0).any():
    cruce = (f"hasta {int(_menos.min()) - 1} la Policía registraba **más** homicidios que Medicina Legal, y desde "
             f"{int(_menos.min())} registra **menos**. Esa diferencia vale la pena investigarla.")
else:
    cruce = "la diferencia entre ambas cambia según el año."
st.markdown(
    f"""
**1. Homicidio: la cifra más confiable.** Es difícil ocultar un homicidio, y existe una segunda fuente independiente:
**Medicina Legal**, que cuenta los cuerpos que examina. Las dos fuentes difieren entre
{num(contraste['diferencia_pct'].abs().min(), 0)} % y {num(contraste['diferencia_pct'].abs().max(), 0)} % según el año
(en {int(ultimo['anio'])}: Policía {num(ultimo['policia'])}, Medicina Legal {num(ultimo['medicina_legal'])}).
Están en el mismo orden de magnitud, pero no siempre se mueven igual año a año: {cruce}
Medicina Legal publica cifras definitivas con más de un año de retraso, por eso no cubre los últimos dos años.
"""
)
cc = contraste.melt(id_vars="anio", value_vars=["policia", "medicina_legal"], var_name="fuente", value_name="homicidios")
cc["fuente"] = cc["fuente"].map({"policia": "Policía Nacional", "medicina_legal": "Medicina Legal"})
fig = graficas.grafica(cc, "lineas", "anio", "homicidios", "fuente", titulo="Homicidios por año según dos fuentes oficiales",
                       fuente="Policía Nacional y Medicina Legal (datos.gov.co)")
fig.update_layout(height=360, yaxis_title=None, xaxis_title=None, yaxis_rangemode="tozero")
st.plotly_chart(fig, width="stretch", config=CONFIG, theme=None)
st.markdown(
    f"""
**2. Hurto, extorsión y secuestro dependen de la denuncia.** Si la gente denuncia menos (por desconfianza o porque
el trámite es difícil), la cifra baja aunque el delito no baje, y al revés. Una caída del hurto registrado **no prueba**
que haya menos hurtos. La Encuesta de Convivencia y Seguridad Ciudadana del DANE mide los delitos que la gente
sufre, los denuncie o no; contrastarla sería un buen siguiente análisis.

**3. El mes más reciente está incompleto.** El último mes publicado ({meta['ultimo_mes_publicado']}) muestra
cifras muy bajas (por ejemplo, {num(resumen.loc['Homicidio', 'mes_preliminar'])} homicidios frente a un promedio de
{num(resumen.loc['Homicidio', 'promedio_mensual_ultimo'])}). No es una mejora, son registros que aún no llegan.
**Lo excluimos** de todas las comparaciones.

**4. Las cifras recientes son preliminares** y pueden ajustarse cuando se actualicen.
"""
)

# ======================= Lo que no dicen =======================
st.header("Lo que estos datos NO dicen")
st.markdown(
    """
- **No explican las causas.** Que un delito suba o baje no prueba que se deba a una política, a un gobierno o a un grupo
  en particular. Muchas cosas cambian al mismo tiempo.
- **No miden lo que no se denuncia.**
- **No reflejan la experiencia de cada lugar.** Un promedio departamental puede ocultar municipios muy distintos.
"""
)

# ======================= Metodología =======================
with st.expander("Metodología, fuentes y cómo verificarlo tú mismo"):
    filas = "\n".join(f"| {k} | {v} |" for k, v in meta["fuentes"].items())
    st.markdown(
        f"""
**Fuentes**

| Dato | Enlace |
|---|---|
{filas}

**Método**
1. Se descargan los registros oficiales agregados por mes y departamento.
2. Se descarta el último mes publicado ({meta['ultimo_mes_publicado']}) por estar incompleto. Corte: {meta['corte']}.
3. Se suman tres periodos de 12 meses: {', '.join(P.values())}.
4. Tasa = casos ÷ población del departamento ({meta['anio_poblacion']}) × 100.000.
5. La variación por departamento solo se calcula con al menos 20 casos en el periodo anterior.

**Reproducir**: descarga el proyecto de [GitHub](https://github.com/jafm5/lokby) y ejecuta
`python analisis/seguridad_2026.py`. Las tablas exactas usadas en esta página están en
[`datos/historias/seguridad/`]({REPO.replace('/blob/', '/tree/')}/datos/historias/seguridad).
"""
    )
    for nombre in ["resumen.csv", "departamentos.csv", "mensual_nacional.csv", "homicidio_caracteristicas.csv",
                   "homicidio_modalidad_mensual.csv", "secuestro.csv", "contraste_medicina_legal.csv"]:
        st.download_button(f"Descargar {nombre}", (DATOS / nombre).read_bytes(), nombre, "text/csv", key=nombre)
