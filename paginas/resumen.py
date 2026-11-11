"""Página Resumen del día: indicadores, el edificio piso por piso, recepción e ingresos por mes."""

import datetime as dt
import html

import altair as alt
import pandas as pd
import streamlit as st

from config import CANALES, HOY, LATON, NOTA_CARTERA, TINTA
from conexion import consultar, valor
from interfaz import barras, pesos, seleccion, tabla, titulo
from reglas import hacer_checkin, hacer_checkout, mismo_dia_anio_anterior


def mover_dia(dias):
    st.session_state.dia_resumen = st.session_state.dia_resumen + dt.timedelta(days=dias)


def ir_a_hoy():
    st.session_state.dia_resumen = HOY


def recepcion_de_hoy():
    """Lista de llegadas y salidas pendientes, con su botón. Solo tiene sentido para el día de hoy."""
    base = """SELECT r.re_id_reserva AS reserva, h.ha_numero AS habitacion, hu.hd_nombre AS huesped,
                     r.re_fecha_entrada AS entrada, r.re_fecha_salida AS salida, r.re_num_personas AS personas,
                     r.re_hora_checkin AS checkin
              FROM reserva r JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
              JOIN huesped hu ON hu.hd_id_huesped = r.re_id_huesped """
    por_llegar = consultar(base + """WHERE r.re_estado = 'confirmada' AND r.re_fecha_entrada <= :h
                                     AND r.re_fecha_salida > :h ORDER BY r.re_fecha_entrada, h.ha_numero""", {"h": HOY})
    por_salir = consultar(base + """WHERE r.re_estado = 'en_curso' AND r.re_fecha_salida <= :h
                                    ORDER BY r.re_fecha_salida, h.ha_numero""", {"h": HOY})
    st.subheader("Recepción de hoy")
    izq, der = st.columns(2)
    with izq:
        st.markdown(f"**Check-in pendientes ({len(por_llegar)})**")
        if por_llegar.empty:
            st.caption("No hay huéspedes por llegar.")
        for r in por_llegar.itertuples():
            ent = pd.to_datetime(r.entrada).date()
            atraso = f", debía llegar el {ent:%d/%m}" if ent < HOY else ""
            a, b = st.columns([3, 1.3], vertical_alignment="center")
            a.markdown(f"**{r.habitacion}** {r.huesped}, {r.personas} persona(s){atraso}")
            b.button("Check-in", key=f"in_{r.reserva}", on_click=hacer_checkin, args=(r.reserva,), type="primary")
    with der:
        st.markdown(f"**Check-out pendientes ({len(por_salir)})**")
        if por_salir.empty:
            st.caption("No hay salidas pendientes.")
        for r in por_salir.itertuples():
            sal = pd.to_datetime(r.salida).date()
            atraso = f", debía salir el {sal:%d/%m}" if sal < HOY else ""
            a, b = st.columns([3, 1.3], vertical_alignment="center")
            a.markdown(f"**{r.habitacion}** {r.huesped}{atraso}")
            b.button("Check-out", key=f"out_{r.reserva}", on_click=hacer_checkout, args=(r.reserva,))


