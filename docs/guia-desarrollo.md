# Guía de desarrollo

## Entorno (Windows)
```bash
python -m venv .venv
source .venv/Scripts/activate        # Git Bash   |  .venv\Scripts\activate en PowerShell/cmd
pip install -e ".[dev]"
```

## Comandos
| Acción | Comando |
|---|---|
| Pruebas (sin internet) | `pytest` |
| Pruebas contra APIs reales | `pytest -m red` |
| Abrir la app | `streamlit run app/Inicio.py` → http://localhost:8501 |
| Borrar caché | eliminar `datos/cache/` |

## Uso desde Python (sin la app)
```python
from lokbi.ingesta import socrata, banrep, dane

ipc, fuente = dane.ipc()
trm, fuente = banrep.serie("TRM diaria", inicio="2024-01-01", fin="2024-12-31")
contratos, fuente = socrata.consultar(
    "jbjy-vk9h",
    where="fecha_de_firma >= '2025-01-01' AND departamento = 'Antioquia'",
    limite=50_000,
)
print(fuente.texto())
```

## Agregar un conector nuevo
1. Crear `lokbi/ingesta/<fuente>.py` con una función que devuelva `(DataFrame, Procedencia)`
   usando `cache.obtener(clave, descargar, max_edad)` y `red.get(...)`.
2. Pruebas simuladas en `tests/test_conectores.py` (reemplazar `red.get` con `monkeypatch`).
3. Una prueba real en `tests/test_red_real.py` que compare con una cifra oficial conocida.
4. Documentar en `docs/fuentes.md` URL, formato, peculiaridades y verificación.
5. Agregar pestaña en `app/pages/1_Cargar_datos.py`.
6. Anotar la decisión en `docs/bitacora.md`.

## Convenciones
- Código, comentarios y documentación en español.
- Todo dato externo viaja con su `Procedencia`.
- Antes de un commit: `pytest` en verde.
