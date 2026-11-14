# lokbi — instrucciones para Claude

- Idioma: español en código, comentarios, documentación y commits.
- Mantener la documentación al día en cada cambio: `docs/bitacora.md` (decisiones y avances con fecha),
  `docs/fuentes.md` (comportamiento verificado de cada fuente), `docs/arquitectura.md`, `README.md` (hoja de ruta).
- Todo dato externo se devuelve como `(DataFrame, Procedencia)` vía `lokbi/cache.py`.
- Entorno: `.venv` (Python 3.10, pip). Pruebas: `.venv/Scripts/python -m pytest` y `-m red` para APIs reales.
- No afirmar que una cifra está verificada si no se contrastó con la publicación oficial.
