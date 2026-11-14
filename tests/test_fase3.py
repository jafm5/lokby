"""Limpieza, pesos constantes, tasas, población, DIVIPOLA y gráficas (sin internet)."""

import io

import pandas as pd
import pytest

from lokbi import cache, geo, graficas
from lokbi.estadistica import agregar, deflactar, tasa_por_habitantes
from lokbi.ingesta import dane
from lokbi.limpieza import a_fecha, a_numero, codigo_divipola, normalizar_columnas, normalizar_texto


@pytest.fixture(autouse=True)
def cache_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "DIRECTORIO", tmp_path)


# ---------- Limpieza ----------

@pytest.mark.parametrize(
    "valores, esperado",
    [
        (["$ 1.234.567,89", "$ 500,00"], [1234567.89, 500.0]),  # pesos colombianos
        (["1,234,567.89", "10.5"], [1234567.89, 10.5]),           # formato inglés
        (["-75,504557037", "6,702"], [-75.504557037, 6.702]),      # coordenadas DIVIPOLA
        (["1.234", "56.789"], [1234.0, 56789.0]),                 # ambiguo: punto de miles
        (["1234567.5", "100"], [1234567.5, 100.0]),               # API
        (["abc", None], [None, None]),
    ],
)
def test_a_numero(valores, esperado):
    r = a_numero(pd.Series(valores, dtype="object"))
    assert r.tolist() == pytest.approx(esperado, nan_ok=True) if None not in esperado else r.isna().all()


def test_a_numero_respeta_decimal_forzado():
    assert a_numero(pd.Series(["1.234"]), decimal=".").iloc[0] == pytest.approx(1.234)


def test_a_fecha_iso_y_dia_mes():
    assert a_fecha(pd.Series(["2024-12-31T00:00:00.000"])).iloc[0] == pd.Timestamp("2024-12-31")
    assert a_fecha(pd.Series(["05/03/2024"])).iloc[0] == pd.Timestamp("2024-03-05")  # 5 de marzo


def test_codigo_divipola_recupera_cero():
    assert codigo_divipola(pd.Series([5001, "8001", "05001", 5.0]), 5).tolist()[:3] == ["05001", "08001", "05001"]
    assert codigo_divipola(pd.Series([5.0, "11"]), 2).tolist() == ["05", "11"]


def test_normalizar():
    assert normalizar_texto("  Bogotá, D.C. ") == "BOGOTA D C"
    assert list(normalizar_columnas(pd.DataFrame(columns=["Valor Total ($)", "Año"])).columns) == ["valor_total", "ano"]


# ---------- Estadística ----------

IPC = pd.DataFrame(
    {"fecha": pd.to_datetime(["2023-12-01", "2024-06-01", "2024-12-01"]), "indice": [137.72, 143.38, 144.88]}
)


def test_deflactar_a_un_anio_base():
    montos = pd.Series([1_000_000.0, 1_000_000.0])
    fechas = pd.Series(pd.to_datetime(["2023-12-15", "2024-12-20"]))
    r = deflactar(montos, fechas, IPC, "2024")
    # Un millón de dic-2023 equivale a 1.000.000 × 144,88 / 137,72 pesos de dic-2024
    assert r.iloc[0] == pytest.approx(1_000_000 * 144.88 / 137.72)
    assert r.iloc[1] == pytest.approx(1_000_000)


def test_deflactar_fecha_sin_ipc_queda_vacia():
    r = deflactar(pd.Series([1.0]), pd.Series(pd.to_datetime(["2020-01-01"])), IPC)
    assert r.isna().all()


def test_tasa_y_agregar():
    assert tasa_por_habitantes(pd.Series([50]), pd.Series([1_000_000])).iloc[0] == 5.0
    df = pd.DataFrame({"d": ["A", "A", "B"], "v": [1, 2, 3]})
    assert agregar(df, ["d"], None).set_index("d")["conteo"].to_dict() == {"A": 2, "B": 1}
    assert agregar(df, ["d"], "v", "sum").set_index("d")["v"].to_dict() == {"A": 3, "B": 3}


# ---------- Población DANE ----------

