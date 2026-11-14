import pandas as pd
import pytest

from lokbi.analisis import seguridad as s


def serie(meses, valores, dpto="05"):
    return pd.DataFrame({"mes": pd.to_datetime(meses), "cod_dpto": dpto, "cantidad": valores})


def test_ultimo_mes_completo_descarta_el_ultimo():
    assert s.ultimo_mes_completo(pd.Series(pd.to_datetime(["2026-08-01", "2026-09-01"]))) == pd.Timestamp("2026-08-01")


def test_periodos_de_12_meses_consecutivos():
    ps = s.periodos(pd.Timestamp("2026-08-01"))
    assert [(p.inicio, p.fin) for p in ps] == [
        (pd.Timestamp("2023-09-01"), pd.Timestamp("2024-08-01")),
        (pd.Timestamp("2024-09-01"), pd.Timestamp("2025-08-01")),
        (pd.Timestamp("2025-09-01"), pd.Timestamp("2026-08-01")),
    ]
    assert ps[-1].etiqueta == "sep-2025 a ago-2026"


def test_total_por_periodo_respeta_limites():
    ps = s.periodos(pd.Timestamp("2026-08-01"), n=2)
    df = serie(["2024-08-01", "2024-09-01", "2025-08-01", "2025-09-01", "2026-08-01", "2026-09-01"], [100, 1, 1, 10, 10, 999])
    t = s.total_por_periodo(df, ps)
    assert t.loc[0, "P0"] == 2 and t.loc[0, "P1"] == 20  # agosto-2024 y septiembre-2026 quedan fuera


def test_resumen_y_variacion():
    ps = s.periodos(pd.Timestamp("2026-08-01"), n=2)
    df = serie(["2025-01-01", "2026-01-01"], [100, 150])
    r = s.resumen_delito(df, ps, poblacion_total=1_000_000)
    assert r["var_ultimo_vs_anterior_pct"] == pytest.approx(50)
    assert r["tasa_100k_ultimo"] == pytest.approx(15)


def test_por_departamento_no_calcula_variacion_con_pocos_casos():
    ps = s.periodos(pd.Timestamp("2026-08-01"), n=2)
    df = pd.concat([serie(["2025-01-01", "2026-01-01"], [100, 120], "05"),
                    serie(["2025-01-01", "2026-01-01"], [2, 4], "97")])
    pob = pd.DataFrame({"codigo": ["05", "97"], "nombre": ["Antioquia", "Vaupés"], "anio": 2026, "poblacion": [7e6, 4e4]})
    t = s.por_departamento(df, ps, pob, 2026).set_index("cod_dpto")
    assert t.loc["05", "variacion_pct"] == pytest.approx(20)
    assert pd.isna(t.loc["97", "variacion_pct"])  # 2 → 4 no es "+100 %" confiable
    assert t.loc["97", "tasa_100k"] == pytest.approx(10)


def test_acumulado_12_meses():
    meses = pd.date_range("2024-01-01", periods=13, freq="MS")
    r = s.acumulado_12_meses(serie(meses, [1] * 13))
    assert r["ultimos_12_meses"].iloc[-1] == 12 and pd.isna(r["ultimos_12_meses"].iloc[10])


def test_contraste_fuentes():
    t = s.contraste_fuentes(pd.Series({2024: 13497}), pd.DataFrame({"anio": [2024], "cantidad": [14021]}))
    assert t.loc[0, "diferencia_pct"] == pytest.approx(-3.737, abs=0.01)
