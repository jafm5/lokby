"""Conector a datos.gov.co (plataforma Socrata).

Cada dataset tiene un identificador de 9 caracteres (ej. `32sa-8pi3` = TRM),
visible en la URL del dataset. Las consultas usan SoQL, un SQL simplificado:
    $select, $where, $order, $group, $limit, $offset
Documentación: https://dev.socrata.com/docs/queries/

Sin token de aplicación hay límite de peticiones; para uso intensivo se puede
crear uno gratis en datos.gov.co y ponerlo en la variable SOCRATA_APP_TOKEN.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from lokbi import cache, red

DOMINIO = "https://www.datos.gov.co"
CATALOGO = "https://api.us.socrata.com/api/catalog/v1"
TAMANO_PAGINA = 50_000  # máximo recomendado por Socrata

# Datasets útiles verificados, para tenerlos a mano
CONOCIDOS = {
    "32sa-8pi3": "TRM - Tasa de Cambio Representativa del Mercado (Superfinanciera)",
    "jbjy-vk9h": "SECOP II - Contratos electrónicos",
    "p6dx-8zbt": "SECOP II - Procesos de contratación",
    "mtic-nvgq": "UVR - Unidad de Valor Real (Banco de la República)",
}


@dataclass
class InfoDataset:
    id: str
    nombre: str
    entidad: str
    descripcion: str
    actualizado: str
    url: str


def _cabeceras() -> dict:
    token = os.environ.get("SOCRATA_APP_TOKEN")
    return {"X-App-Token": token} if token else {}


def info(dataset_id: str) -> InfoDataset:
    """Metadatos del dataset: nombre, entidad que lo publica, fecha de actualización."""
    m = red.get(f"{DOMINIO}/api/views/{dataset_id}.json", headers=_cabeceras()).json()
    actualizado = m.get("rowsUpdatedAt") or m.get("viewLastModified")
    return InfoDataset(
        id=dataset_id,
        nombre=m.get("name", ""),
        entidad=m.get("attribution") or "",
        descripcion=(m.get("description") or "").strip(),
        actualizado=pd.to_datetime(actualizado, unit="s").strftime("%Y-%m-%d") if actualizado else "",
        url=f"{DOMINIO}/d/{dataset_id}",
    )


def buscar(texto: str, limite: int = 20) -> pd.DataFrame:
    """Busca datasets en el catálogo de datos.gov.co."""
    r = red.get(
        CATALOGO,
        params={"domains": "www.datos.gov.co", "q": texto, "limit": limite, "only": "dataset"},
    ).json()
    filas = [
        {
            "id": x["resource"]["id"],
            "nombre": x["resource"]["name"],
            "entidad": x["resource"].get("attribution") or "",
            "actualizado": (x["resource"].get("data_updated_at") or "")[:10],
        }
        for x in r.get("results", [])
    ]
    return pd.DataFrame(filas, columns=["id", "nombre", "entidad", "actualizado"])


def _descargar(dataset_id: str, select, where, order, limite, group=None) -> pd.DataFrame:
    url = f"{DOMINIO}/resource/{dataset_id}.csv"
    paginas = []
    offset = 0
    while True:
        tam = TAMANO_PAGINA if limite is None else min(TAMANO_PAGINA, limite - offset)
        if tam <= 0:
            break
        # Con $group no existe :id; se ordena por las columnas agrupadas
        params = {"$limit": tam, "$offset": offset, "$order": order or group or ":id"}
        if select:
            params["$select"] = select
        if where:
            params["$where"] = where
        if group:
            params["$group"] = group
        texto = red.get(url, params=params, headers=_cabeceras()).content.decode("utf-8")
        pagina = pd.read_csv(io.StringIO(texto))
        paginas.append(pagina)
        offset += len(pagina)
        if len(pagina) < tam:
            break
    return pd.concat(paginas, ignore_index=True) if paginas else pd.DataFrame()


def consultar(
    dataset_id: str,
    select: str | None = None,
    where: str | None = None,
    order: str | None = None,
    limite: int | None = 10_000,
    max_edad: timedelta = timedelta(days=1),
    group: str | None = None,
) -> tuple[pd.DataFrame, cache.Procedencia]:
    """Descarga filas de un dataset (paginando) con caché local.

    Ejemplo: contratos de una entidad en 2024
        consultar("jbjy-vk9h",
                  where="nombre_entidad like '%MINISTERIO%' AND fecha_de_firma >= '2024-01-01'",
                  limite=None)
    `limite=None` trae todo (cuidado: SECOP tiene millones de filas).

    Agregar en el servidor (mucho más rápido que descargar todo):
        consultar("jbjy-vk9h",
                  select="departamento, date_extract_y(fecha_de_firma) AS anio, sum(valor_del_contrato) AS total",
                  group="departamento, anio", limite=None)
    """

    def descargar():
        df = _descargar(dataset_id, select, where, order, limite, group)
        meta = info(dataset_id)
        filtro = f" · filtro: {where}" if where else ""
        if group:
            filtro += f" · agrupado por: {group}"
        return df, meta.url, f"{meta.nombre} ({meta.entidad}){filtro}"

    clave = cache.clave_segura("socrata", dataset_id, select, where, order, limite, group)
    return cache.obtener(clave, descargar, max_edad)