def libro_poblacion(nivel: str) -> bytes:
    if nivel == "departamento":
        cab = ["DP", "DPNOM", "AÑO", "ÁREA GEOGRÁFICA", "TOTAL"]
        datos = [["05", "Antioquia", 2025, "Cabecera Municipal", 5_000_000],
                 ["05", "Antioquia", 2025, "Total", 6_900_000],
                 ["11", "Bogotá, D.C.", 2025, "Total", 7_900_000]]
    else:
        cab = ["DP", "DPNOM", "MPIO", "DPMP", "AÑO", "ÁREA GEOGRÁFICA", "TOTAL"]
        datos = [["05", "Antioquia", 5001, "Medellín", 2025, "Total", 2_600_000],
                 ["05", "Antioquia", 5001, "Medellín", 2025, "Centros Poblados y Rural Disperso", 50_000]]
    titulos = [["PROYECCIONES DE POBLACIÓN"] + [None] * (len(cab) - 1), [None] * len(cab)]
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as w:
        pd.DataFrame([["Índice"]]).to_excel(w, sheet_name="Índice", header=False, index=False)
        pd.DataFrame([["PPED"]]).to_excel(w, sheet_name="PPED", header=False, index=False)
        pd.DataFrame(titulos + [cab] + datos).to_excel(w, sheet_name="Datos", header=False, index=False)
    return buffer.getvalue()


def test_poblacion_departamental_solo_total():
    df = dane.parsear_poblacion(libro_poblacion("departamento"), "departamento")
    assert df[["codigo", "anio", "poblacion"]].values.tolist() == [["05", 2025, 6_900_000], ["11", 2025, 7_900_000]]


def test_poblacion_municipal_recupera_cero_del_codigo():
    df = dane.parsear_poblacion(libro_poblacion("municipio"), "municipio")
    assert df.loc[0, "codigo"] == "05001" and df.loc[0, "codigo_departamento"] == "05"
    assert len(df) == 1


# ---------- DIVIPOLA ----------

DIVIPOLA = pd.DataFrame(
    {"codigo_departamento": ["05", "11", "52", "88"],
     "nombre_departamento": ["ANTIOQUIA", "BOGOTÁ, D.C.", "NARIÑO",
                             "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA"]}
)


def test_codigo_departamento_por_nombre_y_alias():
    nombres = pd.Series(["antioquia", "Bogotá D.C.", "Narino", "San Andrés", "Atlántida", None])
    r = geo.codigo_departamento(nombres, DIVIPOLA)
    assert r.tolist()[:4] == ["05", "11", "52", "88"]
    assert r.iloc[4:].isna().all()  # "Atlántida" no existe; vacío no se inventa


def test_codigo_departamento_desde_codigos_numericos():
    assert geo.codigo_departamento(pd.Series([5, 11]), DIVIPOLA).tolist() == ["05", "11"]


# ---------- Gráficas ----------

def test_limitar_categorias_agrupa_en_otros():
    df = pd.DataFrame({"c": list("ABCDEFGHIJ"), "v": range(10, 0, -1)})
    r = graficas.limitar_categorias(df, "c", "v", maximo=4)
    assert sorted(r["c"].unique()) == ["A", "B", "C", "Otros"]


def test_colores_fijos_por_categoria():
    colores = graficas.mapa_colores(["Bogotá", "Cali", "Otros"])
    assert colores["Bogotá"] == graficas.PALETA[0] and colores["Otros"] == graficas.GRIS_OTROS


@pytest.mark.parametrize("tipo", ["barras", "lineas", "dispersion"])
def test_grafica_incluye_fuente_y_pasos(tipo):
    df = pd.DataFrame({"x": [1, 2, 3], "y": [3, 1, 2]})
    fig = graficas.grafica(df, tipo, "x", "y", titulo="T", fuente="DANE", pasos=["filtro(a)"])
    pie = fig.layout.annotations[0].text
    assert "Fuente: DANE" in pie and "filtro(a)" in pie
    assert not any(k.startswith("yaxis2") for k in fig.layout.to_plotly_json())  # nunca doble eje


def test_mapa_departamentos_usa_codigo_dpto():
    geojson = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"DPTO": "05"},
         "geometry": {"type": "Polygon", "coordinates": [[[-76, 6], [-75, 6], [-75, 7], [-76, 6]]]}}]}
    fig = graficas.mapa_departamentos(pd.DataFrame({"cod": ["05"], "v": [10]}), "cod", "v", geojson, fuente="X")
    assert fig.data[0].featureidkey == "properties.DPTO"
