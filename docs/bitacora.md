# Bitácora del proyecto

Registro de decisiones y avances, del más reciente al más antiguo.

---

## 2026-11-13 — Fase 2: fuentes oficiales

**Hecho**
- Conectores a datos.gov.co, Banco de la República y DANE (IPC), con caché local
  en Parquet y registro de procedencia.
- Página "Cargar datos" con pestañas por fuente; búsqueda en el catálogo de datos.gov.co.
- Consultas SQL con DuckDB en "Explorar", con descarga del resultado en CSV.
- Pruebas: 24 sin internet (respuestas simuladas) + 3 contra APIs reales (`pytest -m red`).

**Decisiones**
- *IPC desde el DANE y no desde el Banco de la República*: la API SDMX del Banco
  no publica el IPC, y datos.gov.co no tiene la serie nacional actualizada.
- *Socrata en CSV y no en JSON*: el JSON entrega todo como texto; con CSV pandas
  reconoce números directamente.
- *Pruebas simuladas por defecto*: no dependen de internet ni de que las fuentes
  estén arriba; las pruebas de red detectan cambios de formato.

**Problemas encontrados y resueltos**
- El detector de encabezados de Excel exigía texto; el anexo del IPC usa años
  numéricos como encabezado. Ahora basta con que la fila esté llena al menos a la mitad.
- BanRep ignora día y mes en los filtros de fecha y responde 404 si el rango
  cae dentro de un mismo año. Se piden años completos y se recorta localmente.

**Verificado**: inflación 2023 (9,28 %) y 2024 (5,20 %) coinciden
con las cifras oficiales del DANE (2025 calculada: 5,10 %, pendiente de contrastar). TRM promedio 2024: 4.071,35 COP.

---

## 2026-11-13 — Fase 1: fundamentos

**Hecho**
- Esqueleto del proyecto, repositorio Git (rama `main`).
- Lectura multiformato: CSV (`,` `;` tab, UTF-8/cp1252/latin-1), Excel con
  títulos arriba, JSON (lista o envuelto en `data`), Parquet.
- Páginas Inicio, Cargar datos y Explorar (perfil de columnas, descriptivos, histograma).

**Decisiones**
- *App propia en Python en vez de Power BI o Looker Studio*: aprendizaje,
  transparencia (código público, verificable) y costo cero. Power BI exige
  cuenta de trabajo para publicar en la web; Looker Studio es limitado para
  transformar datos. Ambos quedan como opción para practicar con los datos limpios.
- *Streamlit* para la web: interfaz en Python puro, publicación gratuita en
  Streamlit Community Cloud.
- *venv + pip en vez de uv*: uv no estaba instalado; Python 3.10 disponible.
