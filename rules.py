"""Business rules that can't be CHECK constraints: age, ID format and front-desk operations."""

import datetime as dt
import re

import oracledb
import streamlit as st

from config import TODAY
from db import error_message, query, transaction


# A room can be sold for a stay if it's active, or if its maintenance ends on or before the check-in date.
# Use it in a query that has the room as "ro" and a :check_in bind variable.
ROOM_OPEN_SQL = "(ro.ro_status = 'active' OR ro.ro_back_in_service <= :check_in)"


def age(birth_date, ref=TODAY):
    return ref.year - birth_date.year - ((ref.month, ref.day) < (birth_date.month, birth_date.day))


def clean_id_number(text):
    """Removes dots, spaces and dashes, and converts to uppercase: '1.036.654.321' -> '1036654321'."""
    return re.sub(r"[\s.\-]", "", text or "").upper()


def guest_by_id_number(id_number):
    return query("""SELECT gu_guest_id, gu_name, gu_id_type, gu_id_number,
                           gu_birth_date, gu_email, gu_phone, gu_country
                    FROM guest WHERE gu_id_number = :d
                    ORDER BY gu_id_type""", {"d": clean_id_number(id_number)})


def same_day_last_year(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:            # February 29
        return d.replace(year=d.year - 1, day=28)


def check_in(reservation_id):
    try:
        with transaction() as cur:
            cur.execute("""UPDATE reservation SET re_status = 'in_house', re_check_in_time = :t
                           WHERE re_reservation_id = :id AND re_status = 'confirmed'
                             AND re_check_in_date <= :today AND re_check_out_date > :today""",
                        {"t": dt.datetime.now().replace(microsecond=0), "id": int(reservation_id), "today": TODAY})
            ok = cur.rowcount
    except oracledb.Error as e:
        st.toast(error_message(e))
        return
    st.toast(f"Reservation {reservation_id} checked in." if ok else
             f"Couldn't check in reservation {reservation_id}: it's no longer confirmed.")


def check_out(reservation_id):
    try:
        with transaction() as cur:
            cur.execute("""UPDATE reservation SET re_status = 'checked_out', re_check_out_time = :t
                           WHERE re_reservation_id = :id AND re_status = 'in_house'""",
                        {"t": dt.datetime.now().replace(microsecond=0), "id": int(reservation_id)})
            ok = cur.rowcount
    except oracledb.Error as e:
        st.toast(error_message(e))
        return
    st.toast(f"Reservation {reservation_id} checked out." if ok else
             f"Reservation {reservation_id} wasn't in house.")
