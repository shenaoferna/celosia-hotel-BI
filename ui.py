"""Shared visual components: style, brand header, tables, charts and Excel export."""

import io

import altair as alt
import pandas as pd
import streamlit as st

from config import CHANNEL_LABEL, GOLD, HOTEL, HOTEL_DESCRIPTION, INK, ROOM_TYPE_LABEL, STATUS_LABEL, TAGLINE, TODAY
from db import query, scalar


def apply_style():
    """Ink and antique gold palette: ink brand bar, gold accents and gold buttons, serif page titles."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,600;1,500&family=Nunito+Sans:wght@400;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0');

    /* ---------- Base ---------- */
    html, body, .stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp li {
        font-family: 'Nunito Sans', 'Segoe UI', sans-serif; }
    .stApp { background: #FAF8F4; }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 2.2rem; max-width: 1320px; }
    h1, h2, h3 { color: #1C1C1C !important; font-family: 'Nunito Sans', sans-serif !important; font-weight: 800 !important;
                 letter-spacing: -.01em; }
    h2, h3 { font-size: 1.35rem !important; }
    .ms { font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal; line-height: 1;
          display: inline-block; vertical-align: middle; -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga'; }

    /* ---------- Brand bar ---------- */
    .brand { position: relative; overflow: hidden; border-radius: 18px; margin: -0.6rem 0 1.8rem; color: #FFFFFF;
             background: #1C1C1C; padding: 26px 32px 24px; border-bottom: 6px solid #916E27; }
    .brand::before { content: ""; position: absolute; top: 0; right: 0; bottom: 0; width: 45%;
             background-image: repeating-linear-gradient(45deg, rgba(205,187,142,.35) 0 1.5px, transparent 1.5px 16px),
                               repeating-linear-gradient(-45deg, rgba(205,187,142,.35) 0 1.5px, transparent 1.5px 16px);
             -webkit-mask-image: linear-gradient(to left, #000 30%, transparent);
                     mask-image: linear-gradient(to left, #000 30%, transparent); }
    .brand .content { position: relative; display: flex; justify-content: space-between; align-items: flex-end;
             gap: 24px; flex-wrap: wrap; }
    .brand .name { font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 600; font-size: 3.4rem;
             line-height: .95; margin: 0; color: #FFFFFF; }
    .brand .description { margin: 8px 0 0; font-size: .95rem; color: #D9D4CB; }
    .brand .tagline { margin: 10px 0 0; font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic;
             font-size: 1.3rem; color: #CDBB8E; }
    .brand .today { display: flex; gap: 10px; }
    .brand .stat { background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22); border-radius: 14px;
             padding: 10px 16px; min-width: 120px; font-size: .8rem; color: #D9D4CB; }
    .brand .stat strong { display: block; font-size: 1.7rem; font-weight: 800; color: #FFFFFF; line-height: 1.1; }
    @media (max-width: 640px) { .brand .name { font-size: 2.5rem; } }

    /* ---------- Page titles ---------- */
    .page-title { border-left: 5px solid #916E27; padding: 2px 0 2px 16px; margin: 0 0 1.4rem 0; }
    .page-title h1 { margin: 0; font-size: 2.5rem; line-height: 1.1; font-family: 'Cormorant Garamond', Georgia, serif !important;
                     font-weight: 600 !important; letter-spacing: 0; }
    .page-title p { margin: 4px 0 0; color: #6B655C; max-width: 75ch; }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] { background: #111111; }
    [data-testid="stSidebar"] * { color: #E6E1D8; }
    [data-testid="stSidebarNav"] a, [data-testid="stSidebarNavLink"] { border-radius: 10px; }
    [data-testid="stSidebarNav"] a:hover, [data-testid="stSidebarNavLink"]:hover { background: rgba(255,255,255,.08); }
    [data-testid="stSidebarNav"] a[aria-current="page"], [data-testid="stSidebarNavLink"][aria-current="page"] {
        background: rgba(145,110,39,.25); box-shadow: inset 4px 0 0 #916E27; }
    [data-testid="stSidebarNav"] a[aria-current="page"] span, [data-testid="stSidebarNavLink"][aria-current="page"] span {
        color: #FFFFFF; font-weight: 700; }
    [data-testid="stNavSectionHeader"], [data-testid="stNavSectionHeader"] * { color: #CDBB8E !important;
        text-transform: uppercase; letter-spacing: .08em; font-size: .72rem !important; font-weight: 800; }
    .sidebar-brand { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.7rem; font-weight: 600; margin: 0;
                     color: #FFFFFF !important; }
    .sidebar-text { font-size: .82rem; margin: 2px 0 0; color: #A9A39A !important; }

    /* ---------- Buttons ---------- */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        border-radius: 999px; font-weight: 700; padding: .45rem 1.2rem; border: 1.5px solid #1C1C1C; color: #1C1C1C;
        background: #FFFFFF; }
    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
        background: #F3EEE3; border-color: #1C1C1C; color: #1C1C1C; }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
        background: #916E27; border-color: #916E27; color: #FFFFFF; }
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover,
    [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {
        background: #7A5B1E; border-color: #7A5B1E; color: #FFFFFF; }

    /* ---------- KPIs (st.metric) as cards ---------- */
    div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E7E1D5; border-top: 4px solid #916E27;
        border-radius: 14px; padding: 14px 16px 12px; }
    div[data-testid="stMetricLabel"] * { color: #6B655C; font-weight: 700; }
    div[data-testid="stMetricValue"] { color: #1C1C1C; font-weight: 800; font-variant-numeric: lining-nums tabular-nums; }
    div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] > div, div[data-testid="stMetricValue"] p {
        font-size: clamp(1.3rem, 1.6vw, 1.9rem) !important; overflow: visible !important; text-overflow: clip !important; }

    /* ---------- Tabs ---------- */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 2px solid #E7E1D5; }
    .stTabs [data-baseweb="tab"] { background: #FFFFFF; border: 1px solid #E7E1D5; border-bottom: none;
        border-radius: 12px 12px 0 0; padding: 8px 16px; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: #1C1C1C; border-color: #1C1C1C; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] p { color: #FFFFFF !important; font-weight: 700; }
    .stTabs [data-baseweb="tab-highlight"] { background: #916E27; height: 3px; }

    /* ---------- Panels and cards ---------- */
    [data-testid="stVerticalBlockBorderWrapper"] { background: #FFFFFF; border-radius: 16px; }
    .st-key-search_box { background: #F3EEE3; border: 1.5px solid #DDD3BF; border-radius: 18px; padding: 18px 18px 6px; }
    .st-key-confirm_box { background: #FFFFFF; border: 1.5px solid #E7E1D5; border-left: 6px solid #916E27;
        border-radius: 16px; padding: 18px; }
    div[class*="st-key-room_card_"], div[class*="st-key-chosen_"] { background: #FFFFFF; border: 1px solid #E7E1D5;
        border-radius: 16px; padding: 0 0 14px; overflow: hidden; transition: box-shadow .15s, transform .15s; }
    div[class*="st-key-room_card_"]:hover { box-shadow: 0 8px 24px rgba(28,28,28,.12); transform: translateY(-2px); }
    div[class*="st-key-room_card_"] > div, div[class*="st-key-chosen_"] > div { padding-left: 14px; padding-right: 14px; }
    div[class*="st-key-chosen_"] { border: 2.5px solid #916E27 !important; box-shadow: 0 8px 24px rgba(145,110,39,.20); }
    .photo { margin: 0 -14px 10px; height: 96px; display: flex; align-items: center; justify-content: center; }
    .photo .ms { font-size: 52px; }
    .room-title { font-size: 1.15rem; font-weight: 800; color: #1C1C1C; margin: 0; }
    .room-detail { font-size: .85rem; color: #6B655C; margin: 2px 0 8px; }
    .room-price { font-size: 1.35rem; font-weight: 800; color: #1C1C1C; margin: 6px 0 0; }
    .room-price small { font-size: .78rem; font-weight: 600; color: #6B655C; }

    /* ---------- Status and risk badges ---------- */
    .badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .75rem; font-weight: 700; }
    .b-confirmed { background: #F3EBD8; color: #5E4615; } .b-in_house { background: #E4EADF; color: #3D5439; }
    .b-checked_out { background: #ECEAE5; color: #3A3A3A; } .b-cancelled { background: #F2E0E0; color: #7A2828; }
    .b-Low { background: #E4EADF; color: #3D5439; } .b-Medium { background: #F3EBD8; color: #5E4615; }
    .b-High { background: #F2E0E0; color: #7A2828; }

    /* ---------- Alerts and tables ---------- */
    div[data-testid="stAlert"] { border-radius: 14px; }
    div[data-testid="stDataFrame"] { border: 1px solid #E7E1D5; border-radius: 12px; overflow: hidden; }

    /* ---------- Floor plan on the Today page ---------- */
    .brand, .cell, .page-title { font-variant-numeric: lining-nums; }
    .building { display: flex; flex-direction: column; gap: 6px; margin: .4rem 0 .6rem; padding: 14px;
                background: #FFFFFF; border: 1px solid #E7E1D5; border-radius: 16px; }
    .floor { display: flex; gap: 6px; align-items: stretch; flex-wrap: wrap; }
    .floor .n { width: 56px; font-size: .78rem; color: #6B655C; font-weight: 700; display: flex; align-items: center; }
    .cell { min-width: 78px; padding: 7px 9px; border-radius: 10px; font-size: .74rem; line-height: 1.25;
           border: 1px solid #E7E1D5; background: #FAF8F4; color: #1C1C1C; }
    .cell b { display: block; font-size: 1.05rem; font-weight: 800; }
    .cell.occupied { background: #1C1C1C; color: #fff; border-color: #1C1C1C; }
    .cell.arriving { background: #4F6B4A; color: #fff; border-color: #4F6B4A; }
    .cell.leaving { background: #916E27; color: #FFFFFF; border-color: #916E27; }
    .cell.maint { background: repeating-linear-gradient(45deg, rgba(142,47,47,.25) 0 6px, #FFFFFF 6px 12px);
                border-color: #8E2F2F; }
    .legend { font-size: .8rem; color: #6B655C; display: flex; gap: 14px; flex-wrap: wrap; }
    .legend i { display: inline-block; width: 12px; height: 12px; border-radius: 4px; margin-right: 5px; vertical-align: -1px; }
    </style>
    """, unsafe_allow_html=True)


