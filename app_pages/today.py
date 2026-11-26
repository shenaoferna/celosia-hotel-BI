"""Today page: KPIs, the hotel floor by floor, the front desk's pending work and revenue by month."""

import datetime as dt
import html

import altair as alt
import pandas as pd
import streamlit as st

from config import CHANNELS, GOLD, INK, MINORS_RULE, REVENUE_NOTE, ROOM_TYPE_LABEL, TODAY, party
from db import query, scalar
from rules import check_in, check_out, same_day_last_year
from ui import bar_chart, chart_selection, cop, cop_short, page_title, table

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def move_day(days):
    st.session_state.today_day = st.session_state.today_day + dt.timedelta(days=days)


def go_to_today():
    st.session_state.today_day = TODAY


def front_desk_today():
    """Pending arrivals and departures, each with its button. Only makes sense for today."""
    base = """SELECT r.re_reservation_id AS reservation, ro.ro_number AS room, g.gu_name AS guest,
                     r.re_check_in_date AS check_in, r.re_check_out_date AS check_out, r.re_adults AS adults,
                     r.re_children AS children, r.re_check_in_time AS check_in_time
              FROM reservation r JOIN room ro ON ro.ro_room_id = r.re_room_id
              JOIN guest g ON g.gu_guest_id = r.re_guest_id """
    to_arrive = query(base + """WHERE r.re_status = 'confirmed' AND r.re_check_in_date <= :today
                                AND r.re_check_out_date > :today ORDER BY r.re_check_in_date, ro.ro_number""",
                      {"today": TODAY})
    to_leave = query(base + """WHERE r.re_status = 'in_house' AND r.re_check_out_date <= :today
                               ORDER BY r.re_check_out_date, ro.ro_number""", {"today": TODAY})
    st.subheader("Today at the front desk")
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Pending check-ins ({len(to_arrive)})**")
        if to_arrive.empty:
            st.caption("No guests left to arrive.")
        for r in to_arrive.itertuples():
            arrival = pd.to_datetime(r.check_in).date()
            late = f", was due {arrival:%b %d}" if arrival < TODAY else ""
            a, b = st.columns([3, 1.3], vertical_alignment="center")
            a.markdown(f"**{r.room}** {r.guest}, {party(r.adults, r.children)}{late}")
            verified = True
            if r.children:      # minors: the documents must be checked before check-in
                verified = a.checkbox("Minors' documents verified", key=f"docs_{r.reservation}", help=MINORS_RULE)
            b.button("Check-in", key=f"in_{r.reservation}", on_click=check_in, args=(r.reservation,), type="primary",
                     disabled=not verified, help=None if verified else "Verify the minors' documents first.")
    with right:
        st.markdown(f"**Pending check-outs ({len(to_leave)})**")
        if to_leave.empty:
            st.caption("No pending departures.")
        for r in to_leave.itertuples():
            departure = pd.to_datetime(r.check_out).date()
            late = f", was due {departure:%b %d}" if departure < TODAY else ""
            a, b = st.columns([3, 1.3], vertical_alignment="center")
            a.markdown(f"**{r.room}** {r.guest}{late}")
            b.button("Check-out", key=f"out_{r.reservation}", on_click=check_out, args=(r.reservation,))


