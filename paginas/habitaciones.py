"""Página Habitaciones: situación del día y estado de servicio."""

import streamlit as st

from config import HOY
from conexion import consultar, escribir, valor
from interfaz import tabla, titulo


def habitaciones():
    titulo("Habitaciones", "Situación de cada habitación hoy y cambio a mantenimiento.")
    df = consultar("""
        SELECT h.ha_id_habitacion AS id, h.ha_numero AS numero, h.ha_tipo AS tipo, h.ha_capacidad AS capacidad,
               h.ha_piso AS piso, h.ha_precio_noche AS precio, h.ha_estado AS estado,
               CASE WHEN h.ha_estado = 'mantenimiento' THEN 'en mantenimiento'
                    WHEN EXISTS (SELECT 1 FROM reserva r
                                 WHERE r.re_id_habitacion = h.ha_id_habitacion AND r.re_estado <> 'cancelada'
                                   AND r.re_fecha_entrada <= :h AND r.re_fecha_salida > :h) THEN 'ocupada'
                    ELSE 'libre' END AS hoy
        FROM habitacion h ORDER BY h.ha_piso, h.ha_numero""", {"h": HOY})
    cuenta = df["hoy"].value_counts()
    k = st.columns(3)
    k[0].metric("Libres hoy", int(cuenta.get("libre", 0)))
    k[1].metric("Ocupadas hoy", int(cuenta.get("ocupada", 0)))
    k[2].metric("En mantenimiento", int(cuenta.get("en mantenimiento", 0)))
    tabla(df.drop(columns=["id"]), dinero=["precio"], exportar="habitaciones")

    st.subheader("Cambiar estado de una habitación")
    c1, c2 = st.columns(2)
    num = c1.selectbox("Habitación", df["numero"])
    fila = df[df["numero"] == num].iloc[0]
    nuevo = "mantenimiento" if fila["estado"] == "activa" else "activa"
    c2.write("")
    c2.write(f"Estado actual: **{fila['estado']}**")
    futuras = valor("""SELECT COUNT(*) FROM reserva WHERE re_id_habitacion = :id
                       AND re_estado IN ('confirmada', 'en_curso') AND re_fecha_salida > :h""",
                     {"id": int(fila["id"]), "h": HOY})
    if nuevo == "mantenimiento" and futuras:
        st.warning(f"La habitación {num} tiene {int(futuras)} reserva(s) pendientes o un huésped alojado. "
                   "Cámbialas de habitación en la página Reservas (Modificar reserva) antes de pasarla a mantenimiento.")
        return
    if st.button(f"Pasar a {nuevo}", type="primary"):
        if escribir("UPDATE habitacion SET ha_estado = :e WHERE ha_id_habitacion = :id",
                    {"e": nuevo, "id": int(fila["id"])}, f"Habitación {num} ahora está {nuevo}."):
            st.rerun()
