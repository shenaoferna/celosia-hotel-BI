"""Performance page: occupancy, ADR, RevPAR, revenue, channels, lead time, booking pace and arrival times."""

import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from config import CHANNEL_LABEL, COMMISSION, CRIMSON, GOLD, INK, OLIVE, REVENUE_NOTE, STONE, TODAY
from db import query, scalar
from ui import bar_chart, page_title, revenue_bars, table, year_filter

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def performance():
    page_title("Hotel performance", "Occupancy, rates and revenue, using the standard hospitality KPIs.")
    year = year_filter("performance_year")
    t1, t2, t3, t4, t5, t6 = st.tabs(["Occupancy, ADR and RevPAR", "Revenue by room type",
                                      "Sales channels", "Booking lead time", "Booking pace",
                                      "Arrival and departure times"])

    with t1:
        n_rooms = int(scalar("SELECT COUNT(*) FROM room"))
        df = query("""
            SELECT s.se_name AS season, s.se_start_date AS start_date, s.se_surcharge AS surcharge,
                   (s.se_end_date - s.se_start_date + 1) AS days,
                   COUNT(r.re_reservation_id) AS reservations, NVL(SUM(r.re_nights), 0) AS room_nights_sold,
                   NVL(SUM(r.re_total_amount), 0) AS revenue
            FROM season s
            LEFT JOIN reservation r ON r.re_season_id = s.se_season_id AND r.re_status <> 'cancelled'
            WHERE (:yr = 0 OR EXTRACT(YEAR FROM s.se_start_date) = :yr)
            GROUP BY s.se_season_id, s.se_name, s.se_start_date, s.se_end_date, s.se_surcharge
            ORDER BY s.se_start_date""", year)
        available = df["days"].astype(float) * n_rooms
        df["occupancy_pct"] = (100 * df["room_nights_sold"] / available).round(1)
        df["adr"] = (df["revenue"].astype(float) / df["room_nights_sold"].where(df["room_nights_sold"] > 0)).fillna(0).round(0)
        df["revpar"] = (df["revenue"].astype(float) / available).round(0)
        st.markdown("**ADR** = revenue ÷ room nights sold (the average price paid per night).  \n"
                    "**RevPAR** = revenue ÷ room nights available (combines price and occupancy in one number).")
        left, right = st.columns(2)
        with left:
            bar_chart(df, "season", "occupancy_pct", "Season", "Occupancy (%)")
        with right:
            bar_chart(df, "season", "revpar", "Season", "RevPAR (COP)", color=GOLD)
        table(df[["season", "surcharge", "reservations", "room_nights_sold", "occupancy_pct", "adr", "revpar"]],
              money=["adr", "revpar"], export="occupancy_adr_revpar")
        st.caption("Each stay's nights count toward the season of its check-in date. For seasons that haven't "
                   "ended, occupancy, ADR and RevPAR include confirmed reservations (on the books).")

    with t2:
        df = query("""
            SELECT ro.ro_type AS room_type, COUNT(*) AS reservations, SUM(r.re_nights) AS nights,
                   SUM(CASE WHEN r.re_status IN ('checked_out', 'in_house') THEN r.re_total_amount ELSE 0 END) AS earned,
                   SUM(CASE WHEN r.re_status = 'confirmed' THEN r.re_total_amount ELSE 0 END) AS on_the_books,
                   SUM(r.re_total_amount) AS total, ROUND(SUM(r.re_total_amount) / SUM(r.re_nights)) AS adr
            FROM reservation r JOIN room ro ON ro.ro_room_id = r.re_room_id
            WHERE r.re_status <> 'cancelled' AND (:yr = 0 OR EXTRACT(YEAR FROM r.re_check_in_date) = :yr)
            GROUP BY ro.ro_type ORDER BY total DESC""", year)
        revenue_bars(df, "room_type", "Room type")
        table(df, money=["earned", "on_the_books", "total", "adr"], export="revenue_by_room_type")
        st.caption(REVENUE_NOTE)

    with t3:
        df = query("""
            SELECT re_channel AS channel, COUNT(*) AS reservations,
                   SUM(CASE WHEN re_status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
                   SUM(CASE WHEN re_status <> 'cancelled' THEN re_total_amount ELSE 0 END) AS revenue,
                   SUM(CASE WHEN re_status IN ('checked_out', 'in_house') THEN re_total_amount ELSE 0 END) AS gross_earned,
                   SUM(CASE WHEN re_status = 'confirmed' THEN re_total_amount ELSE 0 END) AS gross_on_the_books
            FROM reservation
            WHERE (:yr = 0 OR EXTRACT(YEAR FROM re_check_in_date) = :yr)
            GROUP BY re_channel ORDER BY revenue DESC""", year)
        df["commission_pct"] = df["channel"].map(COMMISSION).fillna(0) * 100
        df["net_revenue"] = (df["revenue"].astype(float) * (1 - df["commission_pct"] / 100)).round(0)
        df["cancel_pct"] = (100 * df["cancelled"] / df["reservations"]).round(1)
        df["channel_name"] = df["channel"].map(CHANNEL_LABEL).fillna(df["channel"])
        df["earned"] = (df["gross_earned"].astype(float) * (1 - df["commission_pct"] / 100)).round(0)
        df["on_the_books"] = (df["gross_on_the_books"].astype(float) * (1 - df["commission_pct"] / 100)).round(0)
        left, right = st.columns(2)
        with left:
            revenue_bars(df, "channel_name", "Channel", horizontal=True, value_title="Net revenue (COP millions)")
        with right:
            bar_chart(df, "channel_name", "cancel_pct", "Channel", "Cancellation rate (%)", horizontal=True,
                      color=CRIMSON)
        table(df[["channel_name", "reservations", "cancelled", "cancel_pct", "revenue", "commission_pct", "earned",
                  "on_the_books", "net_revenue"]],
              money=["revenue", "earned", "on_the_books", "net_revenue"],
              headers={"channel_name": "Channel", "commission_pct": "Commission %", "revenue": "Gross revenue",
                       "earned": "Net earned", "on_the_books": "Net on the books", "net_revenue": "Total net revenue"},
              export="channels")
        st.caption("Commissions assumed for the analysis: Booking.com 18%, travel agency 12%, direct and walk-in 0%. "
                   + REVENUE_NOTE)

    with t4:
        df = query("""
            SELECT s.se_name AS season, s.se_start_date AS start_date,
                   ROUND(AVG(r.re_check_in_date - r.re_booking_date), 1) AS avg_lead_days,
                   SUM(CASE WHEN r.re_check_in_date = r.re_booking_date THEN 1 ELSE 0 END) AS same_day,
                   COUNT(*) AS reservations
            FROM reservation r JOIN season s ON s.se_season_id = r.re_season_id
            WHERE (:yr = 0 OR EXTRACT(YEAR FROM r.re_check_in_date) = :yr)
            GROUP BY s.se_season_id, s.se_name, s.se_start_date
            ORDER BY s.se_start_date""", year)
        bar_chart(df, "season", "avg_lead_days", "Season", "Average lead time (days)", color=STONE)
        ranges = query("""
            SELECT CASE WHEN days = 0 THEN '1. Same day'
                        WHEN days <= 7 THEN '2. 1 to 7 days'
                        WHEN days <= 30 THEN '3. 8 to 30 days'
                        WHEN days <= 90 THEN '4. 31 to 90 days'
                        ELSE '5. More than 90 days' END AS lead_time,
                   COUNT(*) AS reservations
            FROM (SELECT re_check_in_date - re_booking_date AS days FROM reservation
                  WHERE (:yr = 0 OR EXTRACT(YEAR FROM re_check_in_date) = :yr))
            GROUP BY CASE WHEN days = 0 THEN '1. Same day'
                          WHEN days <= 7 THEN '2. 1 to 7 days'
                          WHEN days <= 30 THEN '3. 8 to 30 days'
                          WHEN days <= 90 THEN '4. 31 to 90 days'
                          ELSE '5. More than 90 days' END
            ORDER BY 1""", year)
        ranges["lead_time"] = ranges["lead_time"].str[3:]
        bar_chart(ranges, "lead_time", "reservations", "How far ahead do guests book?", "Reservations")

    with t5:
        booking_pace()

    with t6:
        arrivals = query("""
            SELECT TO_NUMBER(TO_CHAR(re_check_in_time, 'HH24')) AS hour, COUNT(*) AS arrivals
            FROM reservation WHERE re_check_in_time IS NOT NULL
              AND (:yr = 0 OR EXTRACT(YEAR FROM re_check_in_date) = :yr)
            GROUP BY TO_NUMBER(TO_CHAR(re_check_in_time, 'HH24')) ORDER BY 1""", year)
        departures = query("""
            SELECT TO_NUMBER(TO_CHAR(re_check_out_time, 'HH24')) AS hour, COUNT(*) AS departures
            FROM reservation WHERE re_check_out_time IS NOT NULL
              AND (:yr = 0 OR EXTRACT(YEAR FROM re_check_in_date) = :yr)
            GROUP BY TO_NUMBER(TO_CHAR(re_check_out_time, 'HH24')) ORDER BY 1""", year)
        if arrivals.empty:
            st.info("No check-ins recorded for that year yet.")
        else:
            total_in = int(arrivals["arrivals"].sum())
            peak = int(arrivals.loc[arrivals["arrivals"].idxmax(), "hour"])
            late_arrivals = int(arrivals.loc[arrivals["hour"] >= 20, "arrivals"].sum())
            late_departures = int(departures.loc[departures["hour"] > 12, "departures"].sum()) if len(departures) else 0
            k = st.columns(3)
            k[0].metric("Peak arrival hour", f"{peak}:00")
            k[1].metric("Arrivals after 8 p.m.", f"{100 * late_arrivals / total_in:.0f}%",
                        f"{late_arrivals} check-ins", delta_color="off")
            k[2].metric("Departures after noon", late_departures, "late check-out", delta_color="off")
            for df_h in (arrivals, departures):
                df_h["hour"] = df_h["hour"].astype(int).map(lambda h: f"{h:02d}:00")
            left, right = st.columns(2)
            with left:
                bar_chart(arrivals, "hour", "arrivals", "Check-in time", "Arrivals", color=OLIVE)
            with right:
                bar_chart(departures, "hour", "departures", "Check-out time", "Departures", color=GOLD)
            st.caption("Useful for planning front-desk staffing and housekeeping.")


