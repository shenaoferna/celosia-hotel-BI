"""Rooms page: today's situation, and maintenance with a back-in-service date."""

import datetime as dt

import pandas as pd
import streamlit as st

from config import TODAY
from db import execute_write, query, scalar, transaction
from ui import page_title, table


def reactivate_finished_maintenance():
    """Rooms whose maintenance date has arrived go back to active on their own."""
    with transaction() as cur:
        cur.execute("""UPDATE room SET ro_status = 'active', ro_back_in_service = NULL
                       WHERE ro_status = 'maintenance' AND ro_back_in_service <= :today""", {"today": TODAY})


def rooms():
    page_title("Rooms", "Each room's status today, and maintenance with the date it's back in service.")
    reactivate_finished_maintenance()
    df = query("""
        SELECT ro.ro_room_id AS id, ro.ro_number AS room, ro.ro_type AS room_type, ro.ro_capacity AS capacity,
               ro.ro_floor AS floor, ro.ro_nightly_rate AS nightly_rate, ro.ro_status AS status,
               ro.ro_back_in_service AS back_in_service,
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
    table(df.drop(columns=["id"]), money=["nightly_rate"], dates=["back_in_service"], export="rooms")

    st.subheader("Maintenance")
    c1, c2 = st.columns(2)
    number = c1.selectbox("Room", df["room"])
    row = df[df["room"] == number].iloc[0]
    room_id = int(row["id"])
    in_maintenance = row["status"] == "maintenance"
    current_back = pd.to_datetime(row["back_in_service"]).date() if in_maintenance else None
    c2.write("")
    c2.write(f"Current status: **Maintenance until {current_back:%b %d, %Y}**" if in_maintenance
             else "Current status: **Active**")

    back = st.date_input("Back in service on", value=current_back or TODAY + dt.timedelta(days=7),
                         min_value=TODAY + dt.timedelta(days=1), format="MM/DD/YYYY",
                         help="The first day the room can be sold again. Until then it's not offered.")
    # Reservations that fall inside the maintenance window block it: move them first
    clashes = scalar("""SELECT COUNT(*) FROM reservation WHERE re_room_id = :id
                        AND re_status IN ('confirmed', 'in_house')
                        AND re_check_in_date < :back AND re_check_out_date > :today""",
                     {"id": room_id, "back": back, "today": TODAY})
    if clashes:
        st.warning(f"Room {number} has {int(clashes)} reservation(s) or a guest in house before {back:%b %d, %Y}. "
                   "Move them to another room on the Reservations page (Change dates, guests or room), "
                   "or choose an earlier date.")

    b1, b2 = st.columns(2)
    label = "Change the date" if in_maintenance else f"Set to maintenance until {back:%b %d}"
    if b1.button(label, type="primary", disabled=bool(clashes)):
        if execute_write("""UPDATE room SET ro_status = 'maintenance', ro_back_in_service = :back
                            WHERE ro_room_id = :id""", {"back": back, "id": room_id},
                         f"Room {number} is in maintenance until {back:%b %d, %Y}."):
            st.rerun()
    if in_maintenance and b2.button("Back in service today"):
        if execute_write("""UPDATE room SET ro_status = 'active', ro_back_in_service = NULL
                            WHERE ro_room_id = :id""", {"id": room_id}, f"Room {number} is active again."):
            st.rerun()
