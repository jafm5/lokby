"""Estado compartido entre páginas: la tabla activa, su fuente y los pasos aplicados.

session_state:
    df          tabla activa
    df_nombre   nombre de la tabla
    df_fuente   procedencia (texto)
    historial   lista de (DataFrame, descripción del paso) para deshacer
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def cargar(df: pd.DataFrame, nombre: str, fuente: str) -> None:
    """Nueva tabla: reinicia el historial de transformaciones."""
    st.session_state["df"] = df
    st.session_state["df_nombre"] = nombre
    st.session_state["df_fuente"] = fuente
    st.session_state["historial"] = []


def hay_datos() -> bool:
    return "df" in st.session_state


def exigir_datos() -> pd.DataFrame:
    """Detiene la página con un aviso si no hay tabla cargada."""
    if not hay_datos():
        st.warning("Primero carga datos.")
        st.page_link("pages/1_Cargar_datos.py", label="Ir a Cargar datos", icon="📥")
        st.stop()
    return st.session_state["df"]


def aplicar(df_nuevo: pd.DataFrame, paso: str) -> None:
    """Reemplaza la tabla activa guardando la anterior para poder deshacer."""
    st.session_state.setdefault("historial", []).append((st.session_state["df"], paso))
    st.session_state["df"] = df_nuevo


def deshacer() -> str | None:
    historial = st.session_state.get("historial", [])
    if not historial:
        return None
    anterior, paso = historial.pop()
    st.session_state["df"] = anterior
    return paso


def pasos() -> list[str]:
    return [p for _, p in st.session_state.get("historial", [])]


def fuente() -> str:
    return st.session_state.get("df_fuente") or "⚠️ sin fuente registrada"


def encabezado() -> None:
    """Línea con nombre, fuente y pasos aplicados a la tabla activa."""
    st.caption(f"Tabla: **{st.session_state['df_nombre']}** · Fuente: {fuente()}")
    if pasos():
        st.caption("Pasos aplicados: " + " → ".join(pasos()))


def aviso(texto: str) -> None:
    """Mensaje que sobrevive a st.rerun(); se muestra con mostrar_aviso()."""
    st.session_state["aviso"] = texto


def mostrar_aviso() -> None:
    texto = st.session_state.pop("aviso", None)
    if texto:
        st.warning(texto)