def booking_pace():
    st.markdown("How is a month's occupancy pacing **compared with last year at the same point**? "
                "Each line adds up the room nights booked by the day the reservation was made (`re_booking_date`).")
    c1, c2 = st.columns(2)
    year = c1.selectbox("Year", [2025, 2026, 2027], index=1, key="pace_year")
    month = c2.selectbox("Month", range(1, 13), index=11, format_func=lambda m: MONTHS[m - 1], key="pace_month")
    n_rooms = int(scalar("SELECT COUNT(*) FROM room"))

    def period(y):
        start = dt.date(y, month, 1)
        end = dt.date(y + (month == 12), month % 12 + 1, 1)
        return start, end

    def bookings_in_period(start, end):
        df = query("""
            SELECT re_booking_date AS booked, GREATEST(re_check_in_date, :period_start) AS stay_start,
                   LEAST(re_check_out_date, :period_end) AS stay_end
            FROM reservation
            WHERE re_status <> 'cancelled' AND re_check_in_date < :period_end AND re_check_out_date > :period_start""",
            {"period_start": start, "period_end": end})
        if df.empty:
            return df
        df["nights"] = (pd.to_datetime(df["stay_end"]) - pd.to_datetime(df["stay_start"])).dt.days
        df["days_before"] = (pd.Timestamp(start) - pd.to_datetime(df["booked"])).dt.days   # days before the 1st
        return df

    start, end = period(year)
    start_ly, end_ly = period(year - 1)
    capacity = (end - start).days * n_rooms
    current, last_year = bookings_in_period(start, end), bookings_in_period(start_ly, end_ly)
    days_to_start = (start - TODAY).days               # days until the month starts (negative if it already started)
    window = range(120, -(end - start).days, -1)

    def curve(df, up_to_today):
        rows = []
        for d in window:
            if up_to_today and d < days_to_start:
                break                                  # days that haven't happened yet
            n = int(df.loc[df["days_before"] >= d, "nights"].sum()) if len(df) else 0
            rows.append({"days_before": d, "occupancy": round(100 * n / capacity, 1), "nights": n})
        return pd.DataFrame(rows)

    current_curve = curve(current, up_to_today=True).assign(period=f"{MONTHS[month - 1]} {year}")
    last_year_curve = curve(last_year, up_to_today=False).assign(period=f"{MONTHS[month - 1]} {year - 1}")
    if current_curve.empty and last_year_curve.empty:
        st.info("No reservations for that month or for the same month last year.")
        return

    cut = max(days_to_start, window[-1])
    now_current = int(current.loc[current["days_before"] >= cut, "nights"].sum()) if len(current) else 0
    now_last_year = int(last_year.loc[last_year["days_before"] >= cut, "nights"].sum()) if len(last_year) else 0
    final_last_year = int(last_year["nights"].sum()) if len(last_year) else 0
    k = st.columns(3)
    label = f"{days_to_start} days before it starts" if days_to_start > 0 else "month closed" if TODAY >= end else "month to date"
    k[0].metric(f"Occupancy on the books {year}", f"{100 * now_current / capacity:.0f}%", label, delta_color="off")
    k[1].metric(f"{year - 1} at the same point", f"{100 * now_last_year / capacity:.0f}%",
                f"{100 * (now_current - now_last_year) / capacity:+.0f} pts" if now_last_year or now_current else None)
    k[2].metric(f"{year - 1} final", f"{100 * final_last_year / capacity:.0f}%", "where last year ended",
                delta_color="off")

    data = pd.concat([last_year_curve, current_curve])
    line = alt.Chart(data).mark_line(strokeWidth=3).encode(
        x=alt.X("days_before:Q", scale=alt.Scale(reverse=True),
                title="Days before the 1st of the month (negative: within the month)"),
        y=alt.Y("occupancy:Q", title="Occupancy on the books (%)"),
        color=alt.Color("period:N", scale=alt.Scale(range=[STONE, INK]), legend=alt.Legend(title=None, orient="bottom")),
        tooltip=[alt.Tooltip("period", title="Month"), alt.Tooltip("days_before", title="Days before"),
                 alt.Tooltip("occupancy", title="Occupancy %"), alt.Tooltip("nights", title="Nights")])
    st.altair_chart(line)
    st.caption("Cancelled reservations aren't counted, because the database doesn't store when they were cancelled.")
