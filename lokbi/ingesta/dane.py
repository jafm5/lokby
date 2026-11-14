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


URL_POBLACION = {
    "departamento": f"{BASE.replace('/operaciones', '')}/censo2018/proyecciones-de-poblacion/Departamental/PPED-AreaDep-2018-2050_VP.xlsx",
    "municipio": f"{BASE.replace('/operaciones', '')}/censo2018/proyecciones-de-poblacion/Municipal/PPED-AreaMun-2018-2042_VP.xlsx",
}


def parsear_poblacion(contenido: bytes, nivel: str) -> pd.DataFrame:
    """Proyecciones de población (CNPV 2018) -> codigo, nombre, anio, poblacion (área Total).

    El libro tiene hojas 'Índice', 'PPED' y la de datos (la última); la tabla
    empieza tras ~7 filas de títulos con columnas DP, DPNOM, [MPIO, DPMP], AÑO,
    ÁREA GEOGRÁFICA, TOTAL. Cada territorio-año trae filas Cabecera, Centros
    Poblados y Total.
    """
    from lokbi.ingesta.archivos import leer_excel
    from lokbi.limpieza import codigo_divipola, normalizar_texto

    hojas = pd.ExcelFile(io.BytesIO(contenido)).sheet_names
    df = leer_excel(contenido, hoja=hojas[-1])
    df.columns = [normalizar_texto(c) for c in df.columns]
    area = next(c for c in df.columns if c.startswith("AREA"))
    df = df[df[area].astype(str).str.strip().str.lower() == "total"]
    if nivel == "municipio":
        codigo, nombre, digitos = "MPIO", "DPMP", 5
    else:
        codigo, nombre, digitos = "DP", "DPNOM", 2
    salida = pd.DataFrame(
        {
            "codigo": codigo_divipola(df[codigo], digitos),
            "nombre": df[nombre].astype(str).str.strip(),
            "anio": pd.to_numeric(df["ANO"], errors="coerce").astype("Int64"),
            "poblacion": pd.to_numeric(df["TOTAL"], errors="coerce"),
        }
    )
    if nivel == "municipio":
        salida.insert(1, "codigo_departamento", salida["codigo"].str[:2])
    return salida.dropna(subset=["codigo", "anio"]).reset_index(drop=True)


def poblacion(nivel: str = "departamento", max_edad: timedelta = timedelta(days=90)) -> tuple[pd.DataFrame, cache.Procedencia]:
    """Proyecciones de población del DANE por departamento (2018-2050) o municipio (2018-2042)."""
    if nivel not in URL_POBLACION:
        raise ValueError("nivel debe ser 'departamento' o 'municipio'")
    url = URL_POBLACION[nivel]

    def descargar():
        return parsear_poblacion(red.get(url).content, nivel), url, f"Proyecciones de población por {nivel}, CNPV 2018 (DANE)"

    return cache.obtener(f"dane-poblacion-{nivel}", descargar, max_edad)


def descargar_excel(url: str, max_edad: timedelta = timedelta(days=7)) -> tuple[pd.DataFrame, cache.Procedencia]:
    """Cualquier anexo Excel del DANE (u otra URL) leído con el detector de encabezados."""
    from lokbi.ingesta.archivos import leer_excel

    def descargar():
        return leer_excel(red.get(url).content), url, "Anexo descargado (DANE)"

    return cache.obtener(cache.clave_segura("excel", url), descargar, max_edad)
