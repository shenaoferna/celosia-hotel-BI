"""Occupancy map page: rooms by day of the month."""

import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from config import BOUGAINVILLEA, INDIGO, TODAY
from db import query
from ui import chart_selection, page_title, table

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def occupancy_map():
    page_title("Occupancy map", "Each row is a room and each column a day of the month.")
    c1, c2 = st.columns(2)
    years = [2025, 2026, 2027]
    year = c1.selectbox("Year", years, index=years.index(TODAY.year) if TODAY.year in years else 1)
    month = c2.selectbox("Month", range(1, 13), index=TODAY.month - 1, format_func=lambda m: MONTHS[m - 1])
    start = dt.date(year, month, 1)
    end = dt.date(year + (month == 12), month % 12 + 1, 1)          # first day of the next month

    rooms = query("SELECT ro_number AS room, ro_type AS room_type, ro_status AS status FROM room ORDER BY ro_number")
    stays = query("""
        SELECT ro.ro_number AS room, r.re_reservation_id AS reservation, g.gu_name AS guest,
               r.re_check_in_date AS check_in, r.re_check_out_date AS check_out
        FROM reservation r
        JOIN room ro ON ro.ro_room_id = r.re_room_id
        JOIN guest g ON g.gu_guest_id = r.re_guest_id
        WHERE r.re_status <> 'cancelled' AND r.re_check_in_date < :period_end AND r.re_check_out_date > :period_start""",
        {"period_start": start, "period_end": end})

    days = pd.date_range(start, end - dt.timedelta(days=1)).date
    grid = pd.DataFrame([(room, d) for room in rooms["room"] for d in days], columns=["room", "date"])
    grid["state"], grid["details"] = "free", ""
    in_maintenance = set(rooms.loc[rooms["status"] == "maintenance", "room"])
    grid.loc[grid["room"].isin(in_maintenance) & (grid["date"] >= TODAY), "state"] = "maintenance"
    for r in stays.itertuples():
        arrival, departure = pd.to_datetime(r.check_in).date(), pd.to_datetime(r.check_out).date()
        mask = (grid["room"] == r.room) & (grid["date"] >= arrival) & (grid["date"] < departure)
        grid.loc[mask, "state"] = "occupied"
        grid.loc[mask, "details"] = f"Reservation {r.reservation}: {r.guest}"
    grid["day"] = [d.day for d in grid["date"]]
    grid["date_text"] = [f"{d:%m/%d/%Y}" for d in grid["date"]]

    occupied = (grid["state"] == "occupied").sum()
    k = st.columns(3)
    k[0].metric("Occupancy this month", f"{100 * occupied / len(grid):.0f}%")
    k[1].metric("Occupied room nights", int(occupied))
    k[2].metric("Stays in the month", len(stays))

    colors = {"occupied": INDIGO, "free": "rgba(140,127,110,.18)", "maintenance": BOUGAINVILLEA}
    click = alt.selection_point(name="cell", fields=["room", "day"])
    chart = alt.Chart(grid.drop(columns=["date"])).mark_rect(stroke="white", strokeWidth=1).encode(
        x=alt.X("day:O", title=f"{MONTHS[month - 1]} {year}", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("room:N", title="Room", sort=list(rooms["room"])),
        color=alt.Color("state:N", scale=alt.Scale(domain=list(colors), range=list(colors.values())),
                        legend=alt.Legend(title=None, orient="bottom")),
        tooltip=[alt.Tooltip("room", title="Room"), alt.Tooltip("date_text", title="Date"),
                 alt.Tooltip("state", title="Status"), alt.Tooltip("details", title="Details")],
        opacity=alt.condition(click, alt.value(1), alt.value(0.55)),
    ).add_params(click).properties(height=26 * len(rooms))
    st.caption("Click an occupied cell to see the reservation.")
    event = st.altair_chart(chart, on_select="rerun", key="map_cells")
    cell = chart_selection(event, "cell")
    if cell:
        row = grid[(grid["room"] == str(cell["room"])) & (grid["day"] == int(cell["day"]))]
        if len(row) and row.iloc[0]["state"] == "occupied":
            reservation_id = int(row.iloc[0]["details"].split(":")[0].replace("Reservation", "").strip())
            info = query("""
                SELECT r.re_reservation_id AS reservation, g.gu_name AS guest, g.gu_country AS country,
                       r.re_check_in_date AS check_in, r.re_check_out_date AS check_out, r.re_nights AS nights,
                       r.re_guests AS guests, r.re_channel AS channel, r.re_total_amount AS amount,
                       r.re_status AS status
                FROM reservation r JOIN guest g ON g.gu_guest_id = r.re_guest_id
                WHERE r.re_reservation_id = :id""", {"id": reservation_id})
            st.markdown(f"**Room {cell['room']}, day {int(cell['day'])}**")
            table(info, money=["amount"], dates=["check_in", "check_out"])
        elif len(row):
            st.info(f"Room {cell['room']} is {row.iloc[0]['state']} that day.")
