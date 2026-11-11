"""Página Desempeño: ocupación, ADR, RevPAR, ingresos, canales, anticipación, ritmo y horarios."""

import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from config import CANALES, COMISION, HOY, LATON, NOTA_CARTERA, PALISANDRO, PIEDRA, SALVIA, TINTA
from conexion import consultar, valor
from interfaz import barras, barras_ingresos, filtro_anio, tabla, titulo


def desempeno():
    titulo("Desempeño del hotel", "Ocupación, tarifas e ingresos con los indicadores que usa la hotelería.")
    filtro = filtro_anio("anio_desempeno")
    t1, t2, t3, t4, t5, t6 = st.tabs(["Ocupación, ADR y RevPAR", "Ingresos por tipo de habitación",
                                      "Canales de venta", "Anticipación de reserva", "Ritmo de reservas",
                                      "Horarios de llegada y salida"])

    with t1:
        n_hab = int(valor("SELECT COUNT(*) FROM habitacion"))
        df = consultar("""
            SELECT t.tp_nombre AS temporada, t.tp_fecha_inicio AS inicio, t.tp_recargo AS recargo,
                   (t.tp_fecha_fin - t.tp_fecha_inicio + 1) AS dias,
                   COUNT(r.re_id_reserva) AS reservas, NVL(SUM(r.re_noches), 0) AS noches_vendidas,
                   NVL(SUM(r.re_valor_total), 0) AS ingresos
            FROM temporada t
            LEFT JOIN reserva r ON r.re_id_temporada = t.tp_id_temporada AND r.re_estado <> 'cancelada'
            WHERE (:anio = 0 OR EXTRACT(YEAR FROM t.tp_fecha_inicio) = :anio)
            GROUP BY t.tp_id_temporada, t.tp_nombre, t.tp_fecha_inicio, t.tp_fecha_fin, t.tp_recargo
            ORDER BY t.tp_fecha_inicio""", filtro)
        disponibles = df["dias"].astype(float) * n_hab
        df["ocupacion_pct"] = (100 * df["noches_vendidas"] / disponibles).round(1)
        df["adr"] = (df["ingresos"].astype(float) / df["noches_vendidas"].where(df["noches_vendidas"] > 0)).fillna(0).round(0)
        df["revpar"] = (df["ingresos"].astype(float) / disponibles).round(0)
        st.markdown("**ADR** = ingresos ÷ noches vendidas (cuánto paga en promedio cada noche).  \n"
                    "**RevPAR** = ingresos ÷ noches disponibles (combina precio y ocupación en un solo número).")
        izq, der = st.columns(2)
        with izq:
            barras(df, "temporada", "ocupacion_pct", "Temporada", "Ocupación (%)")
        with der:
            barras(df, "temporada", "revpar", "Temporada", "RevPAR ($)", color=LATON)
        tabla(df[["temporada", "recargo", "reservas", "noches_vendidas", "ocupacion_pct", "adr", "revpar"]],
              dinero=["adr", "revpar"],
              nombres={"noches_vendidas": "noches vendidas", "ocupacion_pct": "ocupación %", "adr": "ADR", "revpar": "RevPAR"},
              exportar="ocupacion_adr_revpar")
        st.caption("Las noches de cada estadía se asignan a la temporada de su fecha de entrada. "
                   "En las temporadas que no han terminado, la ocupación, el ADR y el RevPAR incluyen las reservas "
                   "confirmadas (en cartera).")

    with t2:
        df = consultar("""
            SELECT h.ha_tipo AS tipo, COUNT(*) AS reservas, SUM(r.re_noches) AS noches,
                   SUM(CASE WHEN r.re_estado IN ('finalizada', 'en_curso') THEN r.re_valor_total ELSE 0 END) AS realizado,
                   SUM(CASE WHEN r.re_estado = 'confirmada' THEN r.re_valor_total ELSE 0 END) AS en_cartera,
                   SUM(r.re_valor_total) AS total, ROUND(SUM(r.re_valor_total) / SUM(r.re_noches)) AS adr
            FROM reserva r JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
            WHERE r.re_estado <> 'cancelada' AND (:anio = 0 OR EXTRACT(YEAR FROM r.re_fecha_entrada) = :anio)
            GROUP BY h.ha_tipo ORDER BY total DESC""", filtro)
        barras_ingresos(df, "tipo", "Tipo de habitación")
        tabla(df, dinero=["realizado", "en_cartera", "total", "adr"], nombres={"en_cartera": "en cartera", "adr": "ADR"},
              exportar="ingresos_por_tipo")
        st.caption(NOTA_CARTERA)

    with t3:
        df = consultar("""
            SELECT re_canal AS canal, COUNT(*) AS reservas,
                   SUM(CASE WHEN re_estado = 'cancelada' THEN 1 ELSE 0 END) AS canceladas,
                   SUM(CASE WHEN re_estado <> 'cancelada' THEN re_valor_total ELSE 0 END) AS ingresos,
                   SUM(CASE WHEN re_estado IN ('finalizada', 'en_curso') THEN re_valor_total ELSE 0 END) AS realizado_bruto,
                   SUM(CASE WHEN re_estado = 'confirmada' THEN re_valor_total ELSE 0 END) AS cartera_bruto
            FROM reserva
            WHERE (:anio = 0 OR EXTRACT(YEAR FROM re_fecha_entrada) = :anio)
            GROUP BY re_canal ORDER BY ingresos DESC""", filtro)
        df["comision_pct"] = df["canal"].map(COMISION).fillna(0) * 100
        df["ingreso_neto"] = (df["ingresos"].astype(float) * (1 - df["comision_pct"] / 100)).round(0)
        df["cancelacion_pct"] = (100 * df["canceladas"] / df["reservas"]).round(1)
        df["nombre"] = df["canal"].map(CANALES).fillna(df["canal"])
        df["realizado"] = (df["realizado_bruto"].astype(float) * (1 - df["comision_pct"] / 100)).round(0)
        df["en_cartera"] = (df["cartera_bruto"].astype(float) * (1 - df["comision_pct"] / 100)).round(0)
        izq, der = st.columns(2)
        with izq:
            barras_ingresos(df, "nombre", "Canal", horizontal=True, titulo_valor="Ingreso neto (millones)")
        with der:
            barras(df, "nombre", "cancelacion_pct", "Canal", "Cancelación (%)", horizontal=True, color=PALISANDRO)
        tabla(df[["nombre", "reservas", "canceladas", "cancelacion_pct", "ingresos", "comision_pct", "realizado",
                  "en_cartera", "ingreso_neto"]],
              dinero=["ingresos", "realizado", "en_cartera", "ingreso_neto"],
              nombres={"nombre": "canal", "cancelacion_pct": "cancelación %", "comision_pct": "comisión %",
                       "ingresos": "ingreso bruto", "realizado": "neto realizado", "en_cartera": "neto en cartera",
                       "ingreso_neto": "ingreso neto total"}, exportar="canales")
        st.caption("Comisiones supuestas para el análisis: Booking 18 %, agencia 12 %, directo y walk-in 0 %. " + NOTA_CARTERA)

    with t4:
        df = consultar("""
            SELECT t.tp_nombre AS temporada, t.tp_fecha_inicio AS inicio,
                   ROUND(AVG(r.re_fecha_entrada - r.re_fecha_reserva), 1) AS dias_promedio,
                   SUM(CASE WHEN r.re_fecha_entrada = r.re_fecha_reserva THEN 1 ELSE 0 END) AS mismo_dia,
                   COUNT(*) AS reservas
            FROM reserva r JOIN temporada t ON t.tp_id_temporada = r.re_id_temporada
            WHERE (:anio = 0 OR EXTRACT(YEAR FROM r.re_fecha_entrada) = :anio)
            GROUP BY t.tp_id_temporada, t.tp_nombre, t.tp_fecha_inicio
            ORDER BY t.tp_fecha_inicio""", filtro)
        barras(df, "temporada", "dias_promedio", "Temporada", "Días de anticipación (promedio)", color=PIEDRA)
        rangos = consultar("""
            SELECT CASE WHEN dias = 0 THEN '1. El mismo día'
                        WHEN dias <= 7 THEN '2. 1 a 7 días'
                        WHEN dias <= 30 THEN '3. 8 a 30 días'
                        WHEN dias <= 90 THEN '4. 31 a 90 días'
                        ELSE '5. Más de 90 días' END AS anticipacion,
                   COUNT(*) AS reservas
            FROM (SELECT re_fecha_entrada - re_fecha_reserva AS dias FROM reserva
                  WHERE (:anio = 0 OR EXTRACT(YEAR FROM re_fecha_entrada) = :anio))
            GROUP BY CASE WHEN dias = 0 THEN '1. El mismo día'
                          WHEN dias <= 7 THEN '2. 1 a 7 días'
                          WHEN dias <= 30 THEN '3. 8 a 30 días'
                          WHEN dias <= 90 THEN '4. 31 a 90 días'
                          ELSE '5. Más de 90 días' END
            ORDER BY 1""", filtro)
        rangos["anticipacion"] = rangos["anticipacion"].str[3:]
        barras(rangos, "anticipacion", "reservas", "¿Con cuánta anticipación reservan?", "Reservas")


    with t5:
        ritmo_de_reservas()

    with t6:
        llegadas = consultar("""
            SELECT TO_NUMBER(TO_CHAR(re_hora_checkin, 'HH24')) AS hora, COUNT(*) AS llegadas
            FROM reserva WHERE re_hora_checkin IS NOT NULL
              AND (:anio = 0 OR EXTRACT(YEAR FROM re_fecha_entrada) = :anio)
            GROUP BY TO_NUMBER(TO_CHAR(re_hora_checkin, 'HH24')) ORDER BY 1""", filtro)
        salidas = consultar("""
            SELECT TO_NUMBER(TO_CHAR(re_hora_checkout, 'HH24')) AS hora, COUNT(*) AS salidas
            FROM reserva WHERE re_hora_checkout IS NOT NULL
              AND (:anio = 0 OR EXTRACT(YEAR FROM re_fecha_entrada) = :anio)
            GROUP BY TO_NUMBER(TO_CHAR(re_hora_checkout, 'HH24')) ORDER BY 1""", filtro)
        if llegadas.empty:
            st.info("Todavía no hay check-in registrados para ese año.")
        else:
            total_in = int(llegadas["llegadas"].sum())
            pico = int(llegadas.loc[llegadas["llegadas"].idxmax(), "hora"])
            nocturnas = int(llegadas.loc[llegadas["hora"] >= 20, "llegadas"].sum())
            tardias = int(salidas.loc[salidas["hora"] > 12, "salidas"].sum()) if len(salidas) else 0
            k = st.columns(3)
            k[0].metric("Hora pico de llegada", f"{pico}:00")
            k[1].metric("Llegadas después de las 20:00", f"{100 * nocturnas / total_in:.0f} %",
                        f"{nocturnas} check-in", delta_color="off")
            k[2].metric("Salidas después de las 12:00", tardias, "salida tardía", delta_color="off")
            for df_h in (llegadas, salidas):
                df_h["hora"] = df_h["hora"].astype(int).map(lambda h: f"{h:02d}:00")
            izq, der = st.columns(2)
            with izq:
                barras(llegadas, "hora", "llegadas", "Hora de check-in", "Llegadas", color=SALVIA)
            with der:
                barras(salidas, "hora", "salidas", "Hora de check-out", "Salidas", color=LATON)
            st.caption("Sirve para planear el personal de recepción y la limpieza de habitaciones.")


