# Arquitectura

## Principio
La lógica (`lokbi/`) no depende de la interfaz (`app/`). Todo lo que hace la web
se puede hacer desde un script o notebook en `analisis/`, lo que permite
reproducir cualquier cifra publicada sin abrir la app.

```
Fuentes                 lokbi/ (lógica)                         app/ (Streamlit)
───────                 ──────────────                          ────────────────
datos.gov.co ─┐
BanRep SDMX ──┼─▶ ingesta/*.py ─▶ cache.py ─▶ DataFrame ─┬─▶ 1_Cargar_datos.py
DANE Excel ───┤        │          (Parquet +            │      ↓ session_state["df"]
Archivo local ┘        └ red.py    procedencia JSON)     └─▶ 2_Explorar.py
                         (HTTP)                               estadistica.py
                                                              consultas.py (DuckDB)
```

## Módulos

| Módulo | Responsabilidad |
|---|---|
| `lokbi/red.py` | Sesión HTTP compartida: User-Agent, timeout 60 s, 3 reintentos ante 429/5xx |
| `lokbi/cache.py` | Guarda cada descarga como Parquet + JSON de procedencia (fuente, descripción, fecha). Reutiliza si es reciente |
| `lokbi/ingesta/archivos.py` | CSV (separador y codificación automáticos), Excel (detecta encabezado), JSON, Parquet |
| `lokbi/ingesta/socrata.py` | datos.gov.co: búsqueda en catálogo, metadatos, consultas SoQL paginadas |
| `lokbi/ingesta/banrep.py` | Banco de la República: parser SDMX-ML, catálogo `SERIES` |
| `lokbi/ingesta/dane.py` | DANE: localización del último anexo del IPC, conversión ancho → largo |
| `lokbi/estadistica.py` | Perfil de columnas, descriptivos, variación porcentual |
| `lokbi/consultas.py` | SQL sobre DataFrames con DuckDB |

## Contrato de los conectores
Toda función que trae datos de una fuente externa devuelve
`(DataFrame, Procedencia)`. La `Procedencia` viaja con la tabla hasta la
interfaz y se muestra junto a los datos. **Ningún dato aparece sin su fuente.**

## Caché
- Ubicación: `datos/cache/` (fuera de Git).
- Vigencia por defecto: Socrata 1 día, BanRep 12 h, DANE 7 días.
- La clave incluye todos los parámetros de la consulta (`cache.clave_segura`).
- Columnas con tipos mezclados se guardan como texto (limitación de Parquet).

## Estado de la interfaz
Las páginas comparten la tabla activa en `st.session_state`:
`df`, `df_nombre`, `df_fuente`.
