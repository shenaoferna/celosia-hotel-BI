"""
Hotel Celosía: app de gestión de reservas y análisis (Streamlit + Oracle).
"""
import datetime as dt
import html
import io
import re
from contextlib import contextmanager

import altair as alt
import oracledb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Celosía Hotel Boutique", page_icon="🏛️", layout="wide")

# ---------- Identidad de marca ----------
HOTEL = "Celosía"
DESCRIPCION_HOTEL = "Hotel boutique en Cartagena de Indias, a cinco minutos de la ciudad amurallada"
LEMA = "La brisa entra, el ruido se queda afuera."
# La celosía es la reja de madera de los balcones coloniales: deja pasar el aire y protege la intimidad.

HOY = dt.date.today()
# Paleta inspirada en la ciudad amurallada
TINTA = "#2F3F73"        # añil de las puertas coloniales (color principal)
LATON = "#B08D57"        # latón de aldabas y herrajes
SALVIA = "#2F6B5E"       # verde de balcón
PALISANDRO = "#A23E6E"   # buganvilla
PIEDRA = "#8C7F6E"       # piedra coralina de la muralla
COLOR_ESTADO = {"confirmada": LATON, "en_curso": SALVIA, "finalizada": TINTA, "cancelada": PALISANDRO}
ESTADOS = ["confirmada", "en_curso", "finalizada", "cancelada"]
# Ciclo de vida: confirmada --check-in--> en_curso --check-out--> finalizada ; confirmada --cancelar--> cancelada
CANALES = {"directo": "Directo (web o teléfono del hotel)", "booking": "Booking / OTA", "agencia": "Agencia de viajes",
           "walk_in": "Llegó sin reserva (walk-in)"}
# Supuestos de negocio (no están en la base): comisión que cobra cada canal sobre el valor de la reserva
COMISION = {"directo": 0.0, "walk_in": 0.0, "booking": 0.18, "agencia": 0.12}

# ================================================================
# 0. ESTILO (tipografía de títulos + detalles en color latón)
# ================================================================
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


# ================================================================
# 1. CONEXIÓN A ORACLE (pool de conexiones)
# ================================================================
@st.cache_resource
def get_pool():
    s = st.secrets["oracle"]
    if "lib_dir" in s:   # modo thick (Instant Client)
        oracledb.init_oracle_client(lib_dir=s["lib_dir"], config_dir=s["config_dir"])
        return oracledb.create_pool(user=s["user"], password=s["password"], dsn=s["dsn"], min=1, max=4)
    return oracledb.create_pool(   # modo thin: el wallet se entrega como parámetros
        user=s["user"], password=s["password"], dsn=s["dsn"], min=1, max=4,
        config_dir=s["config_dir"], wallet_location=s.get("wallet_location", s["config_dir"]),
        wallet_password=s["wallet_password"])


def consultar(sql, params=None):
    """SELECT -> DataFrame (columnas en minúscula)."""
    with get_pool().acquire() as con:
        cur = con.cursor()
        cur.execute(sql, params or {})
        columnas = [d[0].lower() for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columnas)


def valor(sql, params=None):
    """SELECT que devuelve un solo número."""
    df = consultar(sql, params)
    v = df.iat[0, 0] if len(df) else None
    return 0 if v is None or pd.isna(v) else v


@contextmanager
def transaccion():
    """INSERT/UPDATE: si todo sale bien COMMIT, si algo falla ROLLBACK."""
    con = get_pool().acquire()
    try:
        yield con.cursor()
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ================================================================
# 2. AYUDAS DE FORMATO
# ================================================================
def pesos(v):
    try:
        return "$ " + f"{float(v):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$ 0"


def edad(nacimiento, ref=HOY):
    return ref.year - nacimiento.year - ((ref.month, ref.day) < (nacimiento.month, nacimiento.day))


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


# Ingreso realizado = estadías finalizadas o en curso. En cartera = reservas confirmadas que todavía no ocurren.
REALIZADO = "SUM(CASE WHEN {a}re_estado IN ('finalizada', 'en_curso') THEN {a}re_valor_total ELSE 0 END)"
EN_CARTERA = "SUM(CASE WHEN {a}re_estado = 'confirmada' THEN {a}re_valor_total ELSE 0 END)"
NOTA_CARTERA = ("Realizado: estadías finalizadas o en curso. En cartera: reservas confirmadas que todavía "
                "no ocurren, es decir, dinero esperado.")


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


