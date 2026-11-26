"""Cancellation risk page: confirmed reservations ranked by risk, and how the model works."""

import datetime as dt

import pandas as pd
import streamlit as st

from config import CHANNEL_LABEL, INK, TODAY
from risk import ACTION, LEVELS, current_model, load_history, score
from ui import bar_chart, cop, page_title, table


def thousands(n):
    """1234 -> '1,234'."""
    return f"{int(n):,}"


def cancellation_risk():
    page_title("Cancellation risk",
               "Confirmed reservations most likely to be cancelled, so you can act before the guest arrives.")
    info = current_model()
    if info is None:
        st.info("There isn't enough history to train the model yet. It needs at least 200 completed or cancelled "
                "reservations, including 20 cancellations.")
        return

    data = load_history()
    upcoming = data[(data["re_status"] == "confirmed") & (data["re_check_in_date"].dt.date >= TODAY)].copy()
    t1, t2 = st.tabs(["Upcoming reservations", "How the model works"])

    with t1:
        if upcoming.empty:
            st.info("There are no upcoming confirmed reservations.")
        else:
            _upcoming_reservations(upcoming, info)
    with t2:
        _how_it_works(info)


def _upcoming_reservations(upcoming, info):
    upcoming["score"], upcoming["risk"] = score(info, upcoming)
    upcoming["level_rate"] = upcoming["risk"].map(info["rates"])
    upcoming["value_at_risk"] = upcoming["re_total_amount"].astype(float) * upcoming["level_rate"]

    c1, c2 = st.columns([1, 2])
    horizon = c1.selectbox("Arrivals", [30, 90, 0],
                           format_func=lambda d: "All upcoming" if d == 0 else f"Next {d} days")
    levels = c2.multiselect("Risk level", LEVELS[::-1], default=["High", "Medium"])
    view = upcoming if horizon == 0 else upcoming[upcoming["re_check_in_date"].dt.date <= TODAY + dt.timedelta(days=horizon)]

    high = view[view["risk"] == "High"]
    k = st.columns(4)
    k[0].metric("Upcoming reservations", len(view))
    k[1].metric("High risk", len(high))
    k[2].metric("Value at high risk", cop(high["re_total_amount"].astype(float).sum()))
    k[3].metric("Revenue that could be lost", cop(view["value_at_risk"].sum()),
                help="Each reservation's value × the real cancellation rate of its risk level in the hotel's history.")

    shown = view[view["risk"].isin(levels)].sort_values("score", ascending=False).copy()
    if shown.empty:
        st.info("No reservations with that risk level in that period.")
        return
    shown["channel_label"] = shown["channel"].map(lambda c: CHANNEL_LABEL.get(c, c))
    shown["action"] = shown["risk"].map(ACTION)
    shown["score_pct"] = (shown["score"] * 100).round(0).astype(int)
    for c in ["re_reservation_id", "nights"]:
        shown[c] = shown[c].astype(int)
    table(shown[["re_reservation_id", "gu_name", "ro_number", "re_check_in_date", "nights", "channel_label",
                 "lead_time", "re_total_amount", "risk", "score_pct", "action"]],
          money=["re_total_amount"], dates=["re_check_in_date"],
          headers={"re_reservation_id": "Reservation", "gu_name": "Guest", "ro_number": "Room",
                   "re_check_in_date": "Arrival", "nights": "Nights", "channel_label": "Channel",
                   "lead_time": "Lead time (days)", "re_total_amount": "Amount", "risk": "Risk",
                   "score_pct": "Score (0-100)", "action": "What to do"},
          export="cancellation_risk")
    st.caption("The score ranks reservations from most to least risky; it isn't an exact probability. Upcoming "
               "reservations were usually booked far in advance, so more of them show as high risk than in the history.")


def _how_it_works(info):
    m = info["metrics"]
    st.markdown(
        f"The model learns from the hotel's **{thousands(info['n'])} reservations** that were completed or cancelled "
        f"({thousands(info['cancellations'])} cancellations, {info['overall_rate'] * 100:.0f}%). It only uses what's "
        "known at booking time: lead time, channel, nights, guests, nightly rate, season, room type, arrival day and "
        "month, the guest's age and country, and their past stays and cancellations. It's a Random Forest that "
        "retrains every hour with the latest data.")

    st.subheader("How well does it work?")
    st.caption(f"Tested over time: it was trained on the {thousands(m['train_size'])} oldest reservations and "
               f"evaluated on the {thousands(m['test_size'])} made since {m['test_from']:%b %d, %Y}, as if they "
               "were new.")
    k = st.columns(4)
    k[0].metric("AUC", f"{m['auc']:.2f}", help="0.5 = random guessing; 1 = perfect.")
    k[1].metric("Average cancellation rate", f"{m['base_rate'] * 100:.0f}%")
    k[2].metric("Cancellation rate at high risk", f"{m['high_rate'] * 100:.0f}%",
                delta=f"{m['high_rate'] / m['base_rate']:.1f}× the average" if m["base_rate"] else None,
                delta_color="off")
    k[3].metric("Cancellations caught", f"{m['high_capture'] * 100:.0f}%",
                help="Share of all cancellations that fell in the 20% of reservations flagged as high risk.")

    st.subheader("Risk levels")
    order = ["High", "Medium", "Low"]
    levels = pd.DataFrame({
        "Level": order,
        "Which reservations": ["The 20% with the highest score", "The next 30%", "The remaining 50%"],
        "Cancelled in the history": [f"{info['rates'][level] * 100:.0f} of every 100" for level in order],
        "What to do": [ACTION[level] for level in order],
    })
    st.dataframe(levels, hide_index=True)

    st.subheader("What drives the risk?")
    imp = info["importance"]
    imp = imp[imp["importance"] > 0].head(8).copy()
    imp["importance"] = (imp["importance"] * 100).round(2)
    bar_chart(imp, "feature", "importance", "", "How much worse the model gets if this feature is shuffled (AUC points × 100)",
              horizontal=True, color=INK)
    st.caption("Permutation importance on the test reservations. Features that don't appear barely help the prediction.")

    with st.expander("Model limitations"):
        st.markdown(
            "- It predicts from the hotel's past: if channels or cancellation policies change, check that it still works.\n"
            "- High risk doesn't mean the reservation will be cancelled; it means it's worth confirming it or asking "
            "for a deposit.\n"
            "- Celosía's data is invented test data, so the results show the method, not a real hotel.")
