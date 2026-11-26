"""Pruebas de conectores sin internet: se simulan las respuestas HTTP."""

import io
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest
import requests

from lokbi import cache
from lokbi.ingesta import banrep, dane, socrata


class RespuestaFalsa:
    def __init__(self, contenido: bytes = b"", json_data=None, url: str = ""):
        self.content = contenido
        self._json = json_data
        self.url = url

    def json(self):
        return self._json


@pytest.fixture(autouse=True)
def cache_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "DIRECTORIO", tmp_path)


# ---------- Banco de la República (SDMX) ----------

SDMX = b"""<?xml version='1.0' encoding='UTF-8'?>
<message:GenericData xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
  xmlns:generic="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic">
 <message:DataSet>
  <generic:Series>
   <generic:SeriesKey>
    <generic:Value id="REFERENCE_AREA" value="CO" />
    <generic:Value id="UNIT_MEASURE" value="COP" />
   </generic:SeriesKey>
   <generic:Obs><generic:ObsDimension value="20261113" /><generic:ObsValue value="3301.91" /></generic:Obs>
   <generic:Obs><generic:ObsDimension value="20261114" /><generic:ObsValue value="3316.7" /></generic:Obs>
   <generic:Obs><generic:ObsDimension value="20260105" /><generic:ObsValue value="3900.0" /></generic:Obs>
  </generic:Series>
 </message:DataSet>
</message:GenericData>"""


def test_parsear_sdmx_ordena_y_quita_dimensiones_constantes():
    df = banrep.parsear_sdmx(SDMX)
    assert list(df.columns) == ["fecha", "valor"]
    assert df["fecha"].is_monotonic_increasing
    assert df.iloc[-1]["valor"] == pytest.approx(3316.7)


@pytest.mark.parametrize(
    "periodo, esperado",
    [("20261117", "2026-11-17"), ("2026-11", "2026-11-01"), ("202611", "2026-11-01"),
     ("2026-Q3", "2026-07-01"), ("2026", "2026-01-01")],
)
def test_fechas_sdmx(periodo, esperado):
    assert banrep._fecha(periodo) == pd.Timestamp(esperado)


def test_serie_recorta_fechas_que_el_servidor_ignora(monkeypatch):
    monkeypatch.setattr(banrep.red, "get", lambda url, **kw: RespuestaFalsa(SDMX, url=url))
    df, proc = banrep.serie("TRM diaria", inicio="2026-11-01")
    assert len(df) == 2  # la observación de enero queda fuera
    assert "TRM diaria" in proc.descripcion and "DF_TRM_DAILY_HIST" in proc.fuente


# ---------- DANE (IPC) ----------

def anexo_ipc_falso() -> bytes:
    filas = [
        [None, None, None],
        ["Total, Índices - Serie de empalme", None, None],
        ["Número Índice", None, None],
        ["Mes", 2023.0, 2024.0],
        ["Enero", 128.27, 138.98],
        ["Febrero", 130.40, 140.49],
        ["Diciembre", 137.72, 144.88],
        [None, None, None],
        ["Fuente: DANE.", None, None],
    ]
    buffer = io.BytesIO()
    pd.DataFrame(filas).to_excel(buffer, header=False, index=False)
    return buffer.getvalue()


def test_url_ipc():
    assert dane.url_ipc_indices(2026, 10).endswith("/IPC/oct2026/anex-IPC-Indices-oct2026.xlsx")


def test_parsear_ipc_formato_ancho_a_largo():
    df = dane.parsear_ipc_indices(anexo_ipc_falso())
    assert len(df) == 6
    assert df["fecha"].is_monotonic_increasing
    assert df.set_index("fecha").loc["2024-12-01", "indice"] == pytest.approx(144.88)


def test_ipc_retrocede_hasta_encontrar_anexo_y_calcula_inflacion(monkeypatch):
    pedidas = []

    def get_falso(url, **kw):
        pedidas.append(url)
        if "nov2026" in url:  # aún no publicado
            raise requests.HTTPError("404")
        return RespuestaFalsa(anexo_ipc_falso(), url=url)

    monkeypatch.setattr(dane.red, "get", get_falso)
    df, proc = dane.ipc(hoy=date(2026, 11, 13))
    assert "oct2026" in proc.fuente and len(pedidas) == 2
    dic = df.set_index("fecha").loc["2024-12-01"]
    # Inflación oficial 2024: 5.20 % (144.88 / 137.72 - 1)
    assert dic["var_año_corrido_pct"] == pytest.approx(5.199, abs=0.01)


# ---------- datos.gov.co (Socrata) ----------

def test_socrata_pagina_hasta_el_limite(monkeypatch):
    monkeypatch.setattr(socrata, "TAMANO_PAGINA", 2)
    datos = pd.DataFrame({"valor": [1, 2, 3, 4, 5]})
    offsets = []

    def get_falso(url, params=None, **kw):
        if url.endswith(".json"):  # metadatos
            return RespuestaFalsa(json_data={"name": "Prueba", "attribution": "Entidad X", "rowsUpdatedAt": 1700000000})
        off, lim = params["$offset"], params["$limit"]
        offsets.append(off)
        return RespuestaFalsa(datos.iloc[off : off + lim].to_csv(index=False).encode())

    monkeypatch.setattr(socrata.red, "get", get_falso)
    df, proc = socrata.consultar("abcd-1234", limite=None)
    assert df["valor"].tolist() == [1, 2, 3, 4, 5]
    assert offsets == [0, 2, 4]
    assert proc.fuente == "https://www.datos.gov.co/d/abcd-1234"
    assert "Entidad X" in proc.descripcion


# ---------- Caché ----------

def test_cache_reutiliza_y_expira(tmp_path):
    llamadas = []

    def descargar():
        llamadas.append(1)
        return pd.DataFrame({"a": [1]}), "http://fuente", "desc"

    cache.obtener("k", descargar, directorio=tmp_path)
    cache.obtener("k", descargar, directorio=tmp_path)
    assert len(llamadas) == 1
    cache.obtener("k", descargar, max_edad=timedelta(0), directorio=tmp_path)
    assert len(llamadas) == 2


def test_cache_tolera_columnas_con_tipos_mezclados(tmp_path):
    df, _ = cache.obtener(
        "mixta", lambda: (pd.DataFrame({"x": [1, "a", None]}), "f", "d"), directorio=tmp_path
    )
    df2, _ = cache.obtener("mixta", lambda: None, directorio=tmp_path)
    assert df2["x"].tolist()[:2] == ["1", "a"]


def test_cache_usa_carpeta_temporal_si_la_preferida_no_se_puede_escribir(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "DIRECTORIO", tmp_path / "solo_lectura")
    monkeypatch.setattr(cache, "_TEMPORAL", tmp_path / "temporal")
    monkeypatch.setattr(cache, "_escribibles", {tmp_path / "solo_lectura": False})
    assert cache.directorio_cache() == tmp_path / "temporal"


def test_cache_devuelve_datos_aunque_no_pueda_guardar(tmp_path, monkeypatch):
    def falla(*a, **k):
        raise PermissionError("solo lectura")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", falla)
    df, proc = cache.obtener("x", lambda: (pd.DataFrame({"a": [1]}), "f", "d"), directorio=tmp_path)
    assert df["a"].tolist() == [1] and proc.fuente == "f"
