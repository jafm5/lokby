# Fuentes de datos

Comportamiento **verificado** de cada fuente (no solo lo que dice su documentación).
Si una fuente cambia, `pytest -m red` debería fallar: actualizar este archivo y el conector.

---

## datos.gov.co (Socrata)

| | |
|---|---|
| Conector | `lokbi/ingesta/socrata.py` |
| Datos | `https://www.datos.gov.co/resource/{id}.csv` |
| Metadatos | `https://www.datos.gov.co/api/views/{id}.json` |
| Catálogo (búsqueda) | `https://api.us.socrata.com/api/catalog/v1?domains=www.datos.gov.co&q=...` |
| Formato | CSV (se prefiere a JSON porque pandas infiere tipos numéricos) |
| Límites | 50.000 filas por petición → el conector pagina con `$offset`. Sin token hay límite de peticiones; opcional `SOCRATA_APP_TOKEN` |
| Consultas | SoQL: `$select`, `$where`, `$order`, `$group`. https://dev.socrata.com/docs/queries/ |

**Datasets verificados**

| Id | Contenido | Publica |
|---|---|---|
| `32sa-8pi3` | TRM diaria | Superintendencia Financiera |
| `jbjy-vk9h` | SECOP II — Contratos electrónicos | Colombia Compra Eficiente |
| `p6dx-8zbt` | SECOP II — Procesos de contratación | Colombia Compra Eficiente |
| `mtic-nvgq` | UVR | Banco de la República (desactualizado: feb-2026) |

**Observaciones**
- La paginación usa `$order=:id` por defecto para que las páginas sean estables.
- No hay IPC nacional actualizado en datos.gov.co (solo series de Cali hasta 2016).
- SECOP tiene millones de filas: filtrar siempre con `$where` antes de descargar.

---

## Banco de la República (SDMX)

| | |
|---|---|
| Conector | `lokbi/ingesta/banrep.py` |
| Base | `https://totoro.banrep.gov.co/nsi-jax-ws/rest/` |
| Lista de series | `.../dataflow/ESTAT/all/latest` |
| Datos | `.../data/ESTAT,{DATAFLOW},1.0/all/ALL/?startPeriod=...&endPeriod=...` |
| Formato | **Solo XML** (SDMX-ML 2.1 GenericData). `Accept: application/xml`. JSON → 406, CSV → 501 |

**Peculiaridades encontradas (nov-2026)**
1. `startPeriod`/`endPeriod` solo filtran por **año**: pedir desde 2026-11-01 devuelve todo 2026.
2. Si `endPeriod` cae en el **mismo año** que `startPeriod` → **404**. Ej.: `2024-01-01` a `2024-12-31` falla; `2024-01-01` a `2025-01-01` funciona.
3. Solución del conector: pedir años completos (`fin` = 1 de enero del año siguiente) y recortar localmente.
4. **No publica el IPC.** Series disponibles: TRM, tasa de política monetaria, IBR, DTF, UVR, COLCAP, TES, tasas de interés, agregados monetarios (ver `banrep.SERIES`).
5. La TRM incluye fechas futuras de fin de semana/festivos (vigencia ya fijada).

**Verificación**: TRM promedio 2024 = 4.071,35 COP sobre 366 días.

---

## DANE

| | |
|---|---|
| Conector | `lokbi/ingesta/dane.py` |
| API | **No tiene**. Publica anexos Excel por operación estadística |
| IPC (índices) | `https://www.dane.gov.co/files/operaciones/IPC/{mes}{año}/anex-IPC-Indices-{mes}{año}.xlsx` |
| Meses | `ene feb mar abr may jun jul ago sep oct nov dic` |

**Estructura del anexo de índices**
- Una hoja (`IndicesIPC`), ~7 filas de títulos antes de la tabla.
- Tabla ancha: fila `Mes` con años 2003…actual como encabezado; filas Enero…Diciembre.
- Base: diciembre de 2018 = 100. Notas y "Fuente: DANE." al final.
- El IPC de un mes se publica a inicios del mes siguiente → el conector prueba el mes actual y retrocede hasta 4 meses.

**Verificación contra cifras oficiales**
| Año | Índice dic | Inflación anual calculada | Oficial |
|---|---|---|---|
| 2023 | 137,72 | 9,28 % | 9,28 % |
| 2024 | 144,88 | 5,20 % | 5,20 % |
| 2025 | 152,27 | 5,10 % | pendiente de contrastar con el boletín |

Otros anexos (empleo GEIH, pobreza, PIB) se pueden cargar por URL con `dane.descargar_excel(url)`; cada uno tendrá su propio parser cuando se use en un análisis.

### Proyecciones de población (CNPV 2018)

| | |
|---|---|
| Función | `dane.poblacion("departamento" \| "municipio")` |
| Departamental | `.../files/censo2018/proyecciones-de-poblacion/Departamental/PPED-AreaDep-2018-2050_VP.xlsx` (1 MB, 2018-2050) |
| Municipal | `.../files/censo2018/proyecciones-de-poblacion/Municipal/PPED-AreaMun-2018-2042_VP.xlsx` (4 MB, 2018-2042, ~25 s en leerse) |
| Estructura | Hojas `Índice`, `PPED` y la de datos (última). ~7 filas de títulos; columnas `DP, DPNOM, [MPIO, DPMP], AÑO, ÁREA GEOGRÁFICA, TOTAL`. Cada territorio-año tiene 3 filas: Cabecera, Centros Poblados y Rural Disperso, **Total** (se usa solo Total) |

