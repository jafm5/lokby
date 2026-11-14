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

### Ejemplo completo: contratación por departamento, en pesos de 2025 y por habitante
```python
from lokbi import geo, graficas
from lokbi.estadistica import deflactar, tasa_por_habitantes
from lokbi.ingesta import dane, socrata
from lokbi.limpieza import a_fecha, a_numero

df, fuente = socrata.consultar("jbjy-vk9h",
    select="departamento, fecha_de_firma, valor_del_contrato",
    where="fecha_de_firma >= '2024-01-01' AND fecha_de_firma < '2025-01-01'", limite=50_000)
df["valor"] = a_numero(df["valor_del_contrato"])
df["fecha"] = a_fecha(df["fecha_de_firma"])

ipc, _ = dane.ipc()
df["valor_2025"] = deflactar(df["valor"], df["fecha"], ipc, "2025")   # deflactar ANTES de agrupar
df["cod_dpto"] = geo.codigo_departamento(df["departamento"])

por_dpto = df.groupby("cod_dpto", as_index=False)["valor_2025"].sum()
pob, _ = dane.poblacion("departamento")
por_dpto = por_dpto.merge(pob[pob.anio == 2024][["codigo", "poblacion"]], left_on="cod_dpto", right_on="codigo")
por_dpto["por_habitante"] = tasa_por_habitantes(por_dpto["valor_2025"], por_dpto["poblacion"], por=1)

geojson, _ = geo.geojson_departamentos()
fig = graficas.mapa_departamentos(por_dpto, "cod_dpto", "por_habitante", geojson,
                                  titulo="Contratación por habitante, 2024 (pesos de 2025)",
                                  fuente=fuente.texto())
fig.show()
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