def brand_header():
    """Hotel name, tagline and the pulse of the day: the brand never appears without a business number next to it."""
    try:
        total = scalar("SELECT COUNT(*) FROM room")
        occupied = scalar("""SELECT COUNT(DISTINCT re_room_id) FROM reservation WHERE re_status <> 'cancelled'
                             AND re_check_in_date <= :today AND re_check_out_date > :today""", {"today": TODAY})
        arrivals = scalar("""SELECT COUNT(*) FROM reservation
                             WHERE re_status = 'confirmed' AND re_check_in_date = :today""", {"today": TODAY})
        pulse = (f'<div class="stat"><strong>{100 * occupied / total:.0f}%</strong>occupancy today</div>'
                 f'<div class="stat"><strong>{int(arrivals)}</strong>'
                 f'{"arrival today" if int(arrivals) == 1 else "arrivals today"}</div>') if total else ""
    except Exception:
        pulse = ""
    st.markdown(f"""
    <div class="brand"><div class="content">
        <div>
            <p class="name">{HOTEL}</p>
            <p class="description">{HOTEL_DESCRIPTION}</p>
            <p class="tagline">{TAGLINE}</p>
        </div>
        <div class="today">{pulse}</div>
    </div></div>""", unsafe_allow_html=True)


def icon(name, size=20, color=None):
    """Material Symbols icon for use inside HTML (names at fonts.google.com/icons)."""
    style = f"font-size:{size}px;" + (f"color:{color};" if color else "")
    return f'<span class="ms" style="{style}">{name}</span>'


