"""Reglas de negocio que no pueden ser CHECK: edad, formato de documento y operaciones de recepción."""

import datetime as dt
import re

import oracledb
import streamlit as st

from config import HOY
from conexion import consultar, mensaje_error, transaccion


def edad(nacimiento, ref=HOY):
    return ref.year - nacimiento.year - ((ref.month, ref.day) < (nacimiento.month, nacimiento.day))


def limpiar_documento(texto):
    """Quita puntos, espacios y guiones, y pasa a mayúsculas: '1.036.654.321' -> '1036654321'."""
    return re.sub(r"[\s.\-]", "", texto or "").upper()


def huesped_por_documento(doc):
    return consultar("""SELECT hd_id_huesped, hd_nombre, hd_tipo_documento, hd_documento,
                               hd_fecha_nacimiento, hd_email, hd_telefono, hd_pais
                        FROM huesped WHERE hd_documento = :d
                        ORDER BY hd_tipo_documento""", {"d": limpiar_documento(doc)})


def mismo_dia_anio_anterior(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:            # 29 de febrero
        return d.replace(year=d.year - 1, day=28)


def hacer_checkin(reserva_id):
    try:
        with transaccion() as cur:
            cur.execute("""UPDATE reserva SET re_estado = 'en_curso', re_hora_checkin = :t
                           WHERE re_id_reserva = :id AND re_estado = 'confirmada'
                             AND re_fecha_entrada <= :h AND re_fecha_salida > :h""",
                        {"t": dt.datetime.now().replace(microsecond=0), "id": int(reserva_id), "h": HOY})
            ok = cur.rowcount
    except oracledb.Error as e:
        st.toast(mensaje_error(e))
        return
    st.toast(f"Check-in de la reserva {reserva_id} registrado." if ok else
             f"La reserva {reserva_id} no se pudo registrar: ya no estaba confirmada.")


def hacer_checkout(reserva_id):
    try:
        with transaccion() as cur:
            cur.execute("""UPDATE reserva SET re_estado = 'finalizada', re_hora_checkout = :t
                           WHERE re_id_reserva = :id AND re_estado = 'en_curso'""",
                        {"t": dt.datetime.now().replace(microsecond=0), "id": int(reserva_id)})
            ok = cur.rowcount
    except oracledb.Error as e:
        st.toast(mensaje_error(e))
        return
    st.toast(f"Check-out de la reserva {reserva_id} registrado." if ok else
             f"La reserva {reserva_id} no estaba en curso.")
