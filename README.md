# lokbi

Análisis **verificable** de datos públicos de Colombia (datos.gov.co, DANE, Banco de la República) y archivos propios.

## Principios
- Toda cifra lleva su fuente oficial y fecha de descarga.
- La limpieza y los cálculos están en este repositorio: cualquiera puede reproducirlos.
- Cada análisis declara sus limitaciones.
- Los montos de distintos años se comparan en pesos reales (deflactados por IPC).

## Abrir la app (lo más fácil)
Doble clic en **`abrir_app.bat`** (en la carpeta del proyecto). Se abre el navegador en http://localhost:8501.
Para cerrarla, cierra la ventana negra.

## Inicio rápido (Windows, terminal)
```bash
python -m venv .venv
source .venv/Scripts/activate     # PowerShell/cmd: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                            # pruebas
streamlit run app/Inicio.py       # abre http://localhost:8501
```

**🌐 App publicada:** https://sobaeuehf6p4rx8tdmrz5r.streamlit.app/

## Análisis publicados
- **Seguridad en Colombia: ¿qué pasó en los últimos dos años?**: homicidio, hurto, extorsión y secuestro con datos
  de la Policía Nacional, contrastados con Medicina Legal. Página *Historias* de la app; datos en
  `datos/historias/seguridad/`; código en `analisis/seguridad_2026.py`.

## Qué hace hoy
- **Cargar datos** desde:
  - archivos propios: CSV, Excel, JSON, Parquet;
  - **datos.gov.co**: búsqueda en el catálogo y consultas con filtros (SECOP, TRM, …);
  - **Banco de la República**: TRM, tasa de política monetaria, IBR, DTF, UVR, COLCAP, TES;
  - **DANE**: IPC mensual desde 2003 con inflación mensual, anual y año corrido.
- **Explorar**: tipos y nulos por columna, estadística descriptiva, histogramas y consultas SQL (DuckDB).
- **Transformar**: limpiar montos y fechas, filtrar, agrupar, **pesos constantes** (descontar inflación),
  código DIVIPOLA, **tasa por 100.000 habitantes** con población DANE. Cada paso queda registrado y se puede deshacer.
- **Graficar**: barras, líneas, dispersión, mapa por departamento y por municipio. La fuente y los pasos
  aplicados quedan impresos en la imagen.
- Caché local con registro de procedencia de cada descarga.

## Documentación
| Documento | Contenido |
|---|---|
| [docs/arquitectura.md](docs/arquitectura.md) | Módulos, flujo de datos, caché |
| [docs/fuentes.md](docs/fuentes.md) | Cada fuente: URLs, formato, peculiaridades, verificación |
| [docs/metodologia.md](docs/metodologia.md) | Reglas de verificabilidad y fórmulas |
| [docs/guia-desarrollo.md](docs/guia-desarrollo.md) | Entorno, comandos, uso desde Python, cómo agregar conectores |
| [docs/bitacora.md](docs/bitacora.md) | Decisiones y avances por fase |

## Hoja de ruta
1. ✅ Carga multiformato y exploración.
2. ✅ Conectores: datos.gov.co, Banco de la República, DANE (IPC).
3. ✅ Transformación, gráficas, mapas por departamento/municipio, pesos constantes, tasas por habitante.
4. ✅ Primera historia: seguridad, publicada en Streamlit Community Cloud (2026-11-25).
5. ⬜ Opcional: exportar para Power BI/Looker Studio, actualización automática.

## Publicar en internet (Streamlit Community Cloud, gratis)
1. Entrar a https://share.streamlit.io e iniciar sesión con GitHub.
2. **Create app** → **Deploy a public app from GitHub**.
3. Repositorio `jafm5/lokby`, rama `main`, archivo principal `app/Inicio.py`.
4. En *Advanced settings* elegir Python 3.12. **Deploy**.
5. Cada `git push` a `main` actualiza la app publicada.

## Actualizar la historia de seguridad
```bash
python analisis/seguridad_2026.py    # descarga datos nuevos y regenera datos/historias/seguridad/
git add datos/historias && git commit -m "Actualizar datos de seguridad" && git push
```
