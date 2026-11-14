@echo off
REM Abre la app lokbi en el navegador. Para cerrarla, cierra esta ventana negra.
cd /d "%~dp0"
echo Iniciando lokbi... se abrira en tu navegador en unos segundos.
echo Para cerrar la app, cierra esta ventana.
".venv\Scripts\python.exe" -m streamlit run app\Inicio.py
pause
