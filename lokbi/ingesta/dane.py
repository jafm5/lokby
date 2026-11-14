"""Conector al DANE.

El DANE no tiene API de datos: publica anexos Excel cuya URL cambia cada mes
con un patrón estable. Para el IPC:
    https://www.dane.gov.co/files/operaciones/IPC/{mes}{año}/anex-IPC-Indices-{mes}{año}.xlsx
    mes = ene, feb, mar, abr, may, jun, jul, ago, sep, oct, nov, dic

El anexo de índices es una tabla ancha: filas = meses (Enero..Diciembre),
columnas = años (2003..actual), base diciembre de 2018 = 100.
"""

from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
import requests

from lokbi import cache, red

BASE = "https://www.dane.gov.co/files/operaciones"
MESES_ABREV = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def url_ipc_indices(anio: int, mes: int) -> str:
    m = f"{MESES_ABREV[mes - 1]}{anio}"
    return f"{BASE}/IPC/{m}/anex-IPC-Indices-{m}.xlsx"


def parsear_ipc_indices(contenido: bytes) -> pd.DataFrame:
    """Convierte el anexo ancho en tabla larga: fecha, indice (base dic-2018 = 100)."""
    crudo = pd.read_excel(io.BytesIO(contenido), header=None)
    primera = crudo.iloc[:, 0].astype(str).str.strip().str.lower()
    filas_mes = primera[primera == "mes"].index
    if filas_mes.empty:
        raise ValueError("No se encontró la fila 'Mes' en el anexo del IPC; ¿cambió el formato?")
    i = filas_mes[0]
    anios = [int(float(a)) if pd.notna(a) else None for a in crudo.iloc[i, 1:]]

    filas = []
    for _, fila in crudo.iloc[i + 1 : i + 13].iterrows():
        nombre_mes = str(fila.iloc[0]).strip().lower()
        if nombre_mes not in MESES:
            continue
        mes = MESES.index(nombre_mes) + 1
        for anio, valor in zip(anios, fila.iloc[1:]):
            if anio is not None and pd.notna(valor):
                filas.append({"fecha": pd.Timestamp(year=anio, month=mes, day=1), "indice": float(valor)})
    return pd.DataFrame(filas).sort_values("fecha").reset_index(drop=True)


def _ultimo_anexo_disponible(hoy: date, intentos: int = 4) -> tuple[bytes, str]:
    """El DANE publica el IPC de un mes a inicios del siguiente: se prueba hacia atrás."""
    anio, mes = hoy.year, hoy.month
    ultimo_error: Exception | None = None
    for _ in range(intentos):
        url = url_ipc_indices(anio, mes)
        try:
            return red.get(url).content, url
        except requests.HTTPError as e:
            ultimo_error = e
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    raise RuntimeError(f"No se encontró un anexo del IPC en los últimos {intentos} meses") from ultimo_error


def ipc(max_edad: timedelta = timedelta(days=7), hoy: date | None = None) -> tuple[pd.DataFrame, cache.Procedencia]:
    """Serie mensual del IPC total nacional (índice y variaciones), con caché local.

    Columnas: fecha, indice, var_mensual_pct, var_anual_pct, var_año_corrido_pct
    """

    def descargar():
        contenido, url = _ultimo_anexo_disponible(hoy or date.today())
        df = parsear_ipc_indices(contenido)
        df["var_mensual_pct"] = df["indice"].pct_change() * 100
        df["var_anual_pct"] = df["indice"].pct_change(12) * 100
        dic_anterior = df.set_index("fecha")["indice"]
        base = df["fecha"].map(lambda f: dic_anterior.get(pd.Timestamp(year=f.year - 1, month=12, day=1)))
        df["var_año_corrido_pct"] = (df["indice"] / base - 1) * 100
        return df, url, "IPC total nacional, índice base dic-2018=100 (DANE)"

    return cache.obtener("dane-ipc-indices", descargar, max_edad)


def descargar_excel(url: str, max_edad: timedelta = timedelta(days=7)) -> tuple[pd.DataFrame, cache.Procedencia]:
    """Cualquier anexo Excel del DANE (u otra URL) leído con el detector de encabezados."""
    from lokbi.ingesta.archivos import leer_excel

    def descargar():
        return leer_excel(red.get(url).content), url, "Anexo descargado (DANE)"

    return cache.obtener(cache.clave_segura("excel", url), descargar, max_edad)
