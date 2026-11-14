# Metodología

El objetivo del proyecto es que cualquier persona pueda **verificar** cada cifra.
Estas reglas aplican a todo análisis publicado.

## Reglas
1. **Fuente oficial enlazada** y fecha de descarga en cada tabla y gráfica.
2. **Código público**: limpieza y cálculos en el repositorio, reproducibles.
3. **Limitaciones explícitas**: qué no permite concluir el dato.
4. **Contrastar antes de publicar**: comparar al menos una cifra con la publicada
   oficialmente (ver tablas de verificación en `fuentes.md`).
5. **Evitar el sesgo propio**: formular la pregunta antes de mirar los datos y
   reportar el resultado aunque no confirme la hipótesis inicial.
6. **Comparaciones justas**: montos de distintos años en pesos reales; conteos
   entre territorios en tasas por habitante.

## Cálculos

### Variaciones del IPC
Con `I(t)` el índice del mes `t`:

| Medida | Fórmula |
|---|---|
| Mensual | `I(t) / I(t-1) - 1` |
| Anual (12 meses) | `I(t) / I(t-12) - 1` |
| Año corrido | `I(t) / I(diciembre del año anterior) - 1` |

La inflación anual de un año es la variación anual de su diciembre.

### Pesos constantes
`valor_real = valor_nominal × I(base) / I(mes de la fecha)` — `estadistica.deflactar`.

- **Base**: diciembre del año elegido, o el último mes publicado si el año está en curso.
- **Deflactar antes de agrupar**: cada monto con el IPC de *su* mes. Si se suman
  primero los contratos de un año y luego se deflacta el total, hay que usar el
  IPC promedio del año, no el de un mes arbitrario.
- Fechas sin IPC (antes de 2003 o meses aún no publicados) quedan vacías y se avisa cuántas.

Ejemplo verificado: $10.007.333 firmados en sep-2024 equivalen a $10.580.590 en pesos de dic-2025.

### Tasa por habitantes
`tasa = valor / población × 100.000` — `estadistica.tasa_por_habitantes`.

- Población: proyecciones DANE (CNPV 2018) del **mismo año** del dato.
- Cruce por código DIVIPOLA (2 dígitos departamento, 5 municipio), nunca por nombre.
- Antes de 2018 no hay proyección en este archivo: esas filas quedan sin población y se avisa.

## Reglas de las gráficas
Basadas en buenas prácticas de visualización accesible:

| Regla | Por qué |
|---|---|
| Colores en orden fijo de una paleta validada para daltonismo | Que cada categoría sea distinguible por cualquiera |
| Máximo 8 categorías (3 en dispersión); el resto, "Otros" en gris | Más colores ya no se distinguen |
| Mapas en una sola gama de azul (claro = poco, oscuro = mucho) | El arcoíris sugiere categorías y engaña sobre magnitud |
| Un solo eje Y; nunca doble eje | Con dos escalas se puede fabricar cualquier correlación |
| Fuente y pasos de procesamiento dentro de la imagen | La captura compartida conserva su origen |
| Tabla de datos de cada gráfica descargable | Quien dude puede revisar los números |
| En mapas de conteos, sugerir tasa por habitante | Un mapa de conteos es casi siempre un mapa de población |
| Aviso en dispersión: correlación ≠ causalidad | Evitar conclusiones que los datos no sostienen |
| Avisar siempre cuántas filas quedan excluidas | Nada desaparece en silencio |

## Historias publicadas

### Seguridad en Colombia (`analisis/seguridad_2026.py` → `app/pages/5_Historias.py`)
- **Ventanas**: tres periodos de 12 meses consecutivos que terminan en el último mes completo
  (`lokbi/analisis/seguridad.py::periodos`). Evita la estacionalidad y usa todos los meses disponibles.
- **Último mes**: se descarta siempre por incompleto (`ultimo_mes_completo`).
- **Tendencia**: suma móvil de 12 meses, eje desde cero.
- **Territorio**: tasa por 100.000 habitantes con la población del año en que termina el último periodo.
  La variación por departamento solo se publica con al menos 20 casos en el periodo anterior.
- **Secuestro**: se comparan registros (hechos), no víctimas, por el cambio de registro de 2025.
- **Texto**: todas las cifras del texto se calculan desde los CSV; no hay números escritos a mano.
  Las variaciones menores al 2 % se describen como "prácticamente igual".
- **Datos congelados**: las tablas exactas de la versión publicada están en `datos/historias/seguridad/`
  (en Git). Para actualizar: ejecutar el script y volver a publicar.