def today():
    if "today_day" not in st.session_state:
        st.session_state.today_day = TODAY

    c0, c1, c2, c3, c4 = st.columns([3.4, 1.15, 0.8, 1.6, 1.25], vertical_alignment="bottom")
    c1.button("Previous", icon=":material/chevron_left:", on_click=move_day, args=(-1,))
    c2.button("Today", on_click=go_to_today, disabled=st.session_state.today_day == TODAY)
    c3.date_input("Day", key="today_day", format="MM/DD/YYYY", label_visibility="collapsed")
    c4.button("Next", icon=":material/chevron_right:", on_click=move_day, args=(1,))
    d = st.session_state.today_day
    with c0:
        when = "today" if d == TODAY else ("in the past" if d < TODAY else "based on confirmed reservations")
        page_title("Today at a glance", f"{WEEKDAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}, {when}.")

    # ---------- stays that touch day d ----------
    stays = query("""
        SELECT ro.ro_number AS room, r.re_reservation_id AS reservation, g.gu_name AS guest,
               r.re_check_in_date AS check_in, r.re_check_out_date AS check_out, r.re_guests AS guests,
               r.re_children AS children, r.re_nights AS nights, r.re_total_amount AS amount, r.re_channel AS channel, ro.ro_type AS room_type,
               r.re_status AS status, r.re_check_in_time AS check_in_time, r.re_check_out_time AS check_out_time
        FROM reservation r
        JOIN room ro ON ro.ro_room_id = r.re_room_id
        JOIN guest g ON g.gu_guest_id = r.re_guest_id
        WHERE r.re_status <> 'cancelled' AND r.re_check_in_date <= :d AND r.re_check_out_date >= :d""", {"d": d})
    for c in ("check_in", "check_out"):
        stays[c] = pd.to_datetime(stays[c]).dt.date
    arriving = stays[stays["check_in"] == d]
    leaving = stays[stays["check_out"] == d]
    in_house = stays[(stays["check_in"] <= d) & (stays["check_out"] > d)]

    rooms = query("""SELECT ro_number AS room, ro_floor AS floor, ro_type AS room_type, ro_status AS status,
                            ro_back_in_service AS back_in_service
                     FROM room ORDER BY ro_floor DESC, ro_number""")

    def occupancy(day):
        n = scalar("""SELECT COUNT(DISTINCT re_room_id) FROM reservation WHERE re_status <> 'cancelled'
                      AND re_check_in_date <= :d AND re_check_out_date > :d""", {"d": day})
        return 100 * n / len(rooms) if len(rooms) else 0

    occ_today, occ_last_year = occupancy(d), occupancy(same_day_last_year(d))
    revenue_between = lambda start, end: scalar("""SELECT SUM(re_total_amount) FROM reservation
                                                   WHERE re_status <> 'cancelled'
                                                     AND re_check_in_date BETWEEN :a AND :b""", {"a": start, "b": end})
    ytd = revenue_between(dt.date(d.year, 1, 1), d)
    ytd_last_year = revenue_between(dt.date(d.year - 1, 1, 1), same_day_last_year(d))

    k = st.columns(5)
    k[0].metric("Occupancy", f"{occ_today:.0f}%", f"{occ_today - occ_last_year:+.0f} pts vs. {d.year - 1}")
    k[1].metric("Arrivals", len(arriving))
    k[2].metric("Departures", len(leaving))
    k[3].metric("Guests in house", int(in_house["guests"].sum()) if len(in_house) else 0)
    k[4].metric(f"{d.year} revenue (COP)", cop_short(ytd),
                f"{100 * (ytd - ytd_last_year) / ytd_last_year:+.1f}% vs. {d.year - 1}" if ytd_last_year else None,
                help=f"From January 1 to {d:%B %d, %Y}.")

    # ---------- the building, floor by floor ----------
    st.subheader("The hotel that day")
    floors = []
    for floor, group in rooms.groupby("floor", sort=False):
        cells = []
        for h in group.itertuples():
            arr = arriving[arriving["room"] == h.room]
            stay = in_house[in_house["room"] == h.room]
            dep = leaving[leaving["room"] == h.room]
            if len(arr) and d == TODAY and arr.iloc[0]["status"] == "in_house":
                css, who, note = "occupied", arr.iloc[0]["guest"], "Checked in"
            elif len(arr):
                css, who, note = "arriving", arr.iloc[0]["guest"], "Arriving"
            elif len(stay):
                css, who, note = "occupied", stay.iloc[0]["guest"], "Occupied"
            elif len(dep):
                css, who, note = "leaving", dep.iloc[0]["guest"], "Leaving"
            elif h.status == "maintenance" and TODAY <= d < pd.to_datetime(h.back_in_service).date():
                css, who, note = "maint", "", "Maintenance"   # only from today until it's back in service
            else:
                css, who, note = "", "", ROOM_TYPE_LABEL.get(h.room_type, h.room_type)
            hover = html.escape(f"{h.room} · {ROOM_TYPE_LABEL.get(h.room_type, h.room_type)}" + (f" · {who}" if who else ""))
            first_name = html.escape(who.split()[0]) if who else note
            cells.append(f'<div class="cell {css}" title="{hover}"><b>{h.room}</b>{first_name}</div>')
        floors.append(f'<div class="floor"><span class="n">Floor {floor}</span>{"".join(cells)}</div>')
    st.markdown('<div class="building">' + "".join(floors) + "</div>", unsafe_allow_html=True)
    st.markdown('<div class="legend"><span><i style="background:#4F6B4A"></i>Arriving</span>'
                '<span><i style="background:#1C1C1C"></i>Occupied</span>'
                '<span><i style="background:#916E27"></i>Leaving (room frees up)</span>'
                '<span><i style="background:#FAF8F4;border:1px solid #E7E1D5"></i>Free</span>'
                '<span><i style="background:repeating-linear-gradient(45deg,rgba(142,47,47,.55) 0 3px,#fff 3px 6px)"></i>'
                'Maintenance</span></div>', unsafe_allow_html=True)
    st.caption("Hover over a room to see the guest.")

    if d == TODAY:
        front_desk_today()

    t1, t2, t3 = st.tabs([f"Arrivals ({len(arriving)})", f"Departures ({len(leaving)})", f"In house ({len(in_house)})"])
    for tab, rows, name in ((t1, arriving, "arrivals"), (t2, leaving, "departures"), (t3, in_house, "in_house")):
        with tab:
            if rows.empty:
                st.caption("No records for this day.")
            else:
                table(rows[["room", "guest", "check_in", "check_out", "nights", "guests", "children", "channel", "status",
                            "check_in_time", "check_out_time", "amount"]],
                      money=["amount"], times=["check_in_time", "check_out_time"], export=f"{name}_{d:%Y%m%d}")

    # ---------- the year's revenue: click a month to see the breakdown ----------
    st.subheader(f"{d.year} revenue by month")
    st.caption("Click a bar to see where that month's revenue came from. " + REVENUE_NOTE)
    monthly = query("""
        SELECT EXTRACT(MONTH FROM re_check_in_date) AS month_num,
               SUM(CASE WHEN re_status IN ('checked_out', 'in_house') THEN re_total_amount ELSE 0 END) AS earned,
               SUM(CASE WHEN re_status = 'confirmed' THEN re_total_amount ELSE 0 END) AS on_the_books
        FROM reservation
        WHERE re_status <> 'cancelled' AND EXTRACT(YEAR FROM re_check_in_date) = :yr
        GROUP BY EXTRACT(MONTH FROM re_check_in_date) ORDER BY 1""", {"yr": d.year})
    monthly["month_num"] = monthly["month_num"].astype(int)
    long = monthly.melt(id_vars="month_num", value_vars=["earned", "on_the_books"], var_name="part", value_name="amount")
    long["cop_millions"] = (long["amount"].astype(float) / 1e6).round(1)
    long["part"] = long["part"].map({"earned": "Earned", "on_the_books": "On the books"})
    long["order"] = long["part"].map({"Earned": 0, "On the books": 1})
    long["month"] = long["month_num"].map(lambda m: MONTHS_SHORT[m - 1])
    click = alt.selection_point(name="chosen_month", fields=["month_num"])
    chart = alt.Chart(long).mark_bar().encode(
        x=alt.X("month:N", sort=MONTHS_SHORT, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("cop_millions:Q", stack=True, title="COP millions"),
        color=alt.Color("part:N", scale=alt.Scale(domain=["Earned", "On the books"], range=[INK, GOLD]),
                        legend=alt.Legend(title=None, orient="bottom")),
        order=alt.Order("order:Q"),
        opacity=alt.condition(click, alt.value(1), alt.value(0.35)),
        tooltip=[alt.Tooltip("month", title="Month"), alt.Tooltip("part", title="Revenue"),
                 alt.Tooltip("cop_millions", title="COP millions")],
    ).add_params(click)
    event = st.altair_chart(chart, on_select="rerun", key="month_chart")
    chosen = chart_selection(event, "chosen_month")
    if chosen:
        m = int(chosen["month_num"])
        start = dt.date(d.year, m, 1)
        end = dt.date(d.year + (m == 12), m % 12 + 1, 1)
        detail = query("""
            SELECT r.re_channel AS channel, ro.ro_type AS room_type, COUNT(*) AS reservations,
                   SUM(r.re_nights) AS nights, SUM(r.re_total_amount) AS revenue
            FROM reservation r JOIN room ro ON ro.ro_room_id = r.re_room_id
            WHERE r.re_status <> 'cancelled' AND r.re_check_in_date >= :a AND r.re_check_in_date < :b
            GROUP BY r.re_channel, ro.ro_type""", {"a": start, "b": end})
        st.markdown(f"**{MONTHS_SHORT[m - 1]} {d.year} breakdown**")
        kk = st.columns(3)
        kk[0].metric("Reservations", int(detail["reservations"].sum()))
        kk[1].metric("Room nights sold", int(detail["nights"].sum()))
        kk[2].metric("ADR for the month",
                     cop(detail["revenue"].sum() / detail["nights"].sum() if detail["nights"].sum() else 0))
        left, right = st.columns(2)
        with left:
            by_channel = detail.groupby("channel", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
            by_channel["cop_millions"] = (by_channel["revenue"].astype(float) / 1e6).round(1)
            by_channel["channel"] = by_channel["channel"].map(CHANNELS).fillna(by_channel["channel"])
            bar_chart(by_channel[["channel", "cop_millions"]], "channel", "cop_millions", "Channel", "COP millions",
                      horizontal=True)
        with right:
            by_type = detail.groupby("room_type", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
            by_type["cop_millions"] = (by_type["revenue"].astype(float) / 1e6).round(1)
            bar_chart(by_type[["room_type", "cop_millions"]], "room_type", "cop_millions", "Room type", "COP millions",
                      horizontal=True, color=GOLD)