def badge(text, css_class=None):
    """Colored label for reservation statuses (confirmed, in_house...) and risk levels (High, Medium, Low)."""
    label = STATUS_LABEL.get(text, str(text).replace("_", " "))
    return f'<span class="badge b-{css_class or text}">{label}</span>'


# Cell colors for the status and risk columns in tables
_CELL_COLOR = {
    "Confirmed": ("#F3EBD8", "#5E4615"), "In house": ("#E4EADF", "#3D5439"),
    "Checked out": ("#ECEAE5", "#3A3A3A"), "Cancelled": ("#F2E0E0", "#7A2828"),
    "Low": ("#E4EADF", "#3D5439"), "Medium": ("#F3EBD8", "#5E4615"), "High": ("#F2E0E0", "#7A2828"),
}

# Readable headers for the SQL query aliases
COLUMN_LABELS = {
    "reservation": "Reservation", "guest": "Guest", "id_number": "ID number", "room": "Room", "room_type": "Room type",
    "season": "Season", "check_in": "Arrival", "check_out": "Departure", "nights": "Nights", "guests": "Guests", "adults": "Adults", "children": "Children",
    "back_in_service": "Back in service",
    "amount": "Amount", "status": "Status", "channel": "Channel", "rating": "Rating", "check_in_time": "Check-in",
    "check_out_time": "Check-out", "capacity": "Capacity", "floor": "Floor", "nightly_rate": "Nightly rate",
    "today": "Today", "start_date": "Start", "end_date": "End", "surcharge": "Surcharge", "country": "Country",
    "spent": "Spent", "guest_id": "Guest ID", "name": "Name", "email": "Email", "phone": "Phone",
    "reservations": "Reservations", "cancelled": "Cancelled", "total": "Total", "risk": "Risk",
    "earned": "Earned", "on_the_books": "On the books", "avg_nights": "Avg. nights", "average": "Average",
    "ratings": "Ratings", "stars": "Stars", "revenue": "Revenue", "feature": "Feature", "importance": "Importance",
    "cop_millions": "COP millions", "occupancy_pct": "Occupancy %", "revpar": "RevPAR", "adr": "ADR",
    "cancel_pct": "Cancellation %", "avg_lead_days": "Avg. lead time (days)", "lead_time": "Lead time",
    "hour": "Hour", "arrivals": "Arrivals", "departures": "Departures", "room_nights_sold": "Room nights sold",
    "same_day": "Same day", "unique_guests": "Guests",
}

