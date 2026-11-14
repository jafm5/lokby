"""Cliente HTTP compartido por todos los conectores.

Centraliza User-Agent, tiempos de espera y reintentos para que cada conector
no tenga que repetirlos.
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "lokbi/0.1 (analisis de datos abiertos)"
TIMEOUT = 60  # segundos

_sesion: requests.Session | None = None


def sesion() -> requests.Session:
    global _sesion
    if _sesion is None:
        s = requests.Session()
        s.headers["User-Agent"] = USER_AGENT
        reintentos = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
        s.mount("https://", HTTPAdapter(max_retries=reintentos))
        _sesion = s
    return _sesion


def get(url: str, **kwargs) -> requests.Response:
    """GET con timeout y error explícito si el servidor no responde 200."""
    kwargs.setdefault("timeout", TIMEOUT)
    r = sesion().get(url, **kwargs)
    r.raise_for_status()
    return r
