"""Página Clientes: satisfacción, huéspedes frecuentes, cancelaciones y origen."""

import streamlit as st

from config import LATON, NOTA_CARTERA, PALISANDRO, SALVIA
from conexion import consultar
from interfaz import barras, barras_ingresos, filtro_anio, tabla, titulo


def clientes():
    titulo("Clientes", "Quiénes son los huéspedes, qué tan satisfechos quedan y quiénes vuelven.")
    filtro = filtro_anio("anio_clientes")
    t1, t2, t3, t4 = st.tabs(["Satisfacción", "Huéspedes frecuentes", "Cancelaciones", "Origen de los huéspedes"])

    with t1:
        df = consultar("""
            SELECT h.ha_tipo AS tipo, ROUND(AVG(r.re_calificacion), 2) AS promedio, COUNT(r.re_calificacion) AS calificaciones
            FROM reserva r JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
            WHERE r.re_calificacion IS NOT NULL AND (:anio = 0 OR EXTRACT(YEAR FROM r.re_fecha_entrada) = :anio)
            GROUP BY h.ha_tipo ORDER BY promedio DESC""", filtro)
        dist = consultar("""
            SELECT re_calificacion AS estrellas, COUNT(*) AS reservas FROM reserva
            WHERE re_calificacion IS NOT NULL AND (:anio = 0 OR EXTRACT(YEAR FROM re_fecha_entrada) = :anio)
            GROUP BY re_calificacion ORDER BY re_calificacion""", filtro)
        total = int(dist["reservas"].sum()) if len(dist) else 0
        prom = (dist["estrellas"] * dist["reservas"]).sum() / total if total else 0
        k = st.columns(3)
        k[0].metric("Calificación promedio", f"{prom:.2f} / 5")
        k[1].metric("Estadías calificadas", total)
        k[2].metric("Calificaciones de 1 o 2", int(dist.loc[dist["estrellas"] <= 2, "reservas"].sum()) if total else 0)
        izq, der = st.columns(2)
        with izq:
            barras(df, "tipo", "promedio", "Tipo de habitación", "Calificación promedio", color=SALVIA)
        with der:
            dist["estrellas"] = dist["estrellas"].astype(int).astype(str) + " ★"
            barras(dist, "estrellas", "reservas", "Calificación", "Reservas")
        st.caption("Solo se califican estadías finalizadas. Se registran en la página Reservas.")

    with t2:
        top = st.slider("Cuántos huéspedes mostrar", 5, 30, 10)
        df = consultar("""
            SELECT hu.hd_nombre AS huesped, hu.hd_pais AS pais, COUNT(*) AS reservas,
                   SUM(r.re_noches) AS noches, SUM(r.re_valor_total) AS gasto,
                   ROUND(AVG(r.re_calificacion), 1) AS calificacion
            FROM reserva r JOIN huesped hu ON hu.hd_id_huesped = r.re_id_huesped
            WHERE r.re_estado <> 'cancelada' AND (:anio = 0 OR EXTRACT(YEAR FROM r.re_fecha_entrada) = :anio)
            GROUP BY hu.hd_id_huesped, hu.hd_nombre, hu.hd_pais
            ORDER BY reservas DESC, noches DESC
            FETCH FIRST :n ROWS ONLY""", {**filtro, "n": int(top)})
        barras(df, "huesped", "reservas", "Huésped", "Reservas", horizontal=True, color=LATON)
        tabla(df, dinero=["gasto"], exportar="huespedes_frecuentes")

    with t3:
        df = consultar("""
            SELECT t.tp_nombre AS temporada, t.tp_fecha_inicio AS inicio,
                   SUM(CASE WHEN r.re_estado = 'cancelada' THEN 1 ELSE 0 END) AS canceladas, COUNT(*) AS total
            FROM reserva r JOIN temporada t ON t.tp_id_temporada = r.re_id_temporada
            WHERE (:anio = 0 OR EXTRACT(YEAR FROM r.re_fecha_entrada) = :anio)
            GROUP BY t.tp_id_temporada, t.tp_nombre, t.tp_fecha_inicio
            ORDER BY t.tp_fecha_inicio""", filtro)
        total, canc = int(df["total"].sum()), int(df["canceladas"].sum())
        k = st.columns(3)
        k[0].metric("Reservas", total)
        k[1].metric("Canceladas", canc)
        k[2].metric("Tasa de cancelación", f"{100 * canc / total:.1f} %" if total else "—")
        df["tasa_pct"] = (100 * df["canceladas"] / df["total"]).round(1)
        barras(df, "temporada", "tasa_pct", "Temporada", "Cancelación (%)", color=PALISANDRO)
        tabla(df[["temporada", "canceladas", "total", "tasa_pct"]], nombres={"tasa_pct": "cancelación %"},
              exportar="cancelaciones")

    with t4:
        df = consultar("""
            SELECT hu.hd_pais AS pais, COUNT(DISTINCT hu.hd_id_huesped) AS huespedes, COUNT(*) AS reservas,
                   ROUND(AVG(r.re_noches), 1) AS estadia_promedio,
                   SUM(CASE WHEN r.re_estado IN ('finalizada', 'en_curso') THEN r.re_valor_total ELSE 0 END) AS realizado,
                   SUM(CASE WHEN r.re_estado = 'confirmada' THEN r.re_valor_total ELSE 0 END) AS en_cartera,
                   SUM(r.re_valor_total) AS total
            FROM reserva r JOIN huesped hu ON hu.hd_id_huesped = r.re_id_huesped
            WHERE r.re_estado <> 'cancelada' AND (:anio = 0 OR EXTRACT(YEAR FROM r.re_fecha_entrada) = :anio)
            GROUP BY hu.hd_pais ORDER BY total DESC""", filtro)
        barras_ingresos(df, "pais", "País", horizontal=True)
        tabla(df, dinero=["realizado", "en_cartera", "total"],
              nombres={"pais": "país", "huespedes": "huéspedes", "estadia_promedio": "noches promedio",
                       "en_cartera": "en cartera"},
              exportar="origen_paises")
        st.caption(NOTA_CARTERA)
