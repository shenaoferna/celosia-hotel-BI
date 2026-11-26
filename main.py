"""
Celosía Hotel: reservation management and analytics app (Streamlit + Oracle).

Run:          streamlit run main.py
Credentials:  .streamlit/secrets.toml, [oracle] section
    user, password, dsn, config_dir, wallet_password   -> thin mode (no Instant Client)
    lib_dir                                            -> optional, thick mode (Instant Client)

Code structure:
    main.py           start-up, navigation and general error handling
    config.py         hotel identity, colors and business parameters
    db.py             single access point to Oracle and transactions
    ui.py             shared visual components
    rules.py          business rules the app validates
    risk.py           cancellation risk model (learns from the booking history)
    app_pages/        one app page per file
"""
import oracledb
import streamlit as st

st.set_page_config(page_title="Celosía Boutique Hotel", page_icon="🏛️", layout="wide")

from app_pages.cancellation_risk import cancellation_risk
from app_pages.customers import customers
from app_pages.guests import guests
from app_pages.new_reservation import new_reservation
from app_pages.occupancy_map import occupancy_map
from app_pages.performance import performance
from app_pages.reservations import reservations
from app_pages.rooms import rooms
from app_pages.seasons import seasons
from app_pages.sql_queries import sql_queries
from app_pages.today import today
from config import HOTEL, TODAY
from db import error_message, get_pool
from ui import apply_style, brand_header

apply_style()

# Without a connection there's no app: show a clear message instead of the technical error.
try:
    get_pool()
except Exception as e:
    st.error(f"Couldn't connect to Oracle. Check .streamlit/secrets.toml and the wallet.\n\n{e}")
    st.stop()

pg = st.navigation({
    "Front desk": [
        st.Page(today, title="Today", icon=":material/dashboard:", default=True),
        st.Page(new_reservation, title="New reservation", icon=":material/add_circle:"),
        st.Page(reservations, title="Reservations", icon=":material/event_note:"),
        st.Page(cancellation_risk, title="Cancellation risk", icon=":material/query_stats:"),
        st.Page(guests, title="Guests", icon=":material/group:"),
    ],
    "Hotel": [
        st.Page(occupancy_map, title="Occupancy map", icon=":material/grid_view:"),
        st.Page(rooms, title="Rooms", icon=":material/bed:"),
        st.Page(seasons, title="Seasons", icon=":material/calendar_month:"),
    ],
    "Analytics": [
        st.Page(performance, title="Performance", icon=":material/insights:"),
        st.Page(customers, title="Customers", icon=":material/favorite:"),
        st.Page(sql_queries, title="SQL queries", icon=":material/terminal:"),
    ],
})

with st.sidebar:
    st.markdown(f'<p class="sidebar-brand">{HOTEL}</p>'
                '<p class="sidebar-text">23 rooms on 7 floors, with the Celosía Suite on the top floor.</p>',
                unsafe_allow_html=True)
    st.divider()
    st.caption(f"Signed in as {st.secrets['oracle']['user']} · {TODAY:%b %d, %Y}")

brand_header()

# Any Oracle error a page didn't handle ends up here and is shown with a clear message.
try:
    pg.run()
except oracledb.Error as e:
    st.error(error_message(e))
