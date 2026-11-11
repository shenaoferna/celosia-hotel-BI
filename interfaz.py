"""Componentes visuales compartidos: estilo, encabezado de marca, tablas, gráficos y exportación."""

import io

import altair as alt
import pandas as pd
import streamlit as st

from config import DESCRIPCION_HOTEL, HOTEL, HOY, LATON, LEMA, TINTA
from conexion import consultar, valor


def aplicar_estilo():
    """Tipografía y colores de la marca Celosía."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&display=swap');
    h1, h2, h3 { font-family: 'Cormorant Garamond', Georgia, serif !important; font-weight: 600 !important; letter-spacing: .005em; }
    h2, h3 { font-size: 1.55rem !important; }
    .titulo { border-left: 3px solid #B08D57; padding: 2px 0 2px 16px; margin: 0 0 1.2rem 0; }
    .titulo h1 { margin: 0; font-size: 2.1rem; line-height: 1.1; }

    /* Encabezado de marca: banda de celosía en latón sobre añil */
    .marca { position: relative; overflow: hidden; border-radius: 4px; margin: -0.5rem 0 1.6rem; color: #F4EFE6;
             background-color: #23305A; padding: 26px 30px 22px; }
    .marca::before { content: ""; position: absolute; top: 0; right: 0; bottom: 0; width: 42%;
             background-image: repeating-linear-gradient(45deg, rgba(176,141,87,.55) 0 1px, transparent 1px 15px),
                               repeating-linear-gradient(-45deg, rgba(176,141,87,.55) 0 1px, transparent 1px 15px);
             -webkit-mask-image: linear-gradient(to left, #000 35%, transparent);
                     mask-image: linear-gradient(to left, #000 35%, transparent); }
    .marca .contenido { position: relative; display: flex; justify-content: space-between; align-items: flex-end;
             gap: 24px; flex-wrap: wrap; }
    .marca .nombre { font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 600; font-size: 3.4rem;
             line-height: .95; margin: 0; color: #F4EFE6; }
    .marca .descripcion { margin: 8px 0 0; font-size: .92rem; opacity: .82; }
    .marca .lema { margin: 10px 0 0; font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic;
             font-size: 1.3rem; color: #D9BE8F; }
    .marca .hoy { text-align: right; font-size: .85rem; line-height: 1.5; }
    .marca .hoy strong { display: block; font-family: 'Cormorant Garamond', Georgia, serif; font-size: 2rem;
             font-weight: 600; color: #F4EFE6; line-height: 1; }
    @media (max-width: 640px) { .marca .nombre { font-size: 2.5rem; } .marca .hoy { text-align: left; } }
    .lateral-marca { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.5rem; font-weight: 600; margin: 0; }
    .lateral-texto { font-size: .8rem; opacity: .75; margin: 2px 0 0; }
    .titulo p { margin: 4px 0 0; opacity: .72; max-width: 70ch; }
    div[data-testid="stMetric"] { border-top: 1px solid rgba(176,141,87,.7); padding-top: 10px; }
    div[data-testid="stMetricValue"] { font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 600;
           font-variant-numeric: lining-nums tabular-nums; }
    .marca, .hab, .titulo { font-variant-numeric: lining-nums; }
    .edificio { display: flex; flex-direction: column; gap: 6px; margin: .4rem 0 .6rem; }
    .piso { display: flex; gap: 6px; align-items: stretch; flex-wrap: wrap; }
    .piso .n { width: 56px; font-size: .78rem; opacity: .65; display: flex; align-items: center; }
    .hab { min-width: 74px; padding: 7px 8px; border-radius: 6px; font-size: .74rem; line-height: 1.25;
           border: 1px solid rgba(128,128,128,.28); }
    .hab b { display: block; font-size: 1.1rem; font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 600; }
    .hab.ocupada { background: #2F3F73; color: #fff; border-color: #2F3F73; }
    .hab.llega { background: #2F6B5E; color: #fff; border-color: #2F6B5E; }
    .hab.sale { background: #B08D57; color: #fff; border-color: #B08D57; }
    .hab.mant { background: repeating-linear-gradient(45deg, rgba(162,62,110,.3) 0 6px, transparent 6px 12px); }
    .leyenda { font-size: .8rem; opacity: .8; display: flex; gap: 14px; flex-wrap: wrap; }
    .leyenda i { display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
    </style>
    """, unsafe_allow_html=True)


def encabezado_marca():
    """Nombre del hotel, lema y el pulso del día: la marca nunca aparece sin un dato de negocio al lado."""
    try:
        total = valor("SELECT COUNT(*) FROM habitacion")
        ocupadas = valor("""SELECT COUNT(DISTINCT re_id_habitacion) FROM reserva WHERE re_estado <> 'cancelada'
                            AND re_fecha_entrada <= :h AND re_fecha_salida > :h""", {"h": HOY})
        llegadas = valor("SELECT COUNT(*) FROM reserva WHERE re_estado = 'confirmada' AND re_fecha_entrada = :h", {"h": HOY})
        pulso = (f'<strong>{100 * ocupadas / total:.0f} %</strong>ocupación hoy<br>'
                 f'{int(llegadas)} {"llegada esperada" if int(llegadas) == 1 else "llegadas esperadas"}') if total else ""
    except Exception:
        pulso = ""
    st.markdown(f"""
    <div class="marca"><div class="contenido">
        <div>
            <p class="nombre">{HOTEL}</p>
            <p class="descripcion">{DESCRIPCION_HOTEL}</p>
            <p class="lema">{LEMA}</p>
        </div>
        <div class="hoy">{pulso}</div>
    </div></div>""", unsafe_allow_html=True)


