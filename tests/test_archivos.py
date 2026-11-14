import io
import json

import pandas as pd
import pytest

from lokbi.ingesta.archivos import FormatoNoSoportado, leer_archivo


def test_csv_coma_utf8():
    datos = "departamento,valor\nAntioquia,10\nBogotá D.C.,20\n".encode("utf-8")
    df = leer_archivo(datos, nombre="x.csv")
    assert list(df.columns) == ["departamento", "valor"]
    assert df.loc[1, "departamento"] == "Bogotá D.C."
    assert df["valor"].sum() == 30


def test_csv_punto_y_coma_latin1():
    # Así exporta Excel en español
    datos = "municipio;población\nMedellín;2600000\nCúcuta;780000\n".encode("cp1252")
    df = leer_archivo(datos, nombre="x.csv")
    assert list(df.columns) == ["municipio", "población"]
    assert df.loc[1, "municipio"] == "Cúcuta"


def test_csv_con_bom():
    datos = "﻿a,b\n1,2\n".encode("utf-8")
    df = leer_archivo(datos, nombre="x.csv")
    assert list(df.columns) == ["a", "b"]


def test_excel_con_titulo_arriba_estilo_dane():
    buffer = io.BytesIO()
    filas = [
        ["DANE - Departamento Administrativo Nacional de Estadística", None, None],
        ["Índice de Precios al Consumidor", None, None],
        [None, None, None],
        ["Año", "Mes", "Variación anual %"],
        [2023, "Diciembre", 9.28],
        [2024, "Diciembre", 5.20],
    ]
    pd.DataFrame(filas).to_excel(buffer, header=False, index=False)
    df = leer_archivo(buffer.getvalue(), nombre="anexo.xlsx")
    assert list(df.columns) == ["Año", "Mes", "Variación anual %"]
    assert len(df) == 2
    assert df.loc[1, "Variación anual %"] == pytest.approx(5.20)


def test_json_lista_de_registros_socrata():
    registros = [{"entidad": "A", "valor": "100"}, {"entidad": "B", "valor": "200"}]
    df = leer_archivo(json.dumps(registros).encode(), nombre="x.json")
    assert len(df) == 2 and set(df.columns) == {"entidad", "valor"}


def test_json_envuelto_en_data():
    datos = json.dumps({"data": [{"a": 1, "b": {"c": 2}}]}).encode()
    df = leer_archivo(datos, nombre="x.json")
    assert df.loc[0, "b.c"] == 2


def test_formato_no_soportado():
    with pytest.raises(FormatoNoSoportado):
        leer_archivo(b"x", nombre="foto.png")
