"""Página Consultas SQL: consultas de solo lectura."""

import re

import oracledb
import streamlit as st

from conexion import consultar_solo_lectura, mensaje_error
from interfaz import titulo


def consultas_sql():
    titulo("Consultas SQL", "Consultas de solo lectura sobre huesped, habitacion, temporada y reserva.")
    sql = st.text_area("Consulta SELECT (sin punto y coma al final)", height=160,
                       placeholder="SELECT ha_tipo, COUNT(*) FROM habitacion GROUP BY ha_tipo")
    st.caption("Esta página solo permite leer datos. Los cambios se hacen desde las páginas de la app, "
               "que aplican las reglas de negocio.")
    if st.button("Ejecutar", type="primary") and sql.strip():
        texto = sql.strip().rstrip(";")
        if not re.match(r"^(SELECT|WITH)\b", texto, re.IGNORECASE) or ";" in texto:
            st.error("Solo se permite una consulta SELECT.")
            return
        try:
            st.dataframe(consultar_solo_lectura(texto), hide_index=True)
        except oracledb.Error as e:
            st.error(mensaje_error(e))