def titulo(texto, descripcion=""):
    st.markdown(f'<div class="titulo"><h1>{texto}</h1><p>{descripcion}</p></div>', unsafe_allow_html=True)


def pesos(v):
    try:
        return "$ " + f"{float(v):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$ 0"


def boton_excel(df, nombre):
    """Descarga la tabla como Excel (necesita openpyxl); si no está instalado, como CSV."""
    buffer = io.BytesIO()
    try:
        df.to_excel(buffer, index=False, sheet_name="datos")
        st.download_button("Descargar Excel", buffer.getvalue(), file_name=f"celosia_{nombre}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key=f"excel_{nombre}")
    except ImportError:
        st.download_button("Descargar CSV", df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"celosia_{nombre}.csv", mime="text/csv", key=f"csv_{nombre}")


def tabla(df, dinero=(), fechas=(), nombres=None, horas=(), exportar=None):
    d = df.copy()
    for c in fechas:
        d[c] = pd.to_datetime(d[c]).dt.date
    for c in horas:
        d[c] = pd.to_datetime(d[c]).dt.strftime("%d/%m %H:%M").fillna("")
    crudo = d.rename(columns=nombres or {})          # para el Excel: los números quedan como números
    for c in dinero:
        d[c] = d[c].map(pesos)
    st.dataframe(d.rename(columns=nombres or {}), hide_index=True)
    if exportar:
        boton_excel(crudo, exportar)


def barras(df, x, y, titulo_x, titulo_y, horizontal=False, color=TINTA):
    """Gráfico de barras que respeta el orden que trae la consulta (ORDER BY de Oracle)."""
    if horizontal:
        enc = dict(y=alt.Y(f"{x}:N", sort="-x", title=titulo_x), x=alt.X(f"{y}:Q", title=titulo_y))
    else:
        enc = dict(x=alt.X(f"{x}:N", sort=None, title=titulo_x, axis=alt.Axis(labelAngle=-35)),
                   y=alt.Y(f"{y}:Q", title=titulo_y))
    st.altair_chart(alt.Chart(df).mark_bar(color=color).encode(**enc, tooltip=list(df.columns)))


def barras_ingresos(df, x, titulo_x, horizontal=False, titulo_valor="Ingresos (millones)"):
    """Barras apiladas con dos partes: lo realizado (añil) y lo que está en cartera (latón)."""
    largo = df[[x, "realizado", "en_cartera"]].melt(id_vars=x, var_name="parte", value_name="valor")
    largo["millones"] = (largo["valor"].astype(float) / 1e6).round(1)
    largo["parte"] = largo["parte"].map({"realizado": "Realizado", "en_cartera": "En cartera"})
    largo["orden"] = largo["parte"].map({"Realizado": 0, "En cartera": 1})
    orden_x = list(df[x])
    color = alt.Color("parte:N", scale=alt.Scale(domain=["Realizado", "En cartera"], range=[TINTA, LATON]),
                      legend=alt.Legend(title=None, orient="bottom"))
    if horizontal:
        enc = dict(y=alt.Y(f"{x}:N", sort=orden_x, title=titulo_x), x=alt.X("millones:Q", stack=True, title=titulo_valor))
    else:
        enc = dict(x=alt.X(f"{x}:N", sort=orden_x, title=titulo_x, axis=alt.Axis(labelAngle=-35)),
                   y=alt.Y("millones:Q", stack=True, title=titulo_valor))
    st.altair_chart(alt.Chart(largo).mark_bar().encode(
        **enc, color=color, order=alt.Order("orden:Q"),
        tooltip=[alt.Tooltip(x, title=titulo_x), alt.Tooltip("parte", title="Ingreso"), alt.Tooltip("millones", title="Millones")]))


def seleccion(evento, nombre):
    """Lee lo que el usuario hizo clic en un gráfico de Altair (on_select). Devuelve un dict o None."""
    try:
        sel = evento["selection"][nombre]
    except (KeyError, TypeError, AttributeError):
        return None
    if isinstance(sel, list) and sel:
        return sel[0]
    return None


def filtro_anio(clave):
    anios = [0] + [int(a) for a in consultar(
        "SELECT DISTINCT EXTRACT(YEAR FROM re_fecha_entrada) AS anio FROM reserva ORDER BY anio")["anio"]]
    anio = st.selectbox("Año", anios, format_func=lambda a: "Todos los años" if a == 0 else str(a), key=clave)
    return {"anio": anio}
