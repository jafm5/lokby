"""Pruebas contra las APIs reales. Requieren internet.

Se ejecutan a mano:  pytest -m red
Sirven para detectar cuando una fuente oficial cambia de formato o de URL.
"""

from datetime import timedelta

import pytest

from lokbi.ingesta import banrep, dane, socrata

pytestmark = pytest.mark.red
SIN_CACHE = timedelta(0)


def test_trm_datos_gov_co():
    df, _ = socrata.consultar("32sa-8pi3", order="vigenciadesde DESC", limite=5, max_edad=SIN_CACHE)
    assert len(df) == 5 and {"valor", "vigenciadesde"} <= set(df.columns)


def test_trm_banrep():
    df, _ = banrep.serie("TRM diaria", inicio="2024-01-01", fin="2024-12-31", max_edad=SIN_CACHE)
    assert 200 < len(df) <= 366
    assert 3500 < df["valor"].mean() < 4500  # TRM promedio 2024 ≈ 4.070


def test_ipc_dane_coincide_con_cifras_oficiales():
    df, _ = dane.ipc(max_edad=SIN_CACHE)
    s = df.set_index("fecha")["var_anual_pct"]
    assert s["2023-12-01"] == pytest.approx(9.28, abs=0.01)
    assert s["2024-12-01"] == pytest.approx(5.20, abs=0.01)


def test_poblacion_dane_consistente():
    from lokbi.ingesta import dane as d

    dep, _ = d.poblacion("departamento", max_edad=SIN_CACHE)
    assert dep["codigo"].nunique() == 33
    total_2025 = dep.loc[dep["anio"] == 2025, "poblacion"].sum()
    assert 50e6 < total_2025 < 56e6  # proyección DANE 2025 ≈ 53,1 millones


def test_divipola_coincide_con_geojson():
    from lokbi import geo

    divi, _ = geo.departamentos()
    gj, _ = geo.geojson_departamentos()
    assert set(divi["codigo_departamento"]) == {f["properties"]["DPTO"] for f in gj["features"]}


def test_paginas_de_la_app_sin_errores():
    """Recorre las páginas como un usuario (la historia descarga el mapa)."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app/Inicio.py", default_timeout=300).run()
    for pagina in ["pages/2_Explorar.py", "pages/5_Historias.py"]:
        at.switch_page(pagina).run()
        assert not at.exception, (pagina, at.exception)
