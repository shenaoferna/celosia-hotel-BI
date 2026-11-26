"""New reservation page: guest, date search, cards for the available rooms, and confirmation."""

import datetime as dt

import oracledb
import pandas as pd
import streamlit as st

from config import CHANNEL_LABEL, CHANNELS, MINORS_RULE, ROOM_TYPE_LABEL, TODAY, party
from db import query, transaction
from risk import ACTION, current_model, guest_history, new_booking_row, score
from rules import ROOM_OPEN_SQL, age, guest_by_id_number
from ui import badge, cop, icon, page_title

# How each room type looks on its card: icon, background and icon color
ROOM_TYPE_STYLE = {
    "single": ("single_bed", "#F3EEE3", "#1C1C1C"),
    "double": ("bed", "#F3EEE3", "#1C1C1C"),
    "suite": ("king_bed", "#F3EBD8", "#5E4615"),
    "family": ("family_restroom", "#E4EADF", "#3D5439"),
}
CARDS_PER_ROW = 3


def risk_by_room(guest, guest_age, check_in, nights, guests, surcharge, channel, rooms):
    """Cancellation risk level of the reservation in each given room. If it can't be calculated, {}."""
    try:
        info = current_model()
        if info is None:
            return {}, None
        stays, cancellations = guest_history(guest["gu_guest_id"], TODAY)
        rows = pd.concat([new_booking_row((check_in - TODAY).days, nights, guests, r.total_amount, surcharge,
                                          guest_age, stays, cancellations, guest["gu_country"], channel,
                                          r.ro_type, check_in)
                          for r in rooms.itertuples()], ignore_index=True)
        levels = score(info, rows)[1]
        return dict(zip(rooms["ro_room_id"].astype(int), levels)), info
    except Exception:
        return {}, None


def risk_message(level, info):
    """Risk message before confirming, with the recommended action."""
    if not level or info is None:
        st.caption("The cancellation risk couldn't be calculated right now.")
        return
    text = (f"**Cancellation risk: {level.lower()}.** In the hotel's history, "
            f"{info['rates'][level] * 100:.0f} of every 100 reservations at this risk level were cancelled "
            f"(the average is {info['overall_rate'] * 100:.0f}). {ACTION[level]}")
    {"High": st.warning, "Medium": st.info, "Low": st.success}[level](text, icon=":material/query_stats:")


def choose(room_id):
    st.session_state.nr_room = room_id


def room_card(r, nights, chosen):
    """One available room as a card: 'photo' with an icon, details, price and button."""
    symbol, background, color = ROOM_TYPE_STYLE.get(r.ro_type, ("hotel", "#F3EEE3", "#1C1C1C"))
    room_id = int(r.ro_room_id)
    key = f"chosen_{room_id}" if chosen else f"room_card_{room_id}"
    html = (f'<div class="photo" style="background:{background}">{icon(symbol, 52, color)}</div>'
            f'<p class="room-title">{r.ro_number} · {ROOM_TYPE_LABEL.get(r.ro_type, r.ro_type)}</p>'
            f'<p class="room-detail">{icon("group", 16)} up to {int(r.ro_capacity)} guests &nbsp;·&nbsp; '
            f'{icon("stairs", 16)} floor {int(r.ro_floor)}</p>'
            f'<p class="room-price">{cop(r.total_amount)}<br>'
            f'<small>{nights} night(s) · {cop(float(r.ro_nightly_rate))} per night</small></p>')
    with st.container(key=key):
        st.markdown(html, unsafe_allow_html=True)
        if chosen:
            st.button("Selected", key=f"btn_{room_id}", icon=":material/check_circle:", use_container_width=True,
                      on_click=choose, args=(room_id,))
        else:
            st.button("Book", key=f"btn_{room_id}", type="primary", use_container_width=True,
                      on_click=choose, args=(room_id,))


