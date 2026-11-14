import pandas as pd
import pytest

from lokbi.estadistica import descriptivos, perfil_columnas, variacion_porcentual


def test_perfil_cuenta_nulos():
    df = pd.DataFrame({"a": [1, None, 3, None], "b": ["x", "y", "y", "z"]})
    perfil = perfil_columnas(df).set_index("columna")
    assert perfil.loc["a", "nulos"] == 2
    assert perfil.loc["a", "% nulos"] == 50.0
    assert perfil.loc["b", "únicos"] == 3


def test_descriptivos_media_y_mediana():
    df = pd.DataFrame({"v": [1, 2, 3, 10], "t": list("abcd")})
    res = descriptivos(df)
    assert list(res.index) == ["v"]
    assert res.loc["v", "media"] == 4
    assert res.loc["v", "mediana"] == 2.5


def test_variacion_porcentual():
    # IPC: 100 -> 109.28 es 9.28 %
    assert variacion_porcentual(109.28, 100) == pytest.approx(9.28)
    with pytest.raises(ValueError):
        variacion_porcentual(5, 0)
