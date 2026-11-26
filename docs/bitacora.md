# Bitácora del proyecto

Registro de decisiones y avances, del más reciente al más antiguo.

---

## 2026-11-25 — Actualización de la historia de seguridad (datos hasta oct-2026) y publicación

**Publicada** en Streamlit Community Cloud: https://sobaeuehf6p4rx8tdmrz5r.streamlit.app/
(se actualiza sola con cada `git push` a `main`).

**Hecho**
- La Policía publicó datos hasta octubre de 2026 (actualización del 17-nov). Se regeneró
  `datos/historias/seguridad/` con `analisis/seguridad_2026.py`.
- Corte: sep-2026 (octubre se excluye por incompleto: 687 extorsiones frente a un promedio de 1.198;
  1.053 homicidios frente a 1.171). Periodos: oct-2023→sep-2024, oct-2024→sep-2025, oct-2025→sep-2026.
- La frase "es el cambio más grande de los cuatro delitos" ahora se muestra solo si los datos lo confirman.

**Cifras nuevas (último año vs. año anterior)**
- Homicidio −0,1 % (14.053; 26,3 por 100.000 hab.); +4,9 % frente a dos años antes.
- Hurto a personas −8,6 %; extorsión +5,3 %.
- Secuestro (hechos registrados) 296 → 528 → 475: baja 10 % frente al año anterior, pero sube 60 % en dos años.
  El año anterior ahora incluye septiembre de 2025, con hechos masivos en Cauca (107 víctimas en 8 registros).

**Revisado**: el salto GAO/sicariato de enero de 2026 se mantiene (la suma no sube); el cruce Policía vs.
Medicina Legal (2021/2022) se mantiene; el aumento del secuestro en dos años no depende de hechos masivos.

---

## 2026-11-14 — Fase 4: primera historia (seguridad)

**Hecho**
- Código publicado en GitHub: https://github.com/jafm5/lokby (commits con el correo privado de GitHub).
- Conector `mindefensa.py` (9 delitos de la Policía Nacional + homicidios de Medicina Legal).
- Cálculos en `lokbi/analisis/seguridad.py` (con pruebas) y script `analisis/seguridad_2026.py`,
  que genera las tablas en `datos/historias/seguridad/`.
- Página **5_Historias**: "Seguridad en Colombia: ¿qué pasó en los últimos dos años?".
- Tema claro fijo (`.streamlit/config.toml`) y `requirements.txt` para Streamlit Community Cloud.

**Hallazgos (sep-2025 a ago-2026 frente a sep-2024 a ago-2025)**
- Homicidio +1,8 % (14.248; 26,7 por 100.000 hab.); +6,3 % frente a dos años antes.
- Hurto a personas −5,7 %; extorsión +4,7 %; secuestro (hechos registrados) 297 → 481 → 493.
- Posible reclasificación de homicidios de "sicariato" a "atacados por GAO" desde enero de 2026.

**Decisiones**
- *Excluir el último mes publicado*: estaba incompleto en todos los delitos y habría mostrado una caída falsa.
- *Comparar secuestros por registros*: desde 2025 un registro puede tener varias víctimas.
- *No atribuir causas*: la historia dice explícitamente lo que los datos no permiten concluir.
- *Corregidas dos frases que exageraban* antes de publicar: la suma GAO + sicariato sí baja un poco, y
  Policía y Medicina Legal no siempre se mueven igual año a año.

**Pendiente**
- Desplegar en Streamlit Community Cloud (requiere que el usuario inicie sesión con GitHub).
- Contrastar el hurto con la Encuesta de Convivencia y Seguridad Ciudadana (DANE), que mide delitos no denunciados.

---

## 2026-11-13 — Fase 3: transformación, gráficas y mapas

**Hecho**
- Página **Transformar**: texto→número (formato colombiano), texto→fecha, filtrar (SQL),
  agrupar, **pesos constantes** con IPC, código DIVIPOLA desde nombre de departamento,
  **población y tasa por 100.000 habitantes**. Cada paso queda registrado y se puede deshacer.
- Página **Graficar**: barras, líneas (agrupando fechas por día/mes/trimestre/año),
  dispersión, mapa coroplético por departamento y mapa de puntos por municipio.
  Fuente y pasos impresos dentro de la imagen; datos de la gráfica descargables.
- Nuevos módulos: `limpieza.py`, `geo.py`, `graficas.py`, `app/estado.py`;
  `dane.poblacion()`; `$group` en el conector de datos.gov.co.
- Pruebas: 47 sin internet + 5 contra fuentes reales.

**Decisiones**
- *Cruce geográfico por código DIVIPOLA, nunca por nombre*: los nombres varían entre
  fuentes ("Distrito Capital de Bogotá", "BOGOTÁ, D.C.", "SANTAFE DE BOGOTA D.C").
- *Municipios como puntos y no polígonos*: no hay un GeoJSON municipal oficial liviano;
  las coordenadas DIVIPOLA son oficiales.
- *Paleta fija validada para daltonismo* y un solo eje Y (ver `metodologia.md`).
- *`theme=None` en las gráficas*: misma apariencia en pantalla y en la imagen descargada.
- *Avisos persistentes* (`estado.aviso`): los mensajes se perdían al recargar la página.

**Problemas encontrados y resueltos**
- SECOP usa "Distrito Capital de Bogotá" y "San Andrés, Providencia y Santa Catalina",
  que no coincidían con DIVIPOLA → alias. "No Definido" se deja sin código a propósito.
- DIVIPOLA publica latitud/longitud con coma decimal → `a_numero(decimal=",")`.
- El mapa excluía en silencio filas sin departamento → ahora avisa cuántas.

**Pendiente**
- Revisión visual de las gráficas: se verificó que se generan sin errores, pero no se
  inspeccionaron como imagen (no se instaló `kaleido` para exportarlas desde las pruebas).

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