def new_reservation():
    page_title("New reservation", "Find the guest, choose the dates and pick one of the available rooms.")

    # ---- Step 1: guest ----
    st.subheader("1. Guest")
    id_number = st.text_input("ID number", placeholder="1036654321")
    if not id_number.strip():
        st.caption("If the guest is new, register them first on the Guests page.")
        return
    g = guest_by_id_number(id_number)
    if g.empty:
        st.warning("No guest has that ID number. Register them on the Guests page and come back here.")
        return
    if len(g) > 1:     # the same number with two different ID types (for example, CC and PAS)
        types = list(g["gu_id_type"])
        g = g[g["gu_id_type"] == st.radio("More than one guest has that number. Which ID type is it?",
                                          types, horizontal=True)]
    g = g.iloc[0]
    birth_date = pd.to_datetime(g["gu_birth_date"]).date() if pd.notna(g["gu_birth_date"]) else None
    guest_age = age(birth_date) if birth_date else None
    st.success(f"**{g['gu_name']}** · {g['gu_id_type']} {g['gu_id_number']} · {g['gu_country']}"
               + (f" · {guest_age} years old" if guest_age is not None else ""), icon=":material/person:")
    if guest_age is not None and guest_age < 18:     # the guest must be an adult
        st.error("The guest is under 18. Only an adult can make a reservation.")
        return

    # ---- Step 2: date and guest search ----
    st.subheader("2. Dates and guests")
    with st.container(key="search_box"):
        c1, c2, c3, c3b, c4 = st.columns([1, 1, 0.7, 0.7, 1.5])
        check_in = c1.date_input("Check-in", value=TODAY, min_value=TODAY, format="MM/DD/YYYY")
        check_out = c2.date_input("Check-out", value=check_in + dt.timedelta(days=1), min_value=TODAY,
                                  format="MM/DD/YYYY")
        adults = c3.number_input("Adults", min_value=1, max_value=6, value=1)
        children = c3b.number_input("Children", min_value=0, max_value=5, value=0, help="Guests under 18.")
        channel = c4.selectbox("Booking channel", list(CHANNELS), format_func=CHANNELS.get,
                               index=3 if check_in == TODAY else 0)
    nights = (check_out - check_in).days
    if nights <= 0:
        st.error("The check-out date must be after the check-in date.")
        return
    guests = int(adults) + int(children)      # the room's capacity counts everyone, adults and children
    if guests > 6:
        st.error("The largest room holds 6 guests. Split the group into two reservations.")
        return

    # The check-in date determines the season
    season = query("""SELECT se_season_id, se_name, se_surcharge FROM season
                      WHERE :check_in BETWEEN se_start_date AND se_end_date""", {"check_in": check_in})
    if season.empty:
        st.error("There's no season for that check-in date. Create it on the Seasons page.")
        return
    season = season.iloc[0]
    surcharge = float(season["se_surcharge"])

    # If the search changes, forget the room chosen before
    search = (int(g["gu_guest_id"]), check_in, check_out, int(adults), int(children), channel)
    if st.session_state.get("nr_search") != search:
        st.session_state.nr_search = search
        st.session_state.nr_room = None

    # ---- Step 3: available rooms (active, big enough and with no overlapping dates) ----
    available = query("""
        SELECT ro.ro_room_id, ro.ro_number, ro.ro_type, ro.ro_capacity, ro.ro_floor, ro.ro_nightly_rate
        FROM room ro
        WHERE """ + ROOM_OPEN_SQL + """
          AND ro.ro_capacity >= :guests
          AND NOT EXISTS (SELECT 1 FROM reservation r
                          WHERE r.re_room_id = ro.ro_room_id
                            AND r.re_status <> 'cancelled'
                            AND r.re_check_in_date < :check_out
                            AND r.re_check_out_date > :check_in)
        ORDER BY ro.ro_nightly_rate, ro.ro_number""", {"guests": guests, "check_out": check_out, "check_in": check_in})
    st.subheader(f"3. Available rooms ({len(available)})")
    st.markdown(f'{badge(season["se_name"], "checked_out")} &nbsp; season surcharge {surcharge:.0f}% · '
                f'{nights} night(s) · {party(adults, children)}', unsafe_allow_html=True)
    if available.empty:
        st.warning("No rooms with that capacity are free on those dates. Try other dates or fewer guests.")
        return
    # Total amount = nightly rate × nights × (1 + surcharge / 100)
    available["total_amount"] = (available["ro_nightly_rate"].astype(float) * nights * (1 + surcharge / 100)).round(2)

    types = ["all"] + sorted(available["ro_type"].unique())
    type_filter = st.radio("Room type", types, horizontal=True, label_visibility="collapsed",
                           format_func=lambda t: "All rooms" if t == "all" else ROOM_TYPE_LABEL.get(t, t))
    view = available if type_filter == "all" else available[available["ro_type"] == type_filter]

    chosen_id = st.session_state.get("nr_room")
    for start in range(0, len(view), CARDS_PER_ROW):
        row = view.iloc[start:start + CARDS_PER_ROW]
        for col, r in zip(st.columns(CARDS_PER_ROW), row.itertuples()):
            with col:
                room_card(r, nights, chosen=int(r.ro_room_id) == chosen_id)

    if chosen_id is None or chosen_id not in set(available["ro_room_id"].astype(int)):
        st.caption("Pick a room with its Book button to continue.")
        return
    chosen_rows = available[available["ro_room_id"].astype(int) == chosen_id]
    chosen = next(chosen_rows.itertuples())
    risks, info = risk_by_room(g, guest_age, check_in, nights, guests, surcharge, channel, chosen_rows)

    # ---- Step 4: confirm ----
    st.subheader("4. Confirm")
    with st.container(key="confirm_box"):
        st.markdown(f"**{g['gu_name']}** · room **{chosen.ro_number}** "
                    f"({ROOM_TYPE_LABEL.get(chosen.ro_type, chosen.ro_type)}) · "
                    f"**{check_in:%b %d, %Y}** to **{check_out:%b %d, %Y}** · {party(adults, children)} · "
                    f"{CHANNEL_LABEL.get(channel, channel)}")
        k = st.columns(4)
        k[0].metric("Room", chosen.ro_number)
        k[1].metric("Nightly rate", cop(chosen.ro_nightly_rate))
        k[2].metric("Nights", nights)
        k[3].metric("Total", cop(chosen.total_amount))
        risk_message(risks.get(chosen_id), info)
        if children:
            minors = f"{int(children)} minor{'s' if children != 1 else ''}"
            st.info(f"**This reservation includes {minors}.** {MINORS_RULE}",
                    icon=":material/child_care:")

        if st.button("Confirm reservation", type="primary", icon=":material/event_available:"):
            try:
                with transaction() as cur:
                    # check again right before saving, in case someone took the room in the meantime
                    cur.execute("""SELECT COUNT(*) FROM reservation
                                   WHERE re_room_id = :room_id AND re_status <> 'cancelled'
                                     AND re_check_in_date < :check_out AND re_check_out_date > :check_in""",
                                {"room_id": int(chosen.ro_room_id), "check_out": check_out, "check_in": check_in})
                    if cur.fetchone()[0] > 0:
                        raise ValueError("That room was just booked for those dates. Pick another one.")
                    new_id = cur.var(oracledb.NUMBER)
                    cur.execute("""
                        INSERT INTO reservation (re_guest_id, re_room_id, re_season_id, re_booking_date,
                                                 re_check_in_date, re_check_out_date, re_nights, re_adults, re_children,
                                                 re_total_amount, re_status, re_channel)
                        VALUES (:guest_id, :room_id, :season_id, :booked, :check_in, :check_out, :nights, :adults, :children,
                                :amount, 'confirmed', :channel)
                        RETURNING re_reservation_id INTO :new_id""",
                        {"guest_id": int(g["gu_guest_id"]), "room_id": int(chosen.ro_room_id),
                         "season_id": int(season["se_season_id"]), "booked": TODAY, "check_in": check_in,
                         "check_out": check_out, "nights": nights, "adults": int(adults), "children": int(children),
                         "amount": float(chosen.total_amount), "channel": channel, "new_id": new_id})
                    number = int(new_id.getvalue()[0])
                st.session_state.nr_room = None
                st.success(f"Reservation confirmed. Reservation number: **{number}**.", icon=":material/celebration:")
                st.balloons()
            except ValueError as e:
                st.error(str(e))
            except oracledb.IntegrityError:
                st.error("That room already has a reservation (even if cancelled) with the same check-in date. "
                         "Pick another room or change the check-in date.")
            except oracledb.DatabaseError as e:
                st.error(f"Oracle rejected the reservation: {e}")