def inicio():
    if "dia_resumen" not in st.session_state:
        st.session_state.dia_resumen = HOY

    c0, c1, c2, c3, c4 = st.columns([3.4, 1.15, 0.8, 1.6, 1.25], vertical_alignment="bottom")
    c1.button("Anterior", icon=":material/chevron_left:", on_click=mover_dia, args=(-1,))
    c2.button("Hoy", on_click=ir_a_hoy, disabled=st.session_state.dia_resumen == HOY)
    c3.date_input("Día", key="dia_resumen", format="DD/MM/YYYY", label_visibility="collapsed")
    c4.button("Siguiente", icon=":material/chevron_right:", on_click=mover_dia, args=(1,))
    d = st.session_state.dia_resumen
    with c0:
        cuando = "hoy" if d == HOY else ("en el pasado" if d < HOY else "según las reservas confirmadas")
        dias_sem = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                 "octubre", "noviembre", "diciembre"]
        fecha_txt = f"{dias_sem[d.weekday()].capitalize()} {d.day} de {meses[d.month - 1]} de {d.year}"
        titulo("Resumen del día", f"{fecha_txt}, {cuando}.")

    # ---------- estadías que tocan el día d ----------
    estadias = consultar("""
        SELECT h.ha_numero AS habitacion, r.re_id_reserva AS reserva, hu.hd_nombre AS huesped,
               r.re_fecha_entrada AS entrada, r.re_fecha_salida AS salida, r.re_num_personas AS personas,
               r.re_noches AS noches, r.re_valor_total AS valor, r.re_canal AS canal, h.ha_tipo AS tipo,
               r.re_estado AS estado, r.re_hora_checkin AS checkin, r.re_hora_checkout AS checkout
        FROM reserva r
        JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
        JOIN huesped hu ON hu.hd_id_huesped = r.re_id_huesped
        WHERE r.re_estado <> 'cancelada' AND r.re_fecha_entrada <= :d AND r.re_fecha_salida >= :d""", {"d": d})
    for c in ("entrada", "salida"):
        estadias[c] = pd.to_datetime(estadias[c]).dt.date
    llegan = estadias[estadias["entrada"] == d]
    salen = estadias[estadias["salida"] == d]
    alojados = estadias[(estadias["entrada"] <= d) & (estadias["salida"] > d)]

    habs = consultar("""SELECT ha_numero AS habitacion, ha_piso AS piso, ha_tipo AS tipo, ha_estado AS estado
                        FROM habitacion ORDER BY ha_piso DESC, ha_numero""")
    activas = int((habs["estado"] == "activa").sum())

    def ocupacion(dia):
        n = valor("""SELECT COUNT(DISTINCT re_id_habitacion) FROM reserva WHERE re_estado <> 'cancelada'
                     AND re_fecha_entrada <= :d AND re_fecha_salida > :d""", {"d": dia})
        return 100 * n / len(habs) if len(habs) else 0

    ocup_hoy, ocup_antes = ocupacion(d), ocupacion(mismo_dia_anio_anterior(d))
    acumulado = lambda desde, hasta: valor("""SELECT SUM(re_valor_total) FROM reserva WHERE re_estado <> 'cancelada'
                                              AND re_fecha_entrada BETWEEN :a AND :b""", {"a": desde, "b": hasta})
    ytd = acumulado(dt.date(d.year, 1, 1), d)
    ytd_antes = acumulado(dt.date(d.year - 1, 1, 1), mismo_dia_anio_anterior(d))

    k = st.columns(5)
    k[0].metric("Ocupación", f"{ocup_hoy:.0f} %", f"{ocup_hoy - ocup_antes:+.0f} pts vs. {d.year - 1}")
    k[1].metric("Llegadas", len(llegan))
    k[2].metric("Salidas", len(salen))
    k[3].metric("Huéspedes alojados", int(alojados["personas"].sum()) if len(alojados) else 0)
    k[4].metric(f"Ingresos {d.year} al {d:%d/%m}", pesos(ytd),
                f"{100 * (ytd - ytd_antes) / ytd_antes:+.1f} % vs. {d.year - 1}" if ytd_antes else None)

    # ---------- el edificio, piso por piso ----------
    st.subheader("El hotel ese día")
    filas = []
    for piso, grupo in habs.groupby("piso", sort=False):
        celdas = []
        for h in grupo.itertuples():
            e_llega = llegan[llegan["habitacion"] == h.habitacion]
            e_aloja = alojados[alojados["habitacion"] == h.habitacion]
            e_sale = salen[salen["habitacion"] == h.habitacion]
            if len(e_llega) and d == HOY and e_llega.iloc[0]["estado"] == "en_curso":
                clase, quien, nota = "ocupada", e_llega.iloc[0]["huesped"], "Ya llegó"
            elif len(e_llega):
                clase, quien, nota = "llega", e_llega.iloc[0]["huesped"], "Llega"
            elif len(e_aloja):
                clase, quien, nota = "ocupada", e_aloja.iloc[0]["huesped"], "Ocupada"
            elif len(e_sale):
                clase, quien, nota = "sale", e_sale.iloc[0]["huesped"], "Sale"
            elif h.estado == "mantenimiento" and d >= HOY:
                clase, quien, nota = "mant", "", "Mantenimiento"
            else:
                clase, quien, nota = "", "", h.tipo
            ayuda = html.escape(f"{h.habitacion} · {h.tipo}" + (f" · {quien}" if quien else ""))
            primer_nombre = html.escape(quien.split()[0]) if quien else nota
            celdas.append(f'<div class="hab {clase}" title="{ayuda}"><b>{h.habitacion}</b>{primer_nombre}</div>')
        filas.append(f'<div class="piso"><span class="n">Piso {piso}</span>{"".join(celdas)}</div>')
    st.markdown('<div class="edificio">' + "".join(filas) + "</div>", unsafe_allow_html=True)
    st.markdown('<div class="leyenda"><span><i style="background:#2F6B5E"></i>Llega</span>'
                '<span><i style="background:#2F3F73"></i>Ocupada</span>'
                '<span><i style="background:#B08D57"></i>Sale (queda libre)</span>'
                '<span><i style="border:1px solid rgba(128,128,128,.5)"></i>Libre</span>'
                '<span><i style="background:repeating-linear-gradient(45deg,rgba(162,62,110,.55) 0 3px,transparent 3px 6px)"></i>'
                'Mantenimiento</span></div>', unsafe_allow_html=True)
    st.caption("Pasa el mouse sobre una habitación para ver el huésped.")

    if d == HOY:
        recepcion_de_hoy()

    t1, t2, t3 = st.tabs([f"Llegadas ({len(llegan)})", f"Salidas ({len(salen)})", f"Alojados ({len(alojados)})"])
    for pestaña, datos, nombre in ((t1, llegan, "llegadas"), (t2, salen, "salidas"), (t3, alojados, "alojados")):
        with pestaña:
            if datos.empty:
                st.caption("No hay registros para este día.")
            else:
                tabla(datos[["habitacion", "huesped", "entrada", "salida", "noches", "personas", "canal", "estado",
                             "checkin", "checkout", "valor"]],
                      dinero=["valor"], horas=["checkin", "checkout"], exportar=f"{nombre}_{d:%Y%m%d}")

    # ---------- ingresos del año: clic en un mes para ver el detalle ----------
    st.subheader(f"Ingresos de {d.year} por mes")
    st.caption("Haz clic en una barra para ver de dónde salieron los ingresos de ese mes. " + NOTA_CARTERA)
    mensual = consultar("""
        SELECT EXTRACT(MONTH FROM re_fecha_entrada) AS mes,
               SUM(CASE WHEN re_estado IN ('finalizada', 'en_curso') THEN re_valor_total ELSE 0 END) AS realizado,
               SUM(CASE WHEN re_estado = 'confirmada' THEN re_valor_total ELSE 0 END) AS en_cartera
        FROM reserva
        WHERE re_estado <> 'cancelada' AND EXTRACT(YEAR FROM re_fecha_entrada) = :y
        GROUP BY EXTRACT(MONTH FROM re_fecha_entrada) ORDER BY 1""", {"y": d.year})
    nombres_mes = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    mensual["mes"] = mensual["mes"].astype(int)
    largo = mensual.melt(id_vars="mes", value_vars=["realizado", "en_cartera"], var_name="parte", value_name="valor")
    largo["millones"] = (largo["valor"].astype(float) / 1e6).round(1)
    largo["parte"] = largo["parte"].map({"realizado": "Realizado", "en_cartera": "En cartera"})
    largo["orden"] = largo["parte"].map({"Realizado": 0, "En cartera": 1})
    largo["nombre"] = largo["mes"].map(lambda m: nombres_mes[m - 1])
    clic = alt.selection_point(name="mes_elegido", fields=["mes"])
    grafico = alt.Chart(largo).mark_bar().encode(
        x=alt.X("nombre:N", sort=nombres_mes, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("millones:Q", stack=True, title="Millones de pesos"),
        color=alt.Color("parte:N", scale=alt.Scale(domain=["Realizado", "En cartera"], range=[TINTA, LATON]),
                        legend=alt.Legend(title=None, orient="bottom")),
        order=alt.Order("orden:Q"),
        opacity=alt.condition(clic, alt.value(1), alt.value(0.35)),
        tooltip=[alt.Tooltip("nombre", title="Mes"), alt.Tooltip("parte", title="Ingreso"),
                 alt.Tooltip("millones", title="Millones")],
    ).add_params(clic)
    evento = st.altair_chart(grafico, on_select="rerun", key="grafico_meses")
    elegido = seleccion(evento, "mes_elegido")
    if elegido:
        m = int(elegido["mes"])
        ini = dt.date(d.year, m, 1)
        fin = dt.date(d.year + (m == 12), m % 12 + 1, 1)
        det = consultar("""
            SELECT r.re_canal AS canal, h.ha_tipo AS tipo, COUNT(*) AS reservas, SUM(r.re_noches) AS noches,
                   SUM(r.re_valor_total) AS ingresos
            FROM reserva r JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
            WHERE r.re_estado <> 'cancelada' AND r.re_fecha_entrada >= :a AND r.re_fecha_entrada < :b
            GROUP BY r.re_canal, h.ha_tipo""", {"a": ini, "b": fin})
        st.markdown(f"**Detalle de {nombres_mes[m - 1].lower()} {d.year}**")
        kk = st.columns(3)
        kk[0].metric("Reservas", int(det["reservas"].sum()))
        kk[1].metric("Noches vendidas", int(det["noches"].sum()))
        kk[2].metric("ADR del mes", pesos(det["ingresos"].sum() / det["noches"].sum() if det["noches"].sum() else 0))
        izq, der = st.columns(2)
        with izq:
            por_canal = det.groupby("canal", as_index=False)["ingresos"].sum().sort_values("ingresos", ascending=False)
            por_canal["millones"] = (por_canal["ingresos"].astype(float) / 1e6).round(1)
            por_canal["canal"] = por_canal["canal"].map(CANALES).fillna(por_canal["canal"])
            barras(por_canal[["canal", "millones"]], "canal", "millones", "Canal", "Millones", horizontal=True)
        with der:
            por_tipo = det.groupby("tipo", as_index=False)["ingresos"].sum().sort_values("ingresos", ascending=False)
            por_tipo["millones"] = (por_tipo["ingresos"].astype(float) / 1e6).round(1)
            barras(por_tipo[["tipo", "millones"]], "tipo", "millones", "Tipo de habitación", "Millones",
                   horizontal=True, color=LATON)