# Codes stored in the database (confirmed, in_house, double...) and their readable label
VALUE_LABELS = {"status": {**STATUS_LABEL, "active": "Active", "maintenance": "Maintenance"},
                "room_type": ROOM_TYPE_LABEL, "channel": CHANNEL_LABEL}


def label_values(df):
    """Shows status, room type and channel codes with their readable label (in_house -> In house)."""
    d = df.copy()
    for col, labels in VALUE_LABELS.items():
        if col in d.columns:
            d[col] = d[col].map(lambda v: labels.get(v, v))
    return d


def _cell_style(v):
    background, text = _CELL_COLOR.get(v, (None, None))
    return f"background-color: {background}; color: {text}; font-weight: 700" if background else ""


def page_title(text, description=""):
    st.markdown(f'<div class="page-title"><h1>{text}</h1><p>{description}</p></div>', unsafe_allow_html=True)


def cop(v):
    """Formats an amount in Colombian pesos: 1540000 -> 'COP 1,540,000'."""
    try:
        return f"COP {float(v):,.0f}"
    except (TypeError, ValueError):
        return "COP 0"


def cop_short(v):
    """Short form for KPI cards, so big amounts aren't cut off: 1234567890 -> '$1.23 B', 25640000 -> '$25.6 M'.
    The card's label says the amount is in COP (Colombian pesos)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "$0"
    if abs(v) >= 1e9:
        return f"${v / 1e9:.2f} B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.1f} M"
    return f"${v:,.0f}"


def excel_button(df, name):
    """Downloads the table as Excel (needs openpyxl); if it isn't installed, as CSV."""
    buffer = io.BytesIO()
    try:
        df.to_excel(buffer, index=False, sheet_name="data")
        st.download_button("Download Excel", buffer.getvalue(), file_name=f"celosia_{name}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key=f"excel_{name}")
    except ImportError:
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"celosia_{name}.csv", mime="text/csv", key=f"csv_{name}")


