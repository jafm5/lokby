"""Conector a la API SDMX del Banco de la República.

Servicio: https://totoro.banrep.gov.co/nsi-jax-ws/rest/
- Solo responde XML (SDMX-ML 2.1 "GenericData"); pedir JSON o CSV da 406/501.
- startPeriod/endPeriod solo se respetan a nivel de año, y endPeriod en el mismo
  año que startPeriod da 404 (verificado nov-2026). `serie()` pide años
  completos y recorta las fechas exactas localmente.
- Cada serie es un "dataflow". Los *_HIST traen la historia completa; los
  *_LATEST, solo lo reciente.
- NO publica el IPC: para inflación ver `lokbi.ingesta.dane`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, timedelta

import pandas as pd

from lokbi import cache, red

BASE = "https://totoro.banrep.gov.co/nsi-jax-ws/rest"

# Dataflows verificados (nov-2026). Nombre legible -> id
SERIES = {
    "TRM diaria": "DF_TRM_DAILY_HIST",
    "Tasa de política monetaria (diaria)": "DF_CBR_DAILY_HIST",
    "Tasa de política monetaria (promedio mensual)": "DF_CBR_MONTHLY_HIST",
    "IBR diaria": "DF_IBR_DAILY_HIST",
    "DTF diaria": "DF_DTF_DAILY_HIST",
    "DTF mensual": "DF_DTF_MONTHLY_HIST",
    "UVR diaria": "DF_UVR_DAILY_HIST",
    "COLCAP mensual": "DF_COLCAP_MONTHLY_HIST",
    "TES mensual": "DF_TES_MONTHLY_HIST",
    "Tasas de interés mensual": "DF_IR_MONTHLY_HIST",
    "Agregados monetarios mensual": "DF_MONAGG_MONTHLY_HIST",
}

_NS = {"generic": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic"}


def _fecha(valor: str) -> pd.Timestamp:
    """Periodos SDMX: '20261117', '2026-11-17', '2026-11', '202611', '2026-Q3', '2026'."""
    v = valor.strip()
    if "-Q" in v:
        return pd.Period(v.replace("-", ""), freq="Q").to_timestamp()
    if v.isdigit() and len(v) == 6:
        return pd.Timestamp(year=int(v[:4]), month=int(v[4:]), day=1)
    if v.isdigit() and len(v) == 4:
        return pd.Timestamp(year=int(v), month=1, day=1)
    return pd.to_datetime(v)


def parsear_sdmx(xml: bytes) -> pd.DataFrame:
    """Convierte un mensaje GenericData en tabla: fecha, valor + dimensiones de la serie."""
    raiz = ET.fromstring(xml)
    filas = []
    for serie in raiz.iter(f"{{{_NS['generic']}}}Series"):
        dims = {
            v.get("id").lower(): v.get("value")
            for v in serie.findall("generic:SeriesKey/generic:Value", _NS)
        }
        for obs in serie.findall("generic:Obs", _NS):
            periodo = obs.find("generic:ObsDimension", _NS).get("value")
            valor = obs.find("generic:ObsValue", _NS)
            filas.append(
                {
                    "fecha": _fecha(periodo),
                    "valor": float(valor.get("value")) if valor is not None else None,
                    **dims,
                }
            )
    df = pd.DataFrame(filas)
    if df.empty:
        return pd.DataFrame(columns=["fecha", "valor"])
    # Quitar dimensiones que no cambian en toda la tabla (ruido)
    constantes = [c for c in df.columns if c not in ("fecha", "valor") and df[c].nunique() <= 1]
    return df.drop(columns=constantes).sort_values("fecha").reset_index(drop=True)


def serie(
    dataflow: str,
    inicio: date | str | None = None,
    fin: date | str | None = None,
    max_edad: timedelta = timedelta(hours=12),
) -> tuple[pd.DataFrame, cache.Procedencia]:
    """Descarga un dataflow (id de SERIES o su nombre legible) con caché local."""
    dataflow = SERIES.get(dataflow, dataflow)
    # El servidor filtra por año y responde 404 si endPeriod cae en el mismo año
    # que startPeriod: se piden años completos (fin = 1 de enero del año siguiente)
    params = {}
    if inicio:
        params["startPeriod"] = f"{pd.Timestamp(inicio).year}-01-01"
    if fin:
        params["endPeriod"] = f"{pd.Timestamp(fin).year + 1}-01-01"
    url = f"{BASE}/data/ESTAT,{dataflow},1.0/all/ALL/"

    def descargar():
        r = red.get(url, params=params, headers={"Accept": "application/xml"})
        df = parsear_sdmx(r.content)
        # El servidor solo respeta el año de startPeriod/endPeriod: se recorta aquí
        if inicio:
            df = df[df["fecha"] >= pd.Timestamp(inicio)]
        if fin:
            df = df[df["fecha"] <= pd.Timestamp(fin)]
        nombre = next((k for k, v in SERIES.items() if v == dataflow), dataflow)
        return df.reset_index(drop=True), r.url, f"{nombre} (Banco de la República, SDMX)"

    return cache.obtener(cache.clave_segura("banrep", dataflow, inicio, fin), descargar, max_edad)
