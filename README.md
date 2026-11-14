# lokbi

Análisis **verificable** de datos públicos de Colombia (datos.gov.co, DANE, Banco de la República) y archivos propios.

## Principios
- Toda cifra lleva su fuente oficial y fecha de descarga.
- La limpieza y los cálculos están en este repositorio: cualquiera puede reproducirlos.
- Cada análisis declara sus limitaciones.
- Los montos de distintos años se comparan en pesos reales (deflactados por IPC).

## Instalación (Windows)
```bash
python -m venv .venv
.venv\Scripts\activate          # en Git Bash: source .venv/Scripts/activate
pip install -e ".[dev]"
```

## Uso
```bash
pytest                          # pruebas
streamlit run app/Inicio.py     # abre http://localhost:8501
```

## Estructura
- `lokbi/`: lógica (ingesta, limpieza, estadística), sin dependencia de la interfaz.
- `app/`: interfaz web en Streamlit.
- `analisis/`: investigaciones reproducibles.
- `datos/`: crudos y procesados (no se suben a Git).

## Hoja de ruta
1. ✅ Carga multiformato (CSV, Excel, JSON, Parquet) y exploración.
2. Conectores: datos.gov.co (Socrata), Banco de la República, DANE.
3. Gráficas, mapas por departamento/municipio, deflactar por IPC.
4. Primera historia publicada en Streamlit Community Cloud.