**Verificación**: población 2025 = 53.057.212, idéntica sumando departamentos o municipios.
Hay 1.123 códigos municipales en población vs 1.122 en DIVIPOLA.

---

## DIVIPOLA y geografía

| Recurso | Fuente | Notas |
|---|---|---|
| Departamentos | datos.gov.co `vcjz-niiq` (DANE) | 33 (incluye Bogotá D.C.). Latitud/longitud con **coma decimal** |
| Municipios | datos.gov.co `gdxc-w37w` (DANE) | 1.122 con latitud/longitud (coma decimal) |
| Polígonos departamentales | GeoJSON público (gist `john-guerra/Colombia.geo.json`, derivado del MGN del DANE) | Propiedad `DPTO` = código de 2 dígitos. Sus nombres son antiguos ("SANTAFE DE BOGOTA D.C"): por eso **se cruza siempre por código, nunca por nombre** |

**Verificado**: los 33 códigos del GeoJSON coinciden exactamente con DIVIPOLA.

Municipios: no hay polígonos oficiales livianos, se dibujan como **puntos** en su
coordenada DIVIPOLA (tamaño y color según el valor).

### Nombres de departamento en otras fuentes
`geo.codigo_departamento()` normaliza (sin tildes, mayúsculas, sin puntuación) y
usa alias para variantes conocidas. En SECOP II hay 34 valores distintos:
31 coinciden directo, 2 requieren alias ("Distrito Capital de Bogotá",
"San Andrés, Providencia y Santa Catalina") y "No Definido" (~108.000 contratos)
queda sin código **a propósito**: no se le asigna un departamento inventado.

---

## Notas sobre SECOP II (`jbjy-vk9h`)
- Columnas útiles: `nombre_entidad`, `departamento`, `ciudad`, `modalidad_de_contratacion`,
  `fecha_de_firma`, `valor_del_contrato`, `codigo_entidad`.
- Más de 1,8 millones de contratos solo en Bogotá: **agregar en el servidor** con `$group`:
  ```python
  socrata.consultar("jbjy-vk9h",
      select="departamento, date_extract_y(fecha_de_firma) AS anio, sum(valor_del_contrato) AS total, count(*) AS contratos",
      group="departamento, anio", limite=None)
  ```
- Con `$group` no existe la columna interna `:id`; el conector ordena por las columnas agrupadas.

---

## Estadística delictiva — Ministerio de Defensa / Policía Nacional

| | |
|---|---|
| Conector | `lokbi/ingesta/mindefensa.py` |
| Cobertura | 2003 hasta el último mes. Actualización mensual hacia el día 17-21 del mes siguiente (sep-2026 publicado el 2026-10-21; oct-2026 el 2026-11-17) |
| Estructura | Una fila por registro: `fecha_hecho`, `cod_depto`, `departamento`, `cod_muni`, `municipio`, `cantidad` (+ columnas propias de cada delito) |
| Agregación | En el servidor con `$group` (`date_trunc_ym(fecha_hecho)`, `cod_depto`) |

| Delito | Id | Columnas extra |
|---|---|---|
| Homicidio | `m8fd-ahd9` | `zona`, `sexo`, `arma_medio`, `_modalidad_presunta`, `spoa_caracterizacion` (intencional / feminicidio) |
| Hurto a personas | `4rxi-8m8d` | — |
| Extorsión | `q2ib-t9am` | — |
| Secuestro | `d7zw-hpf4` | `tipo_delito` (simple / extorsivo) |
| Hurto a residencias / comercio / vehículos | `7mn7-vzqp` / `7i2x-h5vp` / `csb4-y6v2` | `tipo_delito`, `zona` (vehículos) |
| Violencia intrafamiliar | `gepp-dxcs` | `zona` |
| Delitos sexuales | `bz43-8ahq` | `zona`, `sexo` |

**Peculiaridades verificadas (nov-2026)**
1. **El último mes publicado está incompleto**: sep-2026 traía 966 homicidios (promedio ≈ 1.190) y 630 extorsiones (≈ 1.190) en la publicación de octubre; oct-2026 trae 1.053 homicidios y 687 extorsiones en la de noviembre. Se excluye siempre.
2. **Cambio en el registro de secuestro**: hasta 2024 `cantidad` = 1 en todos los registros; desde 2025 hay registros con varias víctimas (hasta 28). Para comparar en el tiempo se usan **registros** (`count(*)`), no la suma de `cantidad`.
3. **Hurto a personas viene agregado**: ~7 personas por registro, estable 2019-2026, así que es comparable usando `sum(cantidad)`.
4. **Homicidio y extorsión**: `cantidad` ≈ 1 por registro en todos los años.
5. **Posible reclasificación en homicidio (ene-2026)**: "ATACADOS POR GAO O GAO-R" salta de ~66 a ~203 al mes y "SICARIATO" baja de ~780 a ~581; la suma no sube. Ver la historia de seguridad.

## Medicina Legal — presuntos homicidios (`vtub-3de2`)
- Cifras **definitivas** 2015-2024, una fila por víctima (`a_o_del_hecho`, municipio, edad, sexo, mecanismo…).
- Fuente independiente de la Policía para contrastar homicidios. Diferencia con la Policía: entre 3 % y 6 % según el año; hasta 2021 la Policía registraba más, desde 2022 registra menos.
