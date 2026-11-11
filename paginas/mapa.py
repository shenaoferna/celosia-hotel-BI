"""Página Mapa de ocupación: habitaciones por días del mes."""

import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from config import HOY, PALISANDRO, TINTA
from conexion import consultar
from interfaz import seleccion, tabla, titulo


def mapa_ocupacion():
    titulo("Mapa de ocupación", "Cada fila es una habitación y cada columna un día del mes.")
    c1, c2 = st.columns(2)
    anio = c1.selectbox("Año", [2025, 2026, 2027], index=[2025, 2026, 2027].index(HOY.year) if HOY.year in (2025, 2026, 2027) else 1)
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
             "octubre", "noviembre", "diciembre"]
    mes = c2.selectbox("Mes", range(1, 13), index=HOY.month - 1, format_func=lambda m: meses[m - 1])
    ini = dt.date(anio, mes, 1)
    fin = dt.date(anio + (mes == 12), mes % 12 + 1, 1)          # primer día del mes siguiente

    habs = consultar("SELECT ha_numero AS habitacion, ha_tipo AS tipo, ha_estado AS estado FROM habitacion ORDER BY ha_numero")
    res = consultar("""
        SELECT h.ha_numero AS habitacion, r.re_id_reserva AS reserva, hu.hd_nombre AS huesped,
               r.re_fecha_entrada AS entrada, r.re_fecha_salida AS salida
        FROM reserva r
        JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
        JOIN huesped hu ON hu.hd_id_huesped = r.re_id_huesped
        WHERE r.re_estado <> 'cancelada' AND r.re_fecha_entrada < :fin AND r.re_fecha_salida > :ini""",
        {"ini": ini, "fin": fin})

    dias = pd.date_range(ini, fin - dt.timedelta(days=1)).date
    grilla = pd.DataFrame([(h, d) for h in habs["habitacion"] for d in dias], columns=["habitacion", "fecha"])
    grilla["estado"], grilla["detalle"] = "libre", ""
    mant = set(habs.loc[habs["estado"] == "mantenimiento", "habitacion"])
    grilla.loc[grilla["habitacion"].isin(mant) & (grilla["fecha"] >= HOY), "estado"] = "mantenimiento"
    for r in res.itertuples():
        e, s = pd.to_datetime(r.entrada).date(), pd.to_datetime(r.salida).date()
        m = (grilla["habitacion"] == r.habitacion) & (grilla["fecha"] >= e) & (grilla["fecha"] < s)
        grilla.loc[m, "estado"] = "ocupada"
        grilla.loc[m, "detalle"] = f"Reserva {r.reserva}: {r.huesped}"
    grilla["dia"] = [d.day for d in grilla["fecha"]]
    grilla["fecha_txt"] = [f"{d:%d/%m/%Y}" for d in grilla["fecha"]]

    ocupadas = (grilla["estado"] == "ocupada").sum()
    k = st.columns(3)
    k[0].metric("Ocupación del mes", f"{100 * ocupadas / len(grilla):.0f} %")
    k[1].metric("Noches ocupadas", int(ocupadas))
    k[2].metric("Estadías en el mes", len(res))

    colores = {"ocupada": TINTA, "libre": "rgba(140,127,110,.18)", "mantenimiento": PALISANDRO}
    clic = alt.selection_point(name="celda", fields=["habitacion", "dia"])
    mapa = alt.Chart(grilla.drop(columns=["fecha"])).mark_rect(stroke="white", strokeWidth=1).encode(
        x=alt.X("dia:O", title=f"{meses[mes - 1].capitalize()} {anio}", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("habitacion:N", title="Habitación", sort=list(habs["habitacion"])),
        color=alt.Color("estado:N", scale=alt.Scale(domain=list(colores), range=list(colores.values())),
                        legend=alt.Legend(title=None, orient="bottom")),
        tooltip=[alt.Tooltip("habitacion", title="Habitación"), alt.Tooltip("fecha_txt", title="Fecha"),
                 alt.Tooltip("estado", title="Estado"), alt.Tooltip("detalle", title="Detalle")],
        opacity=alt.condition(clic, alt.value(1), alt.value(0.55)),
    ).add_params(clic).properties(height=26 * len(habs))
    st.caption("Haz clic en una celda ocupada para ver la reserva.")
    evento = st.altair_chart(mapa, on_select="rerun", key="mapa_celdas")
    celda = seleccion(evento, "celda")
    if celda:
        fila = grilla[(grilla["habitacion"] == str(celda["habitacion"])) & (grilla["dia"] == int(celda["dia"]))]
        if len(fila) and fila.iloc[0]["estado"] == "ocupada":
            num = int(fila.iloc[0]["detalle"].split(":")[0].replace("Reserva", "").strip())
            info = consultar("""
                SELECT r.re_id_reserva AS reserva, hu.hd_nombre AS huesped, hu.hd_pais AS pais,
                       r.re_fecha_entrada AS entrada, r.re_fecha_salida AS salida, r.re_noches AS noches,
                       r.re_num_personas AS personas, r.re_canal AS canal, r.re_valor_total AS valor,
                       r.re_estado AS estado
                FROM reserva r JOIN huesped hu ON hu.hd_id_huesped = r.re_id_huesped
                WHERE r.re_id_reserva = :id""", {"id": num})
            st.markdown(f"**Habitación {celda['habitacion']}, día {int(celda['dia'])}**")
            tabla(info, dinero=["valor"], fechas=["entrada", "salida"])
        elif len(fila):
            st.info(f"La habitación {celda['habitacion']} está {fila.iloc[0]['estado']} ese día.")
