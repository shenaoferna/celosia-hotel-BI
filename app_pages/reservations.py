"""Reservations page: filters, check-in, check-out, cancellation, changes and ratings."""

import datetime as dt

import oracledb
import pandas as pd
import streamlit as st

from config import MINORS_RULE, ROOM_TYPE_LABEL, STATUSES, STATUS_LABEL, TODAY, party
from db import error_message, execute_write, query, transaction
from rules import check_in, check_out, clean_id_number
from ui import cop, cop_short, page_title, table


def reservations():
    page_title("Reservations",
               "Find a reservation and manage it: check-in, check-out, date or room changes, and cancellation.")

    c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
    date_range = c1.date_input("Arrival between", value=(TODAY - dt.timedelta(days=30), TODAY + dt.timedelta(days=60)),
                               format="MM/DD/YYYY")
    statuses = c2.multiselect("Status", STATUSES, default=["confirmed", "in_house"], format_func=STATUS_LABEL.get)
    room = c3.text_input("Room", placeholder="402")
    search = c4.text_input("Guest (name or ID number)")
    if not isinstance(date_range, tuple) or len(date_range) != 2:
        st.caption("Choose the end date of the range.")
        return

    sql = """SELECT r.re_reservation_id AS reservation, g.gu_name AS guest, g.gu_id_number AS id_number,
                    ro.ro_number AS room, ro.ro_type AS room_type, s.se_name AS season,
                    r.re_check_in_date AS check_in, r.re_check_out_date AS check_out, r.re_nights AS nights,
                    r.re_guests AS guests, r.re_children AS children, r.re_total_amount AS amount, r.re_status AS status,
                    r.re_channel AS channel, r.re_rating AS rating,
                    r.re_check_in_time AS check_in_time, r.re_check_out_time AS check_out_time
             FROM reservation r
             JOIN guest g   ON g.gu_guest_id = r.re_guest_id
             JOIN room ro   ON ro.ro_room_id = r.re_room_id
             JOIN season s  ON s.se_season_id = r.re_season_id
             WHERE r.re_check_in_date BETWEEN :date_from AND :date_to
               AND (:statuses IS NULL OR INSTR(:statuses, ',' || r.re_status || ',') > 0)
               AND (:room IS NULL OR ro.ro_number = :room)
               AND (:id_number IS NULL OR g.gu_id_number = :id_number OR UPPER(g.gu_name) LIKE UPPER(:name_pattern))
             ORDER BY r.re_check_in_date DESC
             FETCH FIRST 500 ROWS ONLY"""
    # Empty filters are sent as NULL, so their condition doesn't filter anything.
    params = {"date_from": date_range[0], "date_to": date_range[1],
              "statuses": ("," + ",".join(statuses) + ",") if statuses else None,
              "room": room.strip() or None,
              "id_number": clean_id_number(search) or None, "name_pattern": f"%{search.strip()}%"}
    df = query(sql, params)

    k = st.columns(3)
    k[0].metric("Reservations found", len(df))
    k[1].metric("Nights", int(df["nights"].sum()) if len(df) else 0)
    k[2].metric("Amount (excluding cancelled)",
                cop_short(df.loc[df["status"] != "cancelled", "amount"].sum() if len(df) else 0))
    if df.empty:
        st.info("No reservations match those filters.")
    else:
        table(df, money=["amount"], dates=["check_in", "check_out"], times=["check_in_time", "check_out_time"],
              export="reservations")

    st.subheader("Manage a reservation")
    number = st.number_input("Reservation number", min_value=1, step=1, value=None, placeholder="2081")
    if number is None:
        return
    r = query("""SELECT r.re_reservation_id, r.re_status, r.re_check_in_date, r.re_check_out_date, r.re_adults, r.re_children,
                        r.re_room_id, r.re_total_amount, r.re_rating, r.re_check_in_time,
                        r.re_check_out_time, g.gu_name, ro.ro_number
                 FROM reservation r JOIN guest g ON g.gu_guest_id = r.re_guest_id
                 JOIN room ro ON ro.ro_room_id = r.re_room_id
                 WHERE r.re_reservation_id = :id""", {"id": int(number)})
    if r.empty:
        st.warning("There's no reservation with that number.")
        return
    r = r.iloc[0]
    res_id = int(number)
    departure = pd.to_datetime(r["re_check_out_date"]).date()
    arrival = pd.to_datetime(r["re_check_in_date"]).date()
    status = r["re_status"]
    fmt_time = lambda v: pd.to_datetime(v).strftime("%b %d, %Y %H:%M") if pd.notna(v) else "—"
    st.write(f"**{r['gu_name']}**, room {r['ro_number']}, {arrival:%b %d, %Y} to {departure:%b %d, %Y}, "
             f"{party(r['re_adults'], r['re_children'])}. "
             f"Status: **{STATUS_LABEL.get(status, status)}**.")
    if status in ("in_house", "checked_out"):
        st.caption(f"Check-in: {fmt_time(r['re_check_in_time'])}   Check-out: {fmt_time(r['re_check_out_time'])}")

    if status == "cancelled":
        st.caption("Cancelled reservations can't change status.")
        return

    if status == "checked_out":
        if pd.notna(r["re_rating"]):
            st.caption(f"Guest rating: {int(r['re_rating'])} / 5")
            return
        rating = st.select_slider("Guest rating", options=[1, 2, 3, 4, 5], value=4)
        if st.button("Save rating", type="primary"):
            execute_write("""UPDATE reservation SET re_rating = :rating
                             WHERE re_reservation_id = :id AND re_status = 'checked_out' AND re_rating IS NULL""",
                          {"rating": rating, "id": res_id}, f"Rating {rating} / 5 saved.",
                          "The reservation already had a rating or isn't checked out.")
        return

    if status == "in_house":
        if departure > TODAY:
            st.info(f"The guest has the room until {departure:%b %d}. If they leave early, the full stay is still charged.")
        st.button("Check out", type="primary", on_click=check_out, args=(res_id,))
        return

    # ---- confirmed: check-in, cancel or change ----
    verified = True
    if r["re_children"] and arrival <= TODAY < departure:     # minors: documents first, then check-in
        st.warning(MINORS_RULE, icon=":material/child_care:")
        verified = st.checkbox("Minors' documents verified", key=f"docs_{res_id}")
    b1, b2 = st.columns(2)
    can_check_in = arrival <= TODAY < departure
    b1.button("Check in", type="primary", disabled=not (can_check_in and verified), on_click=check_in, args=(res_id,),
              help=(f"Check-in opens on {arrival:%b %d, %Y}." if not can_check_in
                    else None if verified else "Verify the minors' documents first."))
    if b2.button("Cancel reservation"):
        execute_write("UPDATE reservation SET re_status = 'cancelled' WHERE re_reservation_id = :id AND re_status = 'confirmed'",
                      {"id": res_id}, f"Reservation {res_id} cancelled.", "The reservation was no longer confirmed.")
        return

    with st.expander("Change dates, guests or room"):
        change_reservation(res_id, arrival, departure, int(r["re_adults"]), int(r["re_children"]),
                           int(r["re_room_id"]), float(r["re_total_amount"]))