# Formato de cada tipo de documento: el mismo que exige el CHECK ck_huesped_formato_doc del DDL
FORMATO_DOC = {
    "CC":  (r"^[0-9]{5,10}$",    "Una cédula de ciudadanía tiene solo números, entre 5 y 10 dígitos."),
    "CE":  (r"^[0-9]{4,7}$",     "Una cédula de extranjería tiene solo números, entre 4 y 7 dígitos."),
    "PAS": (r"^[A-Z0-9]{6,12}$", "Un pasaporte tiene letras y números, entre 6 y 12 caracteres, sin espacios ni símbolos."),
}


def limpiar_documento(texto):
    """Quita puntos, espacios y guiones, y pasa a mayúsculas: '1.036.654.321' -> '1036654321'."""
    return re.sub(r"[\s.\-]", "", texto or "").upper()


def huesped_por_documento(doc):
    return consultar("""SELECT hd_id_huesped, hd_nombre, hd_tipo_documento, hd_documento,
                               hd_fecha_nacimiento, hd_email, hd_telefono, hd_pais
                        FROM huesped WHERE hd_documento = :d
                        ORDER BY hd_tipo_documento""", {"d": limpiar_documento(doc)})


# ================================================================
# 3. PÁGINAS
# ================================================================
def hacer_checkin(reserva_id):
    with transaccion() as cur:
        cur.execute("""UPDATE reserva SET re_estado = 'en_curso', re_hora_checkin = :t
                       WHERE re_id_reserva = :id AND re_estado = 'confirmada'
                         AND re_fecha_entrada <= :h AND re_fecha_salida > :h""",
                    {"t": dt.datetime.now().replace(microsecond=0), "id": int(reserva_id), "h": HOY})
        ok = cur.rowcount
    st.toast(f"Check-in de la reserva {reserva_id} registrado." if ok else
             f"La reserva {reserva_id} no se pudo registrar: ya no estaba confirmada.")


def hacer_checkout(reserva_id):
    with transaccion() as cur:
        cur.execute("""UPDATE reserva SET re_estado = 'finalizada', re_hora_checkout = :t
                       WHERE re_id_reserva = :id AND re_estado = 'en_curso'""",
                    {"t": dt.datetime.now().replace(microsecond=0), "id": int(reserva_id)})
        ok = cur.rowcount
    st.toast(f"Check-out de la reserva {reserva_id} registrado." if ok else
             f"La reserva {reserva_id} no estaba en curso.")


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


def mover_dia(dias):
    st.session_state.dia_resumen = st.session_state.dia_resumen + dt.timedelta(days=dias)


def ir_a_hoy():
    st.session_state.dia_resumen = HOY


