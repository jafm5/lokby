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

### Pesos constantes (fase 3)
`valor_real = valor_nominal × I(base) / I(fecha)`.
Ejemplo: comparar contratos de 2019 y 2025 llevándolos a pesos de 2025.
