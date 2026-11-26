"""Customers page: satisfaction, repeat guests, cancellations and where guests come from."""

import streamlit as st

from config import CRIMSON, GOLD, OLIVE, REVENUE_NOTE
from db import query
from ui import bar_chart, page_title, revenue_bars, table, year_filter


def customers():
    page_title("Customers", "Who the guests are, how satisfied they leave, and who comes back.")
    year = year_filter("customers_year")
    t1, t2, t3, t4 = st.tabs(["Satisfaction", "Repeat guests", "Cancellations", "Where guests come from"])

    with t1:
        df = query("""
            SELECT ro.ro_type AS room_type, ROUND(AVG(r.re_rating), 2) AS average, COUNT(r.re_rating) AS ratings
            FROM reservation r JOIN room ro ON ro.ro_room_id = r.re_room_id
            WHERE r.re_rating IS NOT NULL AND (:yr = 0 OR EXTRACT(YEAR FROM r.re_check_in_date) = :yr)
            GROUP BY ro.ro_type ORDER BY average DESC""", year)
        dist = query("""
            SELECT re_rating AS stars, COUNT(*) AS reservations FROM reservation
            WHERE re_rating IS NOT NULL AND (:yr = 0 OR EXTRACT(YEAR FROM re_check_in_date) = :yr)
            GROUP BY re_rating ORDER BY re_rating""", year)
        total = int(dist["reservations"].sum()) if len(dist) else 0
        avg = (dist["stars"] * dist["reservations"]).sum() / total if total else 0
        k = st.columns(3)
        k[0].metric("Average rating", f"{avg:.2f} / 5")
        k[1].metric("Rated stays", total)
        k[2].metric("Ratings of 1 or 2", int(dist.loc[dist["stars"] <= 2, "reservations"].sum()) if total else 0)
        left, right = st.columns(2)
        with left:
            bar_chart(df, "room_type", "average", "Room type", "Average rating", color=OLIVE)
        with right:
            dist["stars"] = dist["stars"].astype(int).astype(str) + " ★"
            bar_chart(dist, "stars", "reservations", "Rating", "Reservations")
        st.caption("Only completed stays are rated. Ratings are entered on the Reservations page.")

    with t2:
        top = st.slider("How many guests to show", 5, 30, 10)
        df = query("""
            SELECT g.gu_name AS guest, g.gu_country AS country, COUNT(*) AS reservations,
                   SUM(r.re_nights) AS nights, SUM(r.re_total_amount) AS spent,
                   ROUND(AVG(r.re_rating), 1) AS rating
            FROM reservation r JOIN guest g ON g.gu_guest_id = r.re_guest_id
            WHERE r.re_status <> 'cancelled' AND (:yr = 0 OR EXTRACT(YEAR FROM r.re_check_in_date) = :yr)
            GROUP BY g.gu_guest_id, g.gu_name, g.gu_country
            ORDER BY reservations DESC, nights DESC
            FETCH FIRST :n ROWS ONLY""", {**year, "n": int(top)})
        bar_chart(df, "guest", "reservations", "Guest", "Reservations", horizontal=True, color=GOLD)
        table(df, money=["spent"], export="repeat_guests")

    with t3:
        df = query("""
            SELECT s.se_name AS season, s.se_start_date AS start_date,
                   SUM(CASE WHEN r.re_status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled, COUNT(*) AS total
            FROM reservation r JOIN season s ON s.se_season_id = r.re_season_id
            WHERE (:yr = 0 OR EXTRACT(YEAR FROM r.re_check_in_date) = :yr)
            GROUP BY s.se_season_id, s.se_name, s.se_start_date
            ORDER BY s.se_start_date""", year)
        total, cancelled = int(df["total"].sum()), int(df["cancelled"].sum())
        k = st.columns(3)
        k[0].metric("Reservations", total)
        k[1].metric("Cancelled", cancelled)
        k[2].metric("Cancellation rate", f"{100 * cancelled / total:.1f}%" if total else "—")
        df["cancel_pct"] = (100 * df["cancelled"] / df["total"]).round(1)
        bar_chart(df, "season", "cancel_pct", "Season", "Cancellation rate (%)", color=CRIMSON)
        table(df[["season", "cancelled", "total", "cancel_pct"]], export="cancellations")

    with t4:
        df = query("""
            SELECT g.gu_country AS country, COUNT(DISTINCT g.gu_guest_id) AS unique_guests, COUNT(*) AS reservations,
                   ROUND(AVG(r.re_nights), 1) AS avg_nights,
                   SUM(CASE WHEN r.re_status IN ('checked_out', 'in_house') THEN r.re_total_amount ELSE 0 END) AS earned,
                   SUM(CASE WHEN r.re_status = 'confirmed' THEN r.re_total_amount ELSE 0 END) AS on_the_books,
                   SUM(r.re_total_amount) AS total
            FROM reservation r JOIN guest g ON g.gu_guest_id = r.re_guest_id
            WHERE r.re_status <> 'cancelled' AND (:yr = 0 OR EXTRACT(YEAR FROM r.re_check_in_date) = :yr)
            GROUP BY g.gu_country ORDER BY total DESC""", year)
        revenue_bars(df, "country", "Country", horizontal=True)
        table(df, money=["earned", "on_the_books", "total"], export="guest_countries")
        st.caption(REVENUE_NOTE)
