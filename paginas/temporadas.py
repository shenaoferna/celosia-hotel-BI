"""Página Temporadas: consulta, creación y eliminación."""

import datetime as dt

import oracledb
import pandas as pd
import streamlit as st

from config import HOY
from conexion import consultar, escribir, mensaje_error, transaccion, valor
from interfaz import tabla, titulo


def temporadas():
    titulo("Temporadas", "Períodos del año con su recargo. Las reservas toman la temporada de su fecha de entrada.")
    df = consultar("""SELECT tp_nombre AS temporada, tp_fecha_inicio AS inicio, tp_fecha_fin AS fin,
                             tp_recargo AS recargo FROM temporada ORDER BY tp_fecha_inicio""")
    df["recargo"] = df["recargo"].map(lambda v: f"{float(v):.0f} %")
    tabla(df, fechas=["inicio", "fin"], exportar="temporadas")
    ultima = pd.to_datetime(df["fin"]).max().date() if len(df) else HOY

    st.subheader("Crear temporada")
    with st.form("form_temporada"):
        nombre = st.text_input("Nombre", placeholder="Semana Santa 2027")
        c1, c2, c3 = st.columns(3)
        ini = c1.date_input("Inicio", value=ultima + dt.timedelta(days=1), format="DD/MM/YYYY")
        fin = c2.date_input("Fin", value=ultima + dt.timedelta(days=8), format="DD/MM/YYYY")
        rec = c3.number_input("Recargo (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0)
        crear = st.form_submit_button("Crear temporada", type="primary")
    if crear:
        if not nombre.strip():
            st.error("Escribe un nombre para la temporada.")
        elif fin <= ini:
            st.error("La fecha de fin debe ser posterior a la de inicio.")
        elif valor("SELECT COUNT(*) FROM temporada WHERE :i <= tp_fecha_fin AND :f >= tp_fecha_inicio",
                   {"i": ini, "f": fin}):
            st.error("Esas fechas se cruzan con otra temporada. Cada día debe pertenecer a una sola temporada.")
        else:
            try:
                with transaccion() as cur:
                    cur.execute("""INSERT INTO temporada (tp_nombre, tp_fecha_inicio, tp_fecha_fin, tp_recargo)
                                   VALUES (:n, :i, :f, :r)""", {"n": nombre.strip(), "i": ini, "f": fin, "r": rec})
                st.success(f"Temporada «{nombre.strip()}» creada.")
                st.rerun()
            except oracledb.IntegrityError:
                st.error("Ya existe una temporada con ese nombre.")
            except oracledb.Error as e:
                st.error(mensaje_error(e))

    # ---- Eliminar: solo temporadas sin reservas (la FK de reserva protege las que se usan) ----
    st.subheader("Eliminar temporada")
    lista = consultar("""
        SELECT t.tp_id_temporada AS id, t.tp_nombre AS temporada, COUNT(r.re_id_reserva) AS reservas
        FROM temporada t LEFT JOIN reserva r ON r.re_id_temporada = t.tp_id_temporada
        GROUP BY t.tp_id_temporada, t.tp_nombre, t.tp_fecha_inicio
        ORDER BY t.tp_fecha_inicio""")
    opciones = {f"{x.temporada} ({x.reservas} reservas)": x for x in lista.itertuples()}
    elegida = opciones[st.selectbox("Temporada", list(opciones), key="borrar_temporada")]
    if elegida.reservas:
        st.caption("Esta temporada tiene reservas, así que no se puede eliminar: perderían su temporada.")
    else:
        confirmar = st.checkbox(f"Confirmo que quiero eliminar «{elegida.temporada}»", key="confirmar_borrar_temporada")
        if st.button("Eliminar temporada", disabled=not confirmar):
            if escribir("DELETE FROM temporada WHERE tp_id_temporada = :id", {"id": int(elegida.id)},
                        f"Temporada «{elegida.temporada}» eliminada."):
                st.rerun()
