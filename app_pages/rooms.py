"""Rooms page: today's situation and service status."""

import streamlit as st

from config import TODAY
from db import execute_write, query, scalar
from ui import page_title, table


def rooms():
    page_title("Rooms", "Each room's status today, and switching rooms to maintenance.")
    df = query("""
        SELECT ro.ro_room_id AS id, ro.ro_number AS room, ro.ro_type AS room_type, ro.ro_capacity AS capacity,
               ro.ro_floor AS floor, ro.ro_nightly_rate AS nightly_rate, ro.ro_status AS status,
               CASE WHEN ro.ro_status = 'maintenance' THEN 'Maintenance'
                    WHEN EXISTS (SELECT 1 FROM reservation r
                                 WHERE r.re_room_id = ro.ro_room_id AND r.re_status <> 'cancelled'
                                   AND r.re_check_in_date <= :today AND r.re_check_out_date > :today) THEN 'Occupied'
                    ELSE 'Free' END AS today
        FROM room ro ORDER BY ro.ro_floor, ro.ro_number""", {"today": TODAY})
    counts = df["today"].value_counts()
    k = st.columns(3)
    k[0].metric("Free today", int(counts.get("Free", 0)))
    k[1].metric("Occupied today", int(counts.get("Occupied", 0)))
    k[2].metric("In maintenance", int(counts.get("Maintenance", 0)))
    table(df.drop(columns=["id"]), money=["nightly_rate"], export="rooms")

    st.subheader("Change a room's status")
    c1, c2 = st.columns(2)
    number = c1.selectbox("Room", df["room"])
    row = df[df["room"] == number].iloc[0]
    new_status = "maintenance" if row["status"] == "active" else "active"
    c2.write("")
    c2.write(f"Current status: **{'Active' if row['status'] == 'active' else 'Maintenance'}**")
    upcoming = scalar("""SELECT COUNT(*) FROM reservation WHERE re_room_id = :id
                         AND re_status IN ('confirmed', 'in_house') AND re_check_out_date > :today""",
                      {"id": int(row["id"]), "today": TODAY})
    if new_status == "maintenance" and upcoming:
        st.warning(f"Room {number} has {int(upcoming)} upcoming reservation(s) or a guest in house. Move them to "
                   "another room on the Reservations page (Change dates, guests or room) before setting it to "
                   "maintenance.")
        return
    if st.button(f"Set to {new_status}", type="primary"):
        if execute_write("UPDATE room SET ro_status = :new_status WHERE ro_room_id = :id",
                         {"new_status": new_status, "id": int(row["id"])}, f"Room {number} is now {new_status}."):
            st.rerun()