def ritmo_de_reservas():
    st.markdown("¿Cómo va la ocupación de un mes **comparada con el año anterior a la misma distancia**? "
                "Cada línea suma las noches reservadas según el día en que se hizo la reserva (`re_fecha_reserva`).")
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
             "octubre", "noviembre", "diciembre"]
    c1, c2 = st.columns(2)
    anio = c1.selectbox("Año", [2025, 2026, 2027], index=1, key="ritmo_anio")
    mes = c2.selectbox("Mes", range(1, 13), index=11, format_func=lambda m: meses[m - 1], key="ritmo_mes")
    n_hab = int(valor("SELECT COUNT(*) FROM habitacion"))

    def periodo(a):
        ini = dt.date(a, mes, 1)
        fin = dt.date(a + (mes == 12), mes % 12 + 1, 1)
        return ini, fin

    def reservas_del_periodo(ini, fin):
        df = consultar("""
            SELECT re_fecha_reserva AS fr, GREATEST(re_fecha_entrada, :i) AS e, LEAST(re_fecha_salida, :f) AS s
            FROM reserva
            WHERE re_estado <> 'cancelada' AND re_fecha_entrada < :f AND re_fecha_salida > :i""", {"i": ini, "f": fin})
        if df.empty:
            return df
        df["noches"] = (pd.to_datetime(df["s"]) - pd.to_datetime(df["e"])).dt.days
        df["antes"] = (pd.Timestamp(ini) - pd.to_datetime(df["fr"])).dt.days   # días antes del día 1 del mes
        return df

    ini, fin = periodo(anio)
    ini_a, fin_a = periodo(anio - 1)
    capacidad = (fin - ini).days * n_hab
    actual, anterior = reservas_del_periodo(ini, fin), reservas_del_periodo(ini_a, fin_a)
    hoy_antes = (ini - HOY).days                     # cuántos días faltan para el mes (negativo si ya empezó)
    ventana = range(120, -(fin - ini).days, -1)

    def curva(df, desde_hoy):
        filas = []
        for d in ventana:
            if desde_hoy and d < hoy_antes:
                break                                 # días que todavía no han llegado
            n = int(df.loc[df["antes"] >= d, "noches"].sum()) if len(df) else 0
            filas.append({"dias_antes": d, "ocupacion": round(100 * n / capacidad, 1), "noches": n})
        return pd.DataFrame(filas)

    serie_act = curva(actual, desde_hoy=True).assign(periodo=f"{meses[mes - 1]} {anio}")
    serie_ant = curva(anterior, desde_hoy=False).assign(periodo=f"{meses[mes - 1]} {anio - 1}")
    if serie_act.empty and serie_ant.empty:
        st.info("No hay reservas para ese mes ni para el mismo mes del año anterior.")
        return

    corte = max(hoy_antes, ventana[-1])
    hoy_act = int(actual.loc[actual["antes"] >= corte, "noches"].sum()) if len(actual) else 0
    hoy_ant = int(anterior.loc[anterior["antes"] >= corte, "noches"].sum()) if len(anterior) else 0
    final_ant = int(anterior["noches"].sum()) if len(anterior) else 0
    k = st.columns(3)
    etiqueta = f"a {hoy_antes} días del inicio" if hoy_antes > 0 else "al cierre del mes" if HOY >= fin else "en lo que va del mes"
    k[0].metric(f"Ocupación reservada {anio}", f"{100 * hoy_act / capacidad:.0f} %", etiqueta, delta_color="off")
    k[1].metric(f"{anio - 1} a la misma distancia", f"{100 * hoy_ant / capacidad:.0f} %",
                f"{100 * (hoy_act - hoy_ant) / capacidad:+.0f} pts" if hoy_ant or hoy_act else None)
    k[2].metric(f"{anio - 1} al cierre", f"{100 * final_ant / capacidad:.0f} %", "dónde terminó el año pasado",
                delta_color="off")

    datos = pd.concat([serie_ant, serie_act])
    linea = alt.Chart(datos).mark_line(strokeWidth=3).encode(
        x=alt.X("dias_antes:Q", scale=alt.Scale(reverse=True), title="Días antes del 1 del mes (negativo: ya dentro del mes)"),
        y=alt.Y("ocupacion:Q", title="Ocupación reservada (%)"),
        color=alt.Color("periodo:N", scale=alt.Scale(range=[PIEDRA, TINTA]), legend=alt.Legend(title=None, orient="bottom")),
        tooltip=[alt.Tooltip("periodo", title="Mes"), alt.Tooltip("dias_antes", title="Días antes"),
                 alt.Tooltip("ocupacion", title="Ocupación %"), alt.Tooltip("noches", title="Noches")])
    st.altair_chart(linea)
    st.caption("Las reservas canceladas no se cuentan, porque la base no guarda la fecha en que se cancelaron.")
