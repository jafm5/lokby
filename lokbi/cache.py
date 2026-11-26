"""Caché local en Parquet con metadatos de procedencia.

Cada descarga se guarda como `<clave>.parquet` junto a `<clave>.json` con la
fuente (URL), la fecha de descarga y una descripción. Así:
- no se golpean las APIs en cada recarga de la app;
- toda tabla conserva de dónde salió y cuándo, requisito para que el
  análisis sea verificable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

# Carpeta preferida: datos/cache del proyecto. Se puede cambiar con la variable
# de entorno LOKBI_CACHE_DIR. Si no se puede escribir (por ejemplo, en un
# servidor donde el paquete quedó instalado en una carpeta de solo lectura),
# se usa una carpeta temporal del sistema.
DIRECTORIO = Path(os.environ.get("LOKBI_CACHE_DIR") or Path(__file__).resolve().parent.parent / "datos" / "cache")
_TEMPORAL = Path(tempfile.gettempdir()) / "lokbi-cache"
_escribibles: dict[Path, bool] = {}
_log = logging.getLogger(__name__)


def _se_puede_escribir(carpeta: Path) -> bool:
    if carpeta not in _escribibles:
        try:
            carpeta.mkdir(parents=True, exist_ok=True)
            prueba = carpeta / ".prueba_escritura"
            prueba.write_text("ok", encoding="utf-8")
            prueba.unlink()
            _escribibles[carpeta] = True
        except OSError:
            _escribibles[carpeta] = False
    return _escribibles[carpeta]


def directorio_cache() -> Path:
    """La carpeta de caché a usar: la preferida si se puede escribir, si no la temporal."""
    return DIRECTORIO if _se_puede_escribir(DIRECTORIO) else _TEMPORAL


@dataclass
class Procedencia:
    fuente: str  # URL o identificador oficial
    descripcion: str
    descargado: str  # ISO 8601

    def texto(self) -> str:
        fecha = self.descargado[:16].replace("T", " ")
        return f"{self.descripcion} — {self.fuente} (descargado {fecha})"


def clave_segura(*partes: object) -> str:
    """Nombre de archivo legible y único a partir de los parámetros de la consulta."""
    base = "_".join(str(p) for p in partes if p not in (None, ""))
    legible = re.sub(r"[^a-zA-Z0-9]+", "-", base)[:60].strip("-")
    huella = hashlib.sha1(base.encode()).hexdigest()[:8]
    return f"{legible}-{huella}"


def obtener(
    clave: str,
    descargar: Callable[[], tuple[pd.DataFrame, str, str]],
    max_edad: timedelta = timedelta(days=1),
    directorio: Path | None = None,
) -> tuple[pd.DataFrame, Procedencia]:
    """Devuelve la tabla desde caché si es reciente; si no, la descarga y guarda.

    `descargar` devuelve (df, fuente, descripcion).
    """
    directorio = directorio or directorio_cache()
    archivo = directorio / f"{clave}.parquet"
    meta = directorio / f"{clave}.json"

    try:
        if archivo.exists() and meta.exists():
            proc = Procedencia(**json.loads(meta.read_text(encoding="utf-8")))
            if datetime.now() - datetime.fromisoformat(proc.descargado) < max_edad:
                return pd.read_parquet(archivo), proc
    except (OSError, ValueError, TypeError) as e:  # caché dañada o ilegible: se descarga de nuevo
        _log.warning("No se pudo leer la caché %s: %s", clave, e)

    df, fuente, descripcion = descargar()
    proc = Procedencia(fuente=fuente, descripcion=descripcion, descargado=datetime.now().isoformat(timespec="seconds"))
    try:
        directorio.mkdir(parents=True, exist_ok=True)
        # Parquet no admite columnas con tipos mezclados: se normalizan a texto
        seguro = df.copy()
        for col in seguro.columns[seguro.dtypes == object]:
            seguro[col] = seguro[col].astype("string")
        seguro.to_parquet(archivo, index=False)
        meta.write_text(json.dumps(asdict(proc), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        # La caché solo acelera; si no se puede guardar, los datos se devuelven igual
        _log.warning("No se pudo guardar la caché %s: %s", clave, e)
    return df, proc