def mismo_dia_anio_anterior(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:            # 29 de febrero
        return d.replace(year=d.year - 1, day=28)


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
    mensual = consultar(f"""
        SELECT EXTRACT(MONTH FROM re_fecha_entrada) AS mes,
               {REALIZADO.format(a="")} AS realizado, {EN_CARTERA.format(a="")} AS en_cartera
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


def nueva_reserva():
    titulo("Nueva reserva", "Busca al huésped, elige fechas y la app te muestra solo las habitaciones que sirven.")

    # ---- Paso 1: huésped ----
    st.subheader("1. Huésped")
    doc = st.text_input("Número de documento", placeholder="Ej: 1036654321")
    if not doc.strip():
        st.caption("Si el huésped es nuevo, regístralo primero en la página Huéspedes.")
        return
    g = huesped_por_documento(doc)
    if g.empty:
        st.warning("No hay ningún huésped con ese documento. Regístralo en la página Huéspedes y vuelve aquí.")
        return
    if len(g) > 1:     # el mismo número con dos tipos de documento distintos (por ejemplo, CC y PAS)
        tipos = list(g["hd_tipo_documento"])
        g = g[g["hd_tipo_documento"] == st.radio("Hay más de un huésped con ese número. ¿Qué tipo de documento es?",
                                                 tipos, horizontal=True)]
    g = g.iloc[0]
    nacimiento = pd.to_datetime(g["hd_fecha_nacimiento"]).date() if pd.notna(g["hd_fecha_nacimiento"]) else None
    años = edad(nacimiento) if nacimiento else None
    st.success(f"**{g['hd_nombre']}** · {g['hd_tipo_documento']} {g['hd_documento']} · {g['hd_pais']}"
               + (f" · {años} años" if años is not None else ""))
    if años is not None and años < 18:     # el huésped debe ser mayor de edad
        st.error("El huésped es menor de edad. Solo un adulto puede hacer la reserva.")
        return

    # ---- Paso 2: fechas y personas ----
    st.subheader("2. Fechas y personas")
    c1, c2, c3 = st.columns(3)
    entrada = c1.date_input("Entrada", value=HOY, min_value=HOY, format="DD/MM/YYYY")
    salida = c2.date_input("Salida", value=entrada + dt.timedelta(days=1), min_value=HOY, format="DD/MM/YYYY")
    personas = c3.number_input("Personas", min_value=1, max_value=6, value=1)
    canal = st.selectbox("¿Por dónde llegó la reserva?", list(CANALES), format_func=CANALES.get,
                         index=3 if entrada == HOY else 0)
    noches = (salida - entrada).days
    if noches <= 0:
        st.error("La fecha de salida debe ser posterior a la de entrada.")
        return

    # La temporada la define la fecha de entrada
    temp = consultar("""SELECT tp_id_temporada, tp_nombre, tp_recargo FROM temporada
                        WHERE :e BETWEEN tp_fecha_inicio AND tp_fecha_fin""", {"e": entrada})
    if temp.empty:
        st.error("No hay una temporada creada para esa fecha de entrada. Créala en la página Temporadas.")
        return
    temp = temp.iloc[0]
    recargo = float(temp["tp_recargo"])
    st.caption(f"Temporada: **{temp['tp_nombre']}** · recargo {recargo:.0f} % · {noches} noche(s)")

    # ---- Paso 3: habitaciones disponibles (activas, con capacidad y sin cruces de fechas) ----
    st.subheader("3. Habitaciones disponibles")
    libres = consultar("""
        SELECT h.ha_id_habitacion, h.ha_numero, h.ha_tipo, h.ha_capacidad, h.ha_piso, h.ha_precio_noche
        FROM habitacion h
        WHERE h.ha_estado = 'activa'
          AND h.ha_capacidad >= :p
          AND NOT EXISTS (SELECT 1 FROM reserva r
                          WHERE r.re_id_habitacion = h.ha_id_habitacion
                            AND r.re_estado <> 'cancelada'
                            AND r.re_fecha_entrada < :s
                            AND r.re_fecha_salida  > :e)
        ORDER BY h.ha_precio_noche, h.ha_numero""", {"p": personas, "s": salida, "e": entrada})
    if libres.empty:
        st.warning("No hay habitaciones libres con esa capacidad en esas fechas. Prueba otras fechas o menos personas.")
        return
    # Valor total = precio × noches × (1 + recargo/100)
    libres["valor_total"] = (libres["ha_precio_noche"].astype(float) * noches * (1 + recargo / 100)).round(2)

    opciones = {f"{r.ha_numero} · {r.ha_tipo} · hasta {r.ha_capacidad} personas · piso {r.ha_piso} · {pesos(r.valor_total)}": r
                for r in libres.itertuples()}
    elegida = opciones[st.radio("Elige una habitación", list(opciones))]

    # ---- Paso 4: confirmar ----
    st.subheader("4. Confirmar")
    k = st.columns(4)
    k[0].metric("Habitación", elegida.ha_numero)
    k[1].metric("Precio por noche", pesos(elegida.ha_precio_noche))
    k[2].metric("Noches", noches)
    k[3].metric("Valor total", pesos(elegida.valor_total))

    if st.button("Confirmar reserva", type="primary"):
        try:
            with transaccion() as cur:
                # se vuelve a revisar justo antes de guardar, por si alguien la tomó mientras tanto
                cur.execute("""SELECT COUNT(*) FROM reserva
                               WHERE re_id_habitacion = :ha AND re_estado <> 'cancelada'
                                 AND re_fecha_entrada < :s AND re_fecha_salida > :e""",
                            {"ha": int(elegida.ha_id_habitacion), "s": salida, "e": entrada})
                if cur.fetchone()[0] > 0:
                    raise ValueError("La habitación se acaba de ocupar en esas fechas. Elige otra.")
                nuevo_id = cur.var(oracledb.NUMBER)
                cur.execute("""
                    INSERT INTO reserva (re_id_huesped, re_id_habitacion, re_id_temporada, re_fecha_reserva,
                                         re_fecha_entrada, re_fecha_salida, re_noches, re_num_personas,
                                         re_valor_total, re_estado, re_canal)
                    VALUES (:hu, :ha, :tp, :fr, :e, :s, :n, :p, :v, 'confirmada', :c)
                    RETURNING re_id_reserva INTO :nid""",
                    {"hu": int(g["hd_id_huesped"]), "ha": int(elegida.ha_id_habitacion),
                     "tp": int(temp["tp_id_temporada"]), "fr": HOY, "e": entrada, "s": salida,
                     "n": noches, "p": int(personas), "v": float(elegida.valor_total), "c": canal, "nid": nuevo_id})
                numero = int(nuevo_id.getvalue()[0])
            st.success(f"Reserva confirmada. Número de reserva: **{numero}**.")
        except ValueError as e:
            st.error(str(e))
        except oracledb.IntegrityError:
            st.error("Esa habitación ya tiene una reserva (aunque esté cancelada) con la misma fecha de entrada. "
                     "Elige otra habitación o cambia la fecha de entrada.")
        except oracledb.DatabaseError as e:
            st.error(f"Oracle rechazó la reserva: {e}")


def huespedes():
    titulo("Huéspedes", "Registra huéspedes nuevos o consulta el historial de uno existente.")
    registrar, buscar = st.tabs(["Registrar huésped", "Buscar e historial"])

    with registrar:
        with st.form("form_huesped", clear_on_submit=False):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre completo *")
            pais = c2.text_input("País *", value="Colombia")
            c3, c4 = st.columns(2)
            tipo = c3.selectbox("Tipo de documento *", ["CC", "CE", "PAS"],
                                format_func={"CC": "CC · Cédula de ciudadanía", "CE": "CE · Cédula de extranjería",
                                             "PAS": "PAS · Pasaporte"}.get)
            documento = c4.text_input("Número de documento *", help="Puedes escribirlo con puntos o espacios; la app los quita.")
            # Fecha de nacimiento con tres listas. Solo se ofrecen años de personas entre 18 y 100 años.
            # (Quien nació en HOY.year - 18 puede no haber cumplido aún: eso lo revisa la validación de edad.)
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                     "octubre", "noviembre", "diciembre"]
            anios = list(range(HOY.year - 18, HOY.year - 101, -1))
            d1, d2, d3 = st.columns(3)
            dia_n = d1.selectbox("Día de nacimiento *", range(1, 32), index=0)
            mes_n = d2.selectbox("Mes de nacimiento *", range(1, 13), index=0, format_func=lambda m: meses[m - 1])
            anio_n = d3.selectbox("Año de nacimiento *", anios, index=anios.index(1990))
            c6, c7 = st.columns(2)
            email = c6.text_input("Email (opcional)")
            telefono = c7.text_input("Teléfono *", placeholder="+57 300 123 4567")
            guardar = st.form_submit_button("Registrar huésped", type="primary")

        if guardar:
            errores = []
            try:
                nacimiento = dt.date(anio_n, mes_n, dia_n)
            except ValueError:                      # por ejemplo, 31 de febrero
                nacimiento = None
                errores.append(f"La fecha {dia_n} de {meses[mes_n - 1]} de {anio_n} no existe.")
            documento = limpiar_documento(documento)
            if not nombre.strip() or not documento or not telefono.strip() or not pais.strip():
                errores.append("Completa todos los campos marcados con *.")
            patron, mensaje = FORMATO_DOC[tipo]
            if documento and not re.fullmatch(patron, documento):
                errores.append(mensaje)
            if nacimiento and edad(nacimiento) < 18:
                errores.append(f"El huésped tiene {edad(nacimiento)} años. Debe ser mayor de edad para registrarse.")
            if documento and valor("SELECT COUNT(*) FROM huesped WHERE hd_tipo_documento = :t AND hd_documento = :d",
                                   {"t": tipo, "d": documento}):
                errores.append(f"Ya existe un huésped con {tipo} {documento}.")
            if email.strip() and valor("SELECT COUNT(*) FROM huesped WHERE LOWER(hd_email) = LOWER(:m)", {"m": email.strip()}):
                errores.append("Ese email ya está registrado por otro huésped.")
            if errores:
                for e in errores:
                    st.error(e)
            else:
                try:
                    with transaccion() as cur:
                        nuevo_id = cur.var(oracledb.NUMBER)
                        cur.execute("""
                            INSERT INTO huesped (hd_nombre, hd_tipo_documento, hd_documento, hd_fecha_nacimiento,
                                                 hd_email, hd_telefono, hd_pais)
                            VALUES (:n, :t, :d, :f, :m, :tel, :p)
                            RETURNING hd_id_huesped INTO :nid""",
                            {"n": nombre.strip(), "t": tipo, "d": documento, "f": nacimiento,
                             "m": email.strip() or None, "tel": telefono.strip(), "p": pais.strip(), "nid": nuevo_id})
                        nid = int(nuevo_id.getvalue()[0])
                    st.success(f"Huésped registrado con el código {nid}. Ya puedes crear su reserva.")
                except oracledb.DatabaseError as e:
                    st.error(f"Oracle rechazó el registro: {e}")

    with buscar:
        q = st.text_input("Nombre o documento", placeholder="Ej: Restrepo o 1036654321")
        if len(q.strip()) < 3:
            st.caption("Escribe al menos 3 caracteres.")
            return
        encontrados = consultar("""
            SELECT hd_id_huesped AS codigo, hd_nombre AS nombre, hd_tipo_documento AS tipo,
                   hd_documento AS documento, hd_pais AS pais, hd_email AS email, hd_telefono AS telefono
            FROM huesped
            WHERE hd_documento = :d OR UPPER(hd_nombre) LIKE UPPER(:q)
            ORDER BY hd_nombre FETCH FIRST 50 ROWS ONLY""", {"d": limpiar_documento(q), "q": f"%{q.strip()}%"})
        if encontrados.empty:
            st.info("No se encontró ningún huésped con ese nombre o documento.")
            return
        tabla(encontrados)
        opciones = dict(zip(encontrados["nombre"] + " · " + encontrados["documento"], encontrados["codigo"]))
        codigo = int(opciones[st.selectbox("Ver historial de", list(opciones))])
        hist = consultar("""
            SELECT r.re_id_reserva AS reserva, r.re_fecha_entrada AS entrada, r.re_fecha_salida AS salida,
                   h.ha_numero AS habitacion, h.ha_tipo AS tipo, r.re_noches AS noches,
                   r.re_valor_total AS valor, r.re_estado AS estado
            FROM reserva r JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
            WHERE r.re_id_huesped = :c
            ORDER BY r.re_fecha_entrada DESC""", {"c": codigo})
        validas = hist[hist["estado"] != "cancelada"]
        k = st.columns(3)
        k[0].metric("Estadías", len(validas))
        k[1].metric("Noches", int(validas["noches"].sum()) if len(validas) else 0)
        k[2].metric("Total gastado", pesos(validas["valor"].sum() if len(validas) else 0))
        if len(hist):
            tabla(hist, dinero=["valor"], fechas=["entrada", "salida"], exportar=f"historial_{codigo}")
        else:
            st.info("Este huésped todavía no tiene reservas.")


def reservas():
    titulo("Reservas", "Busca una reserva y gestiónala: check-in, check-out, cambios de fechas o habitación y cancelación.")

    c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
    rango = c1.date_input("Entrada entre", value=(HOY - dt.timedelta(days=30), HOY + dt.timedelta(days=60)),
                          format="DD/MM/YYYY")
    estados = c2.multiselect("Estado", ESTADOS, default=["confirmada", "en_curso"])
    hab = c3.text_input("Habitación", placeholder="402")
    q = c4.text_input("Huésped (nombre o documento)")
    if not isinstance(rango, tuple) or len(rango) != 2:
        st.caption("Elige la fecha final del rango.")
        return

    sql = """SELECT r.re_id_reserva AS reserva, hu.hd_nombre AS huesped, hu.hd_documento AS documento,
                    h.ha_numero AS habitacion, h.ha_tipo AS tipo, t.tp_nombre AS temporada,
                    r.re_fecha_entrada AS entrada, r.re_fecha_salida AS salida, r.re_noches AS noches,
                    r.re_num_personas AS personas, r.re_valor_total AS valor, r.re_estado AS estado,
                    r.re_canal AS canal, r.re_calificacion AS calificacion,
                    r.re_hora_checkin AS checkin, r.re_hora_checkout AS checkout
             FROM reserva r
             JOIN huesped hu   ON hu.hd_id_huesped = r.re_id_huesped
             JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
             JOIN temporada t  ON t.tp_id_temporada = r.re_id_temporada
             WHERE r.re_fecha_entrada BETWEEN :desde AND :hasta"""
    params = {"desde": rango[0], "hasta": rango[1]}
    if estados:   # una variable bind por estado: :e0, :e1, ...
        sql += " AND r.re_estado IN (" + ", ".join(f":e{i}" for i in range(len(estados))) + ")"
        params.update({f"e{i}": e for i, e in enumerate(estados)})
    if hab.strip():
        sql += " AND h.ha_numero = :hab"
        params["hab"] = hab.strip()
    if q.strip():
        sql += " AND (hu.hd_documento = :q OR UPPER(hu.hd_nombre) LIKE UPPER(:ql))"
        params.update({"q": limpiar_documento(q), "ql": f"%{q.strip()}%"})
    sql += " ORDER BY r.re_fecha_entrada DESC FETCH FIRST 500 ROWS ONLY"
    df = consultar(sql, params)

    k = st.columns(3)
    k[0].metric("Reservas encontradas", len(df))
    k[1].metric("Noches", int(df["noches"].sum()) if len(df) else 0)
    k[2].metric("Valor (sin canceladas)", pesos(df.loc[df["estado"] != "cancelada", "valor"].sum() if len(df) else 0))
    if df.empty:
        st.info("Ninguna reserva cumple esos filtros.")
    else:
        tabla(df, dinero=["valor"], fechas=["entrada", "salida"], horas=["checkin", "checkout"], exportar="reservas")

    st.subheader("Gestionar una reserva")
    num = st.number_input("Número de reserva", min_value=1, step=1, value=None, placeholder="Ej: 2581")
    if num is None:
        return
    r = consultar("""SELECT r.re_id_reserva, r.re_estado, r.re_fecha_entrada, r.re_fecha_salida, r.re_num_personas,
                            r.re_id_habitacion, r.re_valor_total, r.re_calificacion, r.re_hora_checkin,
                            r.re_hora_checkout, hu.hd_nombre, h.ha_numero
                     FROM reserva r JOIN huesped hu ON hu.hd_id_huesped = r.re_id_huesped
                     JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
                     WHERE r.re_id_reserva = :id""", {"id": int(num)})
    if r.empty:
        st.warning("No existe una reserva con ese número.")
        return
    r = r.iloc[0]
    rid = int(num)
    sal = pd.to_datetime(r["re_fecha_salida"]).date()
    ent = pd.to_datetime(r["re_fecha_entrada"]).date()
    estado = r["re_estado"]
    hora = lambda v: pd.to_datetime(v).strftime("%d/%m/%Y %H:%M") if pd.notna(v) else "—"
    st.write(f"**{r['hd_nombre']}**, habitación {r['ha_numero']}, del {ent:%d/%m/%Y} al {sal:%d/%m/%Y}. "
             f"Estado: **{estado}**.")
    if estado in ("en_curso", "finalizada"):
        st.caption(f"Check-in: {hora(r['re_hora_checkin'])}   Check-out: {hora(r['re_hora_checkout'])}")

    if estado == "cancelada":
        st.caption("Las reservas canceladas no cambian de estado.")
        return

    if estado == "finalizada":
        if pd.notna(r["re_calificacion"]):
            st.caption(f"Calificación del huésped: {int(r['re_calificacion'])} / 5")
            return
        nota = st.select_slider("Calificación del huésped", options=[1, 2, 3, 4, 5], value=4)
        if st.button("Guardar calificación", type="primary"):
            with transaccion() as cur:
                cur.execute("""UPDATE reserva SET re_calificacion = :c
                               WHERE re_id_reserva = :id AND re_estado = 'finalizada'""", {"c": nota, "id": rid})
            st.success(f"Calificación {nota} / 5 guardada.")
        return

    if estado == "en_curso":
        if sal > HOY:
            st.info(f"El huésped tiene la habitación hasta el {sal:%d/%m}. Si sale antes, la estadía se cobra completa.")
        st.button("Registrar check-out", type="primary", on_click=hacer_checkout, args=(rid,))
        return

    # ---- confirmada: check-in, cancelar o modificar ----
    b1, b2 = st.columns(2)
    puede_entrar = ent <= HOY < sal
    b1.button("Registrar check-in", type="primary", disabled=not puede_entrar, on_click=hacer_checkin, args=(rid,),
              help=None if puede_entrar else f"El check-in se habilita desde el {ent:%d/%m/%Y}.")
    if b2.button("Cancelar reserva"):
        with transaccion() as cur:
            cur.execute("UPDATE reserva SET re_estado = 'cancelada' WHERE re_id_reserva = :id AND re_estado = 'confirmada'",
                        {"id": rid})
            ok = cur.rowcount
        if ok:
            st.success(f"Reserva {rid} cancelada.")
        else:
            st.warning("La reserva ya no estaba confirmada.")
        return

    with st.expander("Modificar fechas, personas o habitación"):
        modificar_reserva(rid, ent, sal, int(r["re_num_personas"]), int(r["re_id_habitacion"]), float(r["re_valor_total"]))


def modificar_reserva(rid, ent, sal, personas, hab_actual, valor_actual):
    """Cambia una reserva confirmada volviendo a aplicar las reglas: disponibilidad, capacidad, temporada y valor."""
    c1, c2, c3 = st.columns(3)
    n_ent = c1.date_input("Nueva entrada", value=max(ent, HOY), min_value=HOY, format="DD/MM/YYYY", key=f"m_ent_{rid}")
    n_sal = c2.date_input("Nueva salida", value=max(sal, n_ent + dt.timedelta(days=1)), format="DD/MM/YYYY",
                          key=f"m_sal_{rid}")
    n_per = c3.number_input("Personas", min_value=1, max_value=6, value=personas, key=f"m_per_{rid}")
    noches = (n_sal - n_ent).days
    if noches <= 0:
        st.error("La fecha de salida debe ser posterior a la de entrada.")
        return
    temp = consultar("""SELECT tp_id_temporada, tp_nombre, tp_recargo FROM temporada
                        WHERE :e BETWEEN tp_fecha_inicio AND tp_fecha_fin""", {"e": n_ent})
    if temp.empty:
        st.error("No hay una temporada creada para esa fecha de entrada. Créala en la página Temporadas.")
        return
    temp = temp.iloc[0]
    recargo = float(temp["tp_recargo"])
    # habitaciones libres en las nuevas fechas, sin contar esta misma reserva
    libres = consultar("""
        SELECT h.ha_id_habitacion, h.ha_numero, h.ha_tipo, h.ha_capacidad, h.ha_precio_noche
        FROM habitacion h
        WHERE h.ha_estado = 'activa' AND h.ha_capacidad >= :p
          AND NOT EXISTS (SELECT 1 FROM reserva r
                          WHERE r.re_id_habitacion = h.ha_id_habitacion AND r.re_estado <> 'cancelada'
                            AND r.re_id_reserva <> :id
                            AND r.re_fecha_entrada < :s AND r.re_fecha_salida > :e)
        ORDER BY CASE WHEN h.ha_id_habitacion = :actual THEN 0 ELSE 1 END, h.ha_precio_noche""",
        {"p": n_per, "id": rid, "s": n_sal, "e": n_ent, "actual": hab_actual})
    if libres.empty:
        st.warning("No hay habitaciones libres con esa capacidad en esas fechas.")
        return
    libres["valor_total"] = (libres["ha_precio_noche"].astype(float) * noches * (1 + recargo / 100)).round(2)
    opciones = {f"{x.ha_numero} ({x.ha_tipo}, hasta {x.ha_capacidad}): {pesos(x.valor_total)}"
                + ("  · actual" if x.ha_id_habitacion == hab_actual else ""): x for x in libres.itertuples()}
    elegida = opciones[st.selectbox("Habitación", list(opciones), key=f"m_hab_{rid}")]
    k = st.columns(3)
    k[0].metric("Temporada", temp["tp_nombre"])
    k[1].metric("Noches", noches)
    k[2].metric("Nuevo valor", pesos(elegida.valor_total), f"{pesos(elegida.valor_total - valor_actual)} de diferencia",
                delta_color="off")
    if st.button("Guardar cambios", type="primary", key=f"m_ok_{rid}"):
        try:
            with transaccion() as cur:
                cur.execute("""SELECT COUNT(*) FROM reserva WHERE re_id_habitacion = :ha AND re_estado <> 'cancelada'
                               AND re_id_reserva <> :id AND re_fecha_entrada < :s AND re_fecha_salida > :e""",
                            {"ha": int(elegida.ha_id_habitacion), "id": rid, "s": n_sal, "e": n_ent})
                if cur.fetchone()[0] > 0:
                    raise ValueError("La habitación se acaba de ocupar en esas fechas. Elige otra.")
                cur.execute("""UPDATE reserva
                               SET re_fecha_entrada = :e, re_fecha_salida = :s, re_noches = :n, re_num_personas = :p,
                                   re_id_habitacion = :ha, re_id_temporada = :tp, re_valor_total = :v
                               WHERE re_id_reserva = :id AND re_estado = 'confirmada'""",
                            {"e": n_ent, "s": n_sal, "n": noches, "p": int(n_per), "ha": int(elegida.ha_id_habitacion),
                             "tp": int(temp["tp_id_temporada"]), "v": float(elegida.valor_total), "id": rid})
                ok = cur.rowcount
            if ok:
                st.success(f"Reserva {rid} actualizada.")
            else:
                st.warning("La reserva ya no estaba confirmada.")
        except ValueError as e:
            st.error(str(e))
        except oracledb.IntegrityError:
            st.error("Esa habitación ya tiene otra reserva (aunque esté cancelada) con la misma fecha de entrada.")


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
        with transaccion() as cur:
            cur.execute("UPDATE habitacion SET ha_estado = :e WHERE ha_id_habitacion = :id",
                        {"e": nuevo, "id": int(fila["id"])})
        st.success(f"Habitación {num} ahora está {nuevo}.")
        st.rerun()


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


def filtro_anio(clave):
    anios = [0] + [int(a) for a in consultar(
        "SELECT DISTINCT EXTRACT(YEAR FROM re_fecha_entrada) AS anio FROM reserva ORDER BY anio")["anio"]]
    anio = st.selectbox("Año", anios, format_func=lambda a: "Todos los años" if a == 0 else str(a), key=clave)
    return {"anio": anio}


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
        df = consultar(f"""
            SELECT h.ha_tipo AS tipo, COUNT(*) AS reservas, SUM(r.re_noches) AS noches,
                   {REALIZADO.format(a="r.")} AS realizado, {EN_CARTERA.format(a="r.")} AS en_cartera,
                   SUM(r.re_valor_total) AS total, ROUND(SUM(r.re_valor_total) / SUM(r.re_noches)) AS adr
            FROM reserva r JOIN habitacion h ON h.ha_id_habitacion = r.re_id_habitacion
            WHERE r.re_estado <> 'cancelada' AND (:anio = 0 OR EXTRACT(YEAR FROM r.re_fecha_entrada) = :anio)
            GROUP BY h.ha_tipo ORDER BY total DESC""", filtro)
        barras_ingresos(df, "tipo", "Tipo de habitación")
        tabla(df, dinero=["realizado", "en_cartera", "total", "adr"], nombres={"en_cartera": "en cartera", "adr": "ADR"},
              exportar="ingresos_por_tipo")
        st.caption(NOTA_CARTERA)

    with t3:
        df = consultar(f"""
            SELECT re_canal AS canal, COUNT(*) AS reservas,
                   SUM(CASE WHEN re_estado = 'cancelada' THEN 1 ELSE 0 END) AS canceladas,
                   SUM(CASE WHEN re_estado <> 'cancelada' THEN re_valor_total ELSE 0 END) AS ingresos,
                   {REALIZADO.format(a="")} AS realizado_bruto, {EN_CARTERA.format(a="")} AS cartera_bruto
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
        df = consultar(f"""
            SELECT hu.hd_nombre AS huesped, hu.hd_pais AS pais, COUNT(*) AS reservas,
                   SUM(r.re_noches) AS noches, SUM(r.re_valor_total) AS gasto,
                   ROUND(AVG(r.re_calificacion), 1) AS calificacion
            FROM reserva r JOIN huesped hu ON hu.hd_id_huesped = r.re_id_huesped
            WHERE r.re_estado <> 'cancelada' AND (:anio = 0 OR EXTRACT(YEAR FROM r.re_fecha_entrada) = :anio)
            GROUP BY hu.hd_id_huesped, hu.hd_nombre, hu.hd_pais
            ORDER BY reservas DESC, noches DESC
            FETCH FIRST {int(top)} ROWS ONLY""", filtro)
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
        df = consultar(f"""
            SELECT hu.hd_pais AS pais, COUNT(DISTINCT hu.hd_id_huesped) AS huespedes, COUNT(*) AS reservas,
                   ROUND(AVG(r.re_noches), 1) AS estadia_promedio,
                   {REALIZADO.format(a="r.")} AS realizado, {EN_CARTERA.format(a="r.")} AS en_cartera,
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


def consultas_sql():
    titulo("Consultas SQL", "Escribe tu propia consulta. Las tablas son huesped, habitacion, temporada y reserva.")
    sql = st.text_area("Consulta (sin punto y coma al final)", height=160,
                       placeholder="SELECT ha_tipo, COUNT(*) FROM habitacion GROUP BY ha_tipo")
    tipo = st.radio("Tipo", ["SELECT (leer)", "INSERT / UPDATE / DELETE (modificar)"], horizontal=True)
    if st.button("Ejecutar", type="primary") and sql.strip():
        try:
            if tipo.startswith("SELECT"):
                st.dataframe(consultar(sql.strip().rstrip(";")), hide_index=True)
            else:
                with transaccion() as cur:
                    cur.execute(sql.strip().rstrip(";"))
                    n = cur.rowcount
                st.success(f"Listo, filas afectadas: {n}")
        except Exception as e:
            st.error(e)


# ================================================================
# 4. NAVEGACIÓN
# ================================================================
try:
    get_pool()
except Exception as e:
    st.error(f"No se pudo conectar a Oracle. Revisa .streamlit/secrets.toml y el wallet.\n\n{e}")
    st.stop()

pg = st.navigation({
    "Recepción": [
        st.Page(inicio, title="Resumen del día", icon=":material/dashboard:", default=True),
        st.Page(nueva_reserva, title="Nueva reserva", icon=":material/add_circle:"),
        st.Page(reservas, title="Reservas", icon=":material/event_note:"),
        st.Page(huespedes, title="Huéspedes", icon=":material/group:"),
    ],
    "Hotel": [
        st.Page(mapa_ocupacion, title="Mapa de ocupación", icon=":material/grid_view:"),
        st.Page(habitaciones, title="Habitaciones", icon=":material/bed:"),
        st.Page(temporadas, title="Temporadas", icon=":material/calendar_month:"),
    ],
    "Análisis": [
        st.Page(desempeno, title="Desempeño", icon=":material/insights:"),
        st.Page(clientes, title="Clientes", icon=":material/favorite:"),
        st.Page(consultas_sql, title="Consultas SQL", icon=":material/terminal:"),
    ],
})
with st.sidebar:
    st.markdown(f'<p class="lateral-marca">{HOTEL}</p>'
                '<p class="lateral-texto">23 habitaciones en 7 pisos, con la Suite Celosía en el último.</p>',
                unsafe_allow_html=True)
    st.divider()
    st.caption(f"Conectado como {st.secrets['oracle']['user']}, {HOY:%d/%m/%Y}")
encabezado_marca()
pg.run()
