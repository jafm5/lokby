# Arquitectura

## Principio
La lógica (`lokbi/`) no depende de la interfaz (`app/`). Todo lo que hace la web
se puede hacer desde un script o notebook en `analisis/`, lo que permite
reproducir cualquier cifra publicada sin abrir la app.

```
Fuentes                 lokbi/ (lógica)                         app/ (Streamlit)
───────                 ──────────────                          ────────────────
datos.gov.co ─┐                                                  estado.py (tabla activa + historial)
BanRep SDMX ──┼─▶ ingesta/*.py ─▶ cache.py ─▶ DataFrame ──▶ 1_Cargar_datos.py
DANE Excel ───┤        │          (Parquet +                   ↓
Archivo local ┘        └ red.py    procedencia JSON)        2_Explorar.py    ← estadistica, consultas
                                                             3_Transformar.py ← limpieza, estadistica, geo, dane
DIVIPOLA, GeoJSON, población ─▶ geo.py / dane.py ─────────▶ 4_Graficar.py    ← graficas, geo
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
| `lokbi/ingesta/dane.py` (población) | Proyecciones de población por departamento y municipio |
| `lokbi/estadistica.py` | Perfil de columnas, descriptivos, agrupar, **pesos constantes** (`deflactar`), **tasa por habitantes**, variación porcentual |
| `lokbi/consultas.py` | SQL sobre DataFrames con DuckDB |
| `lokbi/limpieza.py` | Texto→número (formato colombiano), texto→fecha, códigos DIVIPOLA con cero inicial, normalizar nombres |
| `lokbi/geo.py` | DIVIPOLA departamentos/municipios, GeoJSON, nombre de departamento → código (con alias) |
| `lokbi/graficas.py` | Barras, líneas, dispersión, mapa por departamento (coroplético), mapa por municipio (puntos). Paleta fija y fuente en la imagen |
| `lokbi/ingesta/mindefensa.py` | Delitos de la Policía Nacional agregados en el servidor; homicidios de Medicina Legal |
| `lokbi/analisis/seguridad.py` | Cálculos de la historia de seguridad: periodos, totales, tasas, contraste de fuentes |
| `analisis/*.py` | Scripts que generan los datos de cada historia en `datos/historias/<tema>/` (versionados en Git) |
| `app/pages/5_Historias.py` | Historia publicada: lee solo los CSV de `datos/historias/` (y el mapa), sin consultar las fuentes |
| `app/estado.py` | Tabla activa, fuente, historial de pasos (deshacer), avisos que sobreviven a `st.rerun()` |

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
Las páginas comparten la tabla activa en `st.session_state` a través de
`app/estado.py`: `df`, `df_nombre`, `df_fuente` e `historial`.

Cada transformación llama a `estado.aplicar(df_nuevo, "descripción")`, que
guarda la tabla anterior (para **deshacer**) y la descripción del paso. Los pasos
se muestran en todas las páginas y se imprimen al pie de cada gráfica junto con
la fuente. Cargar una tabla nueva reinicia el historial.

## Gráficas
- Plotly con `theme=None` en Streamlit: la gráfica siempre tiene fondo claro,
  igual en pantalla que en la imagen descargada (los colores son de la paleta clara).
- Descarga de imagen: botón de cámara de Plotly (PNG a escala 2).