def change_reservation(res_id, arrival, departure, adults, children, current_room, current_amount):
    """Changes a confirmed reservation by applying the rules again: availability, capacity, season and amount."""
    c1, c2, c3, c4 = st.columns([1, 1, 0.6, 0.6])
    new_in = c1.date_input("New check-in", value=max(arrival, TODAY), min_value=TODAY, format="MM/DD/YYYY",
                           key=f"m_in_{res_id}")
    new_out = c2.date_input("New check-out", value=max(departure, new_in + dt.timedelta(days=1)), format="MM/DD/YYYY",
                            key=f"m_out_{res_id}")
    new_adults = c3.number_input("Adults", min_value=1, max_value=6, value=adults, key=f"m_adults_{res_id}")
    new_children = c4.number_input("Children", min_value=0, max_value=5, value=children, key=f"m_children_{res_id}")
    new_guests = int(new_adults) + int(new_children)
    nights = (new_out - new_in).days
    if nights <= 0:
        st.error("The check-out date must be after the check-in date.")
        return
    if new_guests > 6:
        st.error("The largest room holds 6 guests.")
        return
    season = query("""SELECT se_season_id, se_name, se_surcharge FROM season
                      WHERE :check_in BETWEEN se_start_date AND se_end_date""", {"check_in": new_in})
    if season.empty:
        st.error("There's no season for that check-in date. Create it on the Seasons page.")
        return
    season = season.iloc[0]
    surcharge = float(season["se_surcharge"])
    # rooms free on the new dates, not counting this same reservation
    available = query("""
        SELECT ro.ro_room_id, ro.ro_number, ro.ro_type, ro.ro_capacity, ro.ro_nightly_rate
        FROM room ro
        WHERE ro.ro_status = 'active' AND ro.ro_capacity >= :guests
          AND NOT EXISTS (SELECT 1 FROM reservation r
                          WHERE r.re_room_id = ro.ro_room_id AND r.re_status <> 'cancelled'
                            AND r.re_reservation_id <> :id
                            AND r.re_check_in_date < :check_out AND r.re_check_out_date > :check_in)
        ORDER BY CASE WHEN ro.ro_room_id = :current_room THEN 0 ELSE 1 END, ro.ro_nightly_rate""",
        {"guests": new_guests, "id": res_id, "check_out": new_out, "check_in": new_in, "current_room": current_room})
    if available.empty:
        st.warning("No rooms with that capacity are free on those dates.")
        return
    available["total_amount"] = (available["ro_nightly_rate"].astype(float) * nights * (1 + surcharge / 100)).round(2)
    options = {f"{x.ro_number} ({ROOM_TYPE_LABEL.get(x.ro_type, x.ro_type)}, up to {x.ro_capacity}): {cop(x.total_amount)}"
               + ("  · current" if x.ro_room_id == current_room else ""): x for x in available.itertuples()}
    chosen = options[st.selectbox("Room", list(options), key=f"m_room_{res_id}")]
    k = st.columns(3)
    k[0].metric("Season", season["se_name"])
    k[1].metric("Nights", nights)
    k[2].metric("New amount", cop(chosen.total_amount), f"{cop(chosen.total_amount - current_amount)} difference",
                delta_color="off")
    if st.button("Save changes", type="primary", key=f"m_ok_{res_id}"):
        try:
            with transaction() as cur:
                cur.execute("""SELECT COUNT(*) FROM reservation WHERE re_room_id = :room_id AND re_status <> 'cancelled'
                               AND re_reservation_id <> :id AND re_check_in_date < :check_out
                               AND re_check_out_date > :check_in""",
                            {"room_id": int(chosen.ro_room_id), "id": res_id, "check_out": new_out, "check_in": new_in})
                if cur.fetchone()[0] > 0:
                    raise ValueError("That room was just booked for those dates. Pick another one.")
                cur.execute("""UPDATE reservation
                               SET re_check_in_date = :check_in, re_check_out_date = :check_out, re_nights = :nights,
                                   re_adults = :adults, re_children = :children, re_room_id = :room_id, re_season_id = :season_id,
                                   re_total_amount = :amount
                               WHERE re_reservation_id = :id AND re_status = 'confirmed'""",
                            {"check_in": new_in, "check_out": new_out, "nights": nights, "adults": int(new_adults), "children": int(new_children),
                             "room_id": int(chosen.ro_room_id), "season_id": int(season["se_season_id"]),
                             "amount": float(chosen.total_amount), "id": res_id})
                ok = cur.rowcount
            if ok:
                st.success(f"Reservation {res_id} updated.")
            else:
                st.warning("The reservation was no longer confirmed.")
        except ValueError as e:
            st.error(str(e))
        except oracledb.IntegrityError:
            st.error("That room already has another reservation (even if cancelled) with the same check-in date.")
        except oracledb.Error as e:
            st.error(error_message(e))
