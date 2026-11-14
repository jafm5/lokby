"""Genera los datos de la historia "Seguridad en Colombia: los últimos dos años".

Uso (desde la carpeta del proyecto):
    .venv/Scripts/python analisis/seguridad_2026.py

Descarga los datos oficiales, hace los cálculos de `lokbi.analisis.seguridad` y
guarda las tablas en `datos/historias/seguridad/`. Esas tablas se suben al
repositorio: son la "foto" exacta de los datos con que se escribió la historia.
Volver a ejecutar el script con datos nuevos actualiza todas las cifras.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from lokbi.analisis import seguridad as s
from lokbi.ingesta import dane, mindefensa

SALIDA = Path(__file__).resolve().parent.parent / "datos" / "historias" / "seguridad"
DELITOS = ["Homicidio", "Hurto a personas", "Extorsión", "Secuestro"]
CATEGORIAS_HOMICIDIO = {"arma_medio": "arma", "_modalidad_presunta": "modalidad", "zona": "zona", "sexo": "sexo"}


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    fuentes: dict[str, str] = {}

    series = {}
    for delito in DELITOS:
        df, proc = mindefensa.mensual_por_departamento(delito)
        series[delito] = df
        fuentes[delito] = proc.fuente

    # Corte común: el último mes completo publicado en TODAS las series
    corte = min(s.ultimo_mes_completo(df["mes"]) for df in series.values())
    ps = s.periodos(corte)
    ultimo_publicado = max(df["mes"].max() for df in series.values())

    pob, pob_proc = dane.poblacion("departamento")
    fuentes["Población"] = pob_proc.fuente
    anio_pob = ps[-1].fin.year
    pob_total = pob.loc[pob["anio"] == anio_pob, "poblacion"].sum()

    resumen, mensual, deptos = [], [], []
    for delito, df in series.items():
        resumen.append({"delito": delito, **s.resumen_delito(df, ps, pob_total)})
        m = s.acumulado_12_meses(df[df["mes"] <= corte])
        mensual.append(m.assign(delito=delito))
        deptos.append(s.por_departamento(df, ps, pob, anio_pob).assign(delito=delito))
        # Mes preliminar (excluido de los cálculos), para mostrarlo aparte
        resumen[-1]["mes_preliminar"] = float(df.loc[df["mes"] == ultimo_publicado, "cantidad"].sum())
        resumen[-1]["promedio_mensual_ultimo"] = resumen[-1][ps[-1].nombre] / 12

    pd.DataFrame(resumen).to_csv(SALIDA / "resumen.csv", index=False)
    pd.concat(mensual).to_csv(SALIDA / "mensual_nacional.csv", index=False)
    pd.concat(deptos).to_csv(SALIDA / "departamentos.csv", index=False)

    # Homicidio: características en los dos últimos periodos
    filas = []
    for col, nombre in CATEGORIAS_HOMICIDIO.items():
        for p in ps[-2:]:
            hasta = (p.fin + pd.DateOffset(months=1)).strftime("%Y-%m-%d")
            df, _ = mindefensa.por_categoria("Homicidio", col, p.inicio.strftime("%Y-%m-%d"), hasta)
            filas.append(df.rename(columns={col: "valor"}).assign(categoria=nombre, periodo=p.nombre))
    pd.concat(filas).to_csv(SALIDA / "homicidio_caracteristicas.csv", index=False)

    # ¿Cambio real o cambio de clasificación? Serie mensual de las dos modalidades principales
    hasta = (corte + pd.DateOffset(months=1)).strftime("%Y-%m-%d")
    gao, _ = mindefensa.mensual_por_categoria(
        "Homicidio", "_modalidad_presunta", ["SICARIATO", "ATACADOS POR GAO O GAO-R"],
        ps[0].inicio.strftime("%Y-%m-%d"), hasta,
    )
    gao.to_csv(SALIDA / "homicidio_modalidad_mensual.csv", index=False)

    # Secuestro: ¿el cambio se explica por pocos hechos masivos?
    filas = []
    for p in ps:
        desde, hasta = p.inicio.strftime("%Y-%m-%d"), (p.fin + pd.DateOffset(months=1)).strftime("%Y-%m-%d")
        todos = mindefensa.registros_y_victimas("Secuestro", desde, hasta)
        masivos = mindefensa.registros_y_victimas("Secuestro", desde, hasta, min_victimas=5)
        filas.append({
            "periodo": p.nombre,
            "registros": todos["registros"], "victimas": todos["victimas"],
            "registros_masivos": masivos["registros"], "victimas_en_masivos": masivos["victimas"],
        })
    pd.DataFrame(filas).to_csv(SALIDA / "secuestro.csv", index=False)

    # Contraste con Medicina Legal (fuente independiente)
    ml, ml_proc = mindefensa.medicina_legal_homicidios_anuales()
    fuentes["Medicina Legal"] = ml_proc.fuente
    hom = series["Homicidio"]
    policia_anual = hom.groupby(hom["mes"].dt.year)["cantidad"].sum()
    s.contraste_fuentes(policia_anual, ml).to_csv(SALIDA / "contraste_medicina_legal.csv", index=False)

    meta = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "ultimo_mes_publicado": ultimo_publicado.strftime("%Y-%m"),
        "corte": corte.strftime("%Y-%m"),
        "periodos": {p.nombre: p.etiqueta for p in ps},
        "anio_poblacion": anio_pob,
        "poblacion_total": float(pob_total),
        "fuentes": fuentes,
    }
    (SALIDA / "metadatos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo: {SALIDA}  (corte {meta['corte']}, periodos {meta['periodos']})")


if __name__ == "__main__":
    main()
