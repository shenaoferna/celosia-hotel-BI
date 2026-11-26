"""Seasons page: view, create and delete seasons."""

import datetime as dt

import oracledb
import pandas as pd
import streamlit as st

from config import TODAY
from db import error_message, execute_write, query, scalar, transaction
from ui import page_title, table


def seasons():
    page_title("Seasons", "Periods of the year and their surcharge. Each reservation takes the season of its "
                          "check-in date.")
    df = query("""SELECT se_name AS season, se_start_date AS start_date, se_end_date AS end_date,
                         se_surcharge AS surcharge FROM season ORDER BY se_start_date""")
    df["surcharge"] = df["surcharge"].map(lambda v: f"{float(v):.0f} %")
    table(df, dates=["start_date", "end_date"], export="seasons")
    last_end = pd.to_datetime(df["end_date"]).max().date() if len(df) else TODAY

    st.subheader("Create a season")
    with st.form("season_form"):
        name = st.text_input("Name", placeholder="Holy Week 2027")
        c1, c2, c3 = st.columns(3)
        start = c1.date_input("Start", value=last_end + dt.timedelta(days=1), format="MM/DD/YYYY")
        end = c2.date_input("End", value=last_end + dt.timedelta(days=8), format="MM/DD/YYYY")
        surcharge = c3.number_input("Surcharge (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0)
        create = st.form_submit_button("Create season", type="primary")
    if create:
        if not name.strip():
            st.error("Enter a name for the season.")
        elif end <= start:
            st.error("The end date must be after the start date.")
        elif scalar("SELECT COUNT(*) FROM season WHERE :start_date <= se_end_date AND :end_date >= se_start_date",
                    {"start_date": start, "end_date": end}):
            st.error("Those dates overlap another season. Each day must belong to exactly one season.")
        else:
            try:
                with transaction() as cur:
                    cur.execute("""INSERT INTO season (se_name, se_start_date, se_end_date, se_surcharge)
                                   VALUES (:name, :start_date, :end_date, :surcharge)""",
                                {"name": name.strip(), "start_date": start, "end_date": end, "surcharge": surcharge})
                st.success(f"Season “{name.strip()}” created.")
                st.rerun()
            except oracledb.IntegrityError:
                st.error("A season with that name already exists.")
            except oracledb.Error as e:
                st.error(error_message(e))

    # ---- Delete: only seasons without reservations (the reservation FK protects the ones in use) ----
    st.subheader("Delete a season")
    season_list = query("""
        SELECT s.se_season_id AS id, s.se_name AS season, COUNT(r.re_reservation_id) AS reservations
        FROM season s LEFT JOIN reservation r ON r.re_season_id = s.se_season_id
        GROUP BY s.se_season_id, s.se_name, s.se_start_date
        ORDER BY s.se_start_date""")
    options = {f"{x.season} ({x.reservations} reservations)": x for x in season_list.itertuples()}
    chosen = options[st.selectbox("Season", list(options), key="delete_season")]
    if chosen.reservations:
        st.caption("This season has reservations, so it can't be deleted: they would lose their season.")
    else:
        confirm = st.checkbox(f"I confirm I want to delete “{chosen.season}”", key="confirm_delete_season")
        if st.button("Delete season", disabled=not confirm):
            if execute_write("DELETE FROM season WHERE se_season_id = :id", {"id": int(chosen.id)},
                             f"Season “{chosen.season}” deleted."):
                st.rerun()
