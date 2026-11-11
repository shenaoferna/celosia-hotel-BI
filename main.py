"""
Hotel Celosía: app de gestión de reservas y análisis (Streamlit + Oracle).

Ejecución:     streamlit run main.py
Credenciales:  .streamlit/secrets.toml, sección [oracle]
    user, password, dsn, config_dir, wallet_password   -> modo thin (sin Instant Client)
    lib_dir                                            -> opcional, modo thick (Instant Client)

Estructura del código:
    main.py           arranque, navegación y manejo general de errores
    config.py         identidad del hotel, colores y parámetros de negocio
    conexion.py       conexión centralizada a Oracle y transacciones
    interfaz.py       componentes visuales compartidos
    reglas.py         reglas de negocio que valida la aplicación
    paginas/          una página de la app por archivo
"""
import oracledb
import streamlit as st

st.set_page_config(page_title="Celosía Hotel Boutique", page_icon="🏛️", layout="wide")

from config import HOTEL, HOY
from conexion import get_pool, mensaje_error
from interfaz import aplicar_estilo, encabezado_marca
from paginas.clientes import clientes
from paginas.consultas_sql import consultas_sql
from paginas.desempeno import desempeno
from paginas.habitaciones import habitaciones
from paginas.huespedes import huespedes
from paginas.mapa import mapa_ocupacion
from paginas.nueva_reserva import nueva_reserva
from paginas.reservas import reservas
from paginas.resumen import inicio
from paginas.temporadas import temporadas

aplicar_estilo()

# Sin conexión no hay app: se muestra un mensaje claro en lugar del error técnico.
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

# Cualquier error de Oracle que no se haya manejado en una página llega aquí y se muestra con un mensaje claro.
try:
    pg.run()
except oracledb.Error as e:
    st.error(mensaje_error(e))