def table(df, money=(), dates=(), headers=None, times=(), export=None):
    """Shows a DataFrame with readable headers and labels, money as COP, colored status and risk columns,
    and an optional Excel download."""
    d = label_values(df)
    for c in dates:
        d[c] = pd.to_datetime(d[c]).dt.date
    for c in times:
        d[c] = pd.to_datetime(d[c]).dt.strftime("%b %d %H:%M").fillna("")
    names = {c: (headers or {}).get(c, COLUMN_LABELS.get(c, c)) for c in d.columns}
    raw = d.rename(columns=names)                  # for the Excel file: numbers stay numbers
    for c in money:
        d[c] = d[c].map(cop)
    shown = d.rename(columns=names)
    colored = [names[c] for c in d.columns if c in ("status", "risk")]
    if colored:      # statuses and risk levels with their color (confirmed in gold, cancelled in crimson...)
        style = shown.style
        paint = getattr(style, "map", None) or style.applymap
        shown = paint(_cell_style, subset=colored).format(precision=0, na_rep="")
    st.dataframe(shown, hide_index=True)
    if export:
        excel_button(raw, export)


def bar_chart(df, x, y, x_title, y_title, horizontal=False, color=INK):
    """Bar chart that keeps the order the query returns (Oracle's ORDER BY)."""
    if horizontal:
        enc = dict(y=alt.Y(f"{x}:N", sort="-x", title=x_title), x=alt.X(f"{y}:Q", title=y_title))
    else:
        enc = dict(x=alt.X(f"{x}:N", sort=None, title=x_title, axis=alt.Axis(labelAngle=-35)),
                   y=alt.Y(f"{y}:Q", title=y_title))
    df = label_values(df)
    tooltip = [alt.Tooltip(c, title=COLUMN_LABELS.get(c, c)) for c in df.columns]
    st.altair_chart(alt.Chart(df).mark_bar(color=color).encode(**enc, tooltip=tooltip))


def revenue_bars(df, x, x_title, horizontal=False, value_title="Revenue (COP millions)"):
    """Stacked bars with two parts: earned (ink) and on the books (gold)."""
    df = label_values(df)
    long = df[[x, "earned", "on_the_books"]].melt(id_vars=x, var_name="part", value_name="amount")
    long["cop_millions"] = (long["amount"].astype(float) / 1e6).round(1)
    long["part"] = long["part"].map({"earned": "Earned", "on_the_books": "On the books"})
    long["order"] = long["part"].map({"Earned": 0, "On the books": 1})
    x_order = list(df[x])
    color = alt.Color("part:N", scale=alt.Scale(domain=["Earned", "On the books"], range=[INK, GOLD]),
                      legend=alt.Legend(title=None, orient="bottom"))
    if horizontal:
        enc = dict(y=alt.Y(f"{x}:N", sort=x_order, title=x_title),
                   x=alt.X("cop_millions:Q", stack=True, title=value_title))
    else:
        enc = dict(x=alt.X(f"{x}:N", sort=x_order, title=x_title, axis=alt.Axis(labelAngle=-35)),
                   y=alt.Y("cop_millions:Q", stack=True, title=value_title))
    st.altair_chart(alt.Chart(long).mark_bar().encode(
        **enc, color=color, order=alt.Order("order:Q"),
        tooltip=[alt.Tooltip(x, title=x_title), alt.Tooltip("part", title="Revenue"),
                 alt.Tooltip("cop_millions", title="COP millions")]))


def chart_selection(event, name):
    """Reads what the user clicked on an Altair chart (on_select). Returns a dict or None."""
    try:
        sel = event["selection"][name]
    except (KeyError, TypeError, AttributeError):
        return None
    if isinstance(sel, list) and sel:
        return sel[0]
    return None


def year_filter(key):
    years = [0] + [int(a) for a in query(
        "SELECT DISTINCT EXTRACT(YEAR FROM re_check_in_date) AS yr FROM reservation ORDER BY yr")["yr"]]
    year = st.selectbox("Year", years, format_func=lambda a: "All years" if a == 0 else str(a), key=key)
    return {"yr": year}
