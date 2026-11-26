"""Guests page: registration, search with history, and deletion."""

import datetime as dt
import re

import oracledb
import streamlit as st

from config import ID_FORMAT, TODAY
from db import execute_write, query, scalar, transaction
from rules import age, clean_id_number
from ui import cop_short, page_title, table

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def guests():
    page_title("Guests", "Register new guests or look up an existing guest's history.")
    register_tab, search_tab, delete_tab = st.tabs(["Register guest", "Search and history", "Delete guest"])

    with register_tab:
        register_guest()
    with delete_tab:
        delete_guest()
    with search_tab:
        search_guests()


def register_guest():
    with st.form("guest_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name *")
        country = c2.text_input("Country *", value="Colombia")
        c3, c4 = st.columns(2)
        id_type = c3.selectbox("ID type *", ["CC", "CE", "PAS"],
                               format_func={"CC": "CC · Colombian national ID", "CE": "CE · Foreign resident ID",
                                            "PAS": "PAS · Passport"}.get)
        id_number = c4.text_input("ID number *", help="You can type it with dots or spaces; the app removes them.")
        # Birth date with three lists. Only years for people between 18 and 100 are offered.
        # (Someone born in TODAY.year - 18 may not have turned 18 yet: the age check catches that.)
        years = list(range(TODAY.year - 18, TODAY.year - 101, -1))
        d1, d2, d3 = st.columns(3)
        birth_day = d1.selectbox("Birth day *", range(1, 32), index=0)
        birth_month = d2.selectbox("Birth month *", range(1, 13), index=0, format_func=lambda m: MONTHS[m - 1])
        birth_year = d3.selectbox("Birth year *", years, index=years.index(1990))
        c6, c7 = st.columns(2)
        email = c6.text_input("Email (optional)")
        phone = c7.text_input("Phone *", placeholder="+57 300 123 4567")
        submitted = st.form_submit_button("Register guest", type="primary")

    if not submitted:
        return
    errors = []
    try:
        birth_date = dt.date(birth_year, birth_month, birth_day)
    except ValueError:                      # for example, February 31
        birth_date = None
        errors.append(f"{MONTHS[birth_month - 1]} {birth_day}, {birth_year} isn't a real date.")
    id_number = clean_id_number(id_number)
    if not name.strip() or not id_number or not phone.strip() or not country.strip():
        errors.append("Fill in every field marked with *.")
    pattern, message = ID_FORMAT[id_type]
    if id_number and not re.fullmatch(pattern, id_number):
        errors.append(message)
    if birth_date and age(birth_date) < 18:
        errors.append(f"The guest is {age(birth_date)}. Guests must be 18 or older to register.")
    if id_number and scalar("SELECT COUNT(*) FROM guest WHERE gu_id_type = :id_type AND gu_id_number = :id_number",
                            {"id_type": id_type, "id_number": id_number}):
        errors.append(f"A guest with {id_type} {id_number} already exists.")
    if email.strip() and scalar("SELECT COUNT(*) FROM guest WHERE LOWER(gu_email) = LOWER(:email)",
                                {"email": email.strip()}):
        errors.append("Another guest already uses that email.")
    if errors:
        for e in errors:
            st.error(e)
        return
    try:
        with transaction() as cur:
            new_id = cur.var(oracledb.NUMBER)
            cur.execute("""
                INSERT INTO guest (gu_name, gu_id_type, gu_id_number, gu_birth_date, gu_email, gu_phone, gu_country)
                VALUES (:name, :id_type, :id_number, :birth_date, :email, :phone, :country)
                RETURNING gu_guest_id INTO :new_id""",
                {"name": name.strip(), "id_type": id_type, "id_number": id_number, "birth_date": birth_date,
                 "email": email.strip() or None, "phone": phone.strip(), "country": country.strip(), "new_id": new_id})
            guest_id = int(new_id.getvalue()[0])
        st.success(f"Guest registered with ID {guest_id}. You can now create their reservation.")
    except oracledb.DatabaseError as e:
        st.error(f"Oracle rejected the registration: {e}")


def search_guests():
    text = st.text_input("Name or ID number", placeholder="Restrepo or 1036654321")
    if len(text.strip()) < 3:
        st.caption("Type at least 3 characters.")
        return
    found = query("""
        SELECT gu_guest_id AS guest_id, gu_name AS name, gu_id_type AS id_type,
               gu_id_number AS id_number, gu_country AS country, gu_email AS email, gu_phone AS phone
        FROM guest
        WHERE gu_id_number = :id_number OR UPPER(gu_name) LIKE UPPER(:name_pattern)
        ORDER BY gu_name FETCH FIRST 50 ROWS ONLY""",
        {"id_number": clean_id_number(text), "name_pattern": f"%{text.strip()}%"})
    if found.empty:
        st.info("No guest found with that name or ID number.")
        return
    table(found, headers={"id_type": "ID type"})
    options = dict(zip(found["name"] + " · " + found["id_number"], found["guest_id"]))
    guest_id = int(options[st.selectbox("Show history for", list(options))])
    history = query("""
        SELECT r.re_reservation_id AS reservation, r.re_check_in_date AS check_in, r.re_check_out_date AS check_out,
               ro.ro_number AS room, ro.ro_type AS room_type, r.re_nights AS nights,
               r.re_total_amount AS amount, r.re_status AS status
        FROM reservation r JOIN room ro ON ro.ro_room_id = r.re_room_id
        WHERE r.re_guest_id = :guest_id
        ORDER BY r.re_check_in_date DESC""", {"guest_id": guest_id})
    valid = history[history["status"] != "cancelled"]
    k = st.columns(3)
    k[0].metric("Stays", len(valid))
    k[1].metric("Nights", int(valid["nights"].sum()) if len(valid) else 0)
    k[2].metric("Total spent", cop_short(valid["amount"].sum() if len(valid) else 0))
    if len(history):
        table(history, money=["amount"], dates=["check_in", "check_out"], export=f"history_{guest_id}")
    else:
        st.info("This guest has no reservations yet.")


def delete_guest():
    """Deletes a guest only if they have no reservations: the reservation foreign key protects their history."""
    st.caption("Only guests without reservations can be deleted, for example a record created by mistake.")
    c1, c2 = st.columns([1, 2])
    id_type = c1.selectbox("ID type", ["CC", "CE", "PAS"], key="delete_id_type")
    id_number = clean_id_number(c2.text_input("ID number", key="delete_id_number"))
    if not id_number:
        return
    g = query("""SELECT g.gu_guest_id AS guest_id, g.gu_name AS name, g.gu_country AS country,
                        (SELECT COUNT(*) FROM reservation r WHERE r.re_guest_id = g.gu_guest_id) AS reservations
                 FROM guest g WHERE g.gu_id_type = :id_type AND g.gu_id_number = :id_number""",
              {"id_type": id_type, "id_number": id_number})
    if g.empty:
        st.info(f"No guest has {id_type} {id_number}.")
        return
    g = g.iloc[0]
    st.write(f"**{g['name']}**, {g['country']}. Reservations on record: **{int(g['reservations'])}**.")
    if g["reservations"]:
        st.warning("This guest has reservations, so they can't be deleted: their history would be lost. "
                   "The database also prevents it with the reservation foreign key.")
        return
    confirmed = st.checkbox(f"I confirm I want to delete {g['name']}", key="confirm_delete_guest")
    if st.button("Delete guest", disabled=not confirmed):
        execute_write("DELETE FROM guest WHERE gu_guest_id = :id", {"id": int(g["guest_id"])},
                      f"{g['name']} was deleted.", "The guest no longer existed.")
