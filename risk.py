"""Cancellation risk: a model that learns from the hotel's own booking history.

Idea: using what is known at booking time (lead time, channel, nights, guests, rate, season, the guest's
history...), estimate how likely a reservation is to be cancelled, so the front desk can act in time
(ask for a deposit, confirm before arrival).

The data and model logic (prepare, train, score) doesn't use Streamlit or Oracle, so it can be tested on
its own. Only the functions at the end talk to the database and use Streamlit's cache.
"""

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# ---- Features known at booking time (nothing that happens afterwards) ----
NUMERIC_FEATURES = ["lead_time", "nights", "guests", "nightly_rate", "surcharge", "age",
                    "past_stays", "past_cancellations", "international"]
CATEGORICAL_FEATURES = ["channel", "room_type", "arrival_month", "arrival_weekday"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

FEATURE_LABEL = {
    "lead_time": "Lead time (days)", "nights": "Nights", "guests": "Guests",
    "nightly_rate": "Nightly rate", "surcharge": "Season surcharge", "age": "Guest age",
    "past_stays": "Guest's past stays", "past_cancellations": "Guest's past cancellations",
    "international": "International guest", "channel": "Sales channel", "room_type": "Room type",
    "arrival_month": "Arrival month", "arrival_weekday": "Arrival weekday",
}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Risk levels: the 20% of reservations with the highest score are "High", the next 30% "Medium"
MEDIUM_CUTOFF, HIGH_CUTOFF = 0.50, 0.80
LEVELS = ["Low", "Medium", "High"]
ACTION = {
    "High": "Ask for a deposit or prepayment, and confirm the arrival with the guest a week before.",
    "Medium": "Send a reminder a week before arrival.",
    "Low": "No special action needed.",
}
MIN_RESERVATIONS, MIN_CANCELLATIONS = 200, 20

HISTORY_SQL = """
    SELECT r.re_reservation_id, r.re_guest_id, r.re_booking_date, r.re_check_in_date, r.re_check_out_date,
           r.re_nights, r.re_guests, r.re_total_amount, r.re_status, r.re_channel,
           ro.ro_number, ro.ro_type, s.se_surcharge, g.gu_name, g.gu_country, g.gu_birth_date
    FROM reservation r
    JOIN room ro ON ro.ro_room_id = r.re_room_id
    JOIN season s ON s.se_season_id = r.re_season_id
    JOIN guest g ON g.gu_guest_id = r.re_guest_id"""


# =========================== Data ===========================

def _guest_history(d):
    """For each reservation: how many stays the guest completed and how many reservations they cancelled
    BEFORE booking. A stay counts if it ended before the booking date; a cancellation, if its check-in date
    had already passed (the database doesn't store when it was cancelled, so this is the safe way not to
    look into the future)."""
    stays = np.zeros(len(d), dtype=int)
    cancellations = np.zeros(len(d), dtype=int)
    for _, idx in d.groupby("re_guest_id").indices.items():
        g = d.iloc[idx]
        booked = g["re_booking_date"].values[:, None]
        completed = ((g["re_status"].values == "checked_out")[None, :] & (g["re_check_out_date"].values[None, :] <= booked))
        cancelled = ((g["re_status"].values == "cancelled")[None, :] & (g["re_check_in_date"].values[None, :] <= booked))
        stays[idx] = completed.sum(axis=1)
        cancellations[idx] = cancelled.sum(axis=1)
    return stays, cancellations


def prepare(raw):
    """Turns the result of HISTORY_SQL into the model's feature table."""
    d = raw.copy()
    for c in ["re_booking_date", "re_check_in_date", "re_check_out_date", "gu_birth_date"]:
        d[c] = pd.to_datetime(d[c])
    d = d.sort_values(["re_booking_date", "re_reservation_id"]).reset_index(drop=True)

    d["lead_time"] = (d["re_check_in_date"] - d["re_booking_date"]).dt.days.clip(lower=0)
    d["nights"] = d["re_nights"].astype(float)
    d["guests"] = d["re_guests"].astype(float)
    d["nightly_rate"] = d["re_total_amount"].astype(float) / d["nights"]
    d["surcharge"] = d["se_surcharge"].astype(float)
    d["age"] = ((d["re_booking_date"] - d["gu_birth_date"]).dt.days / 365.25).round()
    d["age"] = d["age"].fillna(d["age"].median())
    d["international"] = (d["gu_country"].fillna("Colombia") != "Colombia").astype(int)
    d["channel"] = d["re_channel"].astype(str)
    d["room_type"] = d["ro_type"].astype(str)
    d["arrival_month"] = d["re_check_in_date"].dt.month.astype(str)
    d["arrival_weekday"] = d["re_check_in_date"].dt.dayofweek.map(dict(enumerate(WEEKDAYS)))
    d["past_stays"], d["past_cancellations"] = _guest_history(d)

    # Reservations with a known outcome are used for training. Confirmed ones are still open.
    d["resolved"] = d["re_status"].isin(["checked_out", "cancelled", "in_house"])
    d["cancelled"] = (d["re_status"] == "cancelled").astype(int)
    return d


def new_booking_row(lead_time, nights, guests, total_amount, surcharge, age, past_stays,
                    past_cancellations, country, channel, room_type, check_in_date):
    """Builds the features of a reservation that isn't in the database yet (New reservation page)."""
    check_in_date = pd.Timestamp(check_in_date)
    return pd.DataFrame([{
        "lead_time": max(int(lead_time), 0), "nights": float(nights), "guests": float(guests),
        "nightly_rate": float(total_amount) / float(nights), "surcharge": float(surcharge),
        "age": float(age) if age is not None else 40.0,
        "past_stays": int(past_stays), "past_cancellations": int(past_cancellations),
        "international": int((country or "Colombia") != "Colombia"), "channel": str(channel),
        "room_type": str(room_type), "arrival_month": str(check_in_date.month),
        "arrival_weekday": WEEKDAYS[check_in_date.dayofweek],
    }])


# =========================== Model ===========================

def _pipeline():
    pre = ColumnTransformer([("num", "passthrough", NUMERIC_FEATURES),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES)])
    forest = RandomForestClassifier(n_estimators=200, min_samples_leaf=10, class_weight="balanced",
                                    random_state=42, n_jobs=-1)
    return Pipeline([("pre", pre), ("model", forest)])


def train(data):
    """Trains the model on resolved reservations. Returns a dict with the model, the risk-level cutoffs and
    the metrics, or None if there isn't enough history yet."""
    res = data[data["resolved"]].sort_values("re_booking_date").reset_index(drop=True)
    if len(res) < MIN_RESERVATIONS or res["cancelled"].sum() < MIN_CANCELLATIONS:
        return None
    X, y = res[FEATURES], res["cancelled"]

    # 1) Honest evaluation over time: train on the oldest 75% and test on the newest 25%,
    #    as it would happen in real life (the model only knows the past).
    cut = int(len(res) * 0.75)
    evaluator = _pipeline().fit(X.iloc[:cut], y.iloc[:cut])
    X_test, y_test = X.iloc[cut:], y.iloc[cut:]
    p_test = evaluator.predict_proba(X_test)[:, 1]
    high_test = p_test >= np.quantile(p_test, HIGH_CUTOFF)
    metrics = {
        "train_size": int(cut), "test_size": int(len(y_test)),
        "test_from": res["re_booking_date"].iloc[cut].date(),
        "auc": float(roc_auc_score(y_test, p_test)),
        "base_rate": float(y_test.mean()),
        "high_rate": float(y_test[high_test].mean()),
        "high_capture": float(y_test[high_test].sum() / max(y_test.sum(), 1)),
    }
    imp = permutation_importance(evaluator, X_test, y_test, scoring="roc_auc", n_repeats=5, random_state=42)
    importance = (pd.DataFrame({"feature": [FEATURE_LABEL[f] for f in FEATURES], "importance": imp.importances_mean})
                  .sort_values("importance", ascending=False).reset_index(drop=True))

    # 2) Risk-level cutoffs and the real cancellation rate of each level, from out-of-sample predictions
    #    (cross-validation), so the model isn't measured on the same data it learned from.
    oof = cross_val_predict(_pipeline(), X, y, method="predict_proba",
                            cv=StratifiedKFold(5, shuffle=True, random_state=42))[:, 1]
    cutoffs = (float(np.quantile(oof, MEDIUM_CUTOFF)), float(np.quantile(oof, HIGH_CUTOFF)))
    oof_level = _to_level(oof, cutoffs)
    rates = {level: float(y[oof_level == level].mean()) for level in LEVELS}

    # 3) Final model trained on the full history
    model = _pipeline().fit(X, y)
    return {"model": model, "cutoffs": cutoffs, "rates": rates, "metrics": metrics,
            "importance": importance, "n": int(len(res)), "cancellations": int(y.sum()),
            "overall_rate": float(y.mean())}


def _to_level(prob, cutoffs):
    return np.where(prob >= cutoffs[1], "High", np.where(prob >= cutoffs[0], "Medium", "Low"))


def score(info, X):
    """Returns (score, risk level) for each row of X."""
    prob = info["model"].predict_proba(X[FEATURES])[:, 1]
    return prob, _to_level(prob, info["cutoffs"])


# =========================== Connection to the app ===========================

def load_history():
    from db import query
    return prepare(query(HISTORY_SQL))


@st.cache_resource(ttl=3600, show_spinner="Training the risk model on the hotel's booking history...")
def current_model():
    """Model trained on the current database. Cached for an hour so it doesn't retrain on every click."""
    return train(load_history())


def guest_history(guest_id, today):
    """The guest's completed stays and cancelled reservations up to today (for a new reservation)."""
    from db import query
    df = query("""
        SELECT NVL(SUM(CASE WHEN re_status = 'checked_out' AND re_check_out_date <= :today THEN 1 ELSE 0 END), 0) AS stays,
               NVL(SUM(CASE WHEN re_status = 'cancelled' AND re_check_in_date <= :today THEN 1 ELSE 0 END), 0) AS cancellations
        FROM reservation WHERE re_guest_id = :guest_id""", {"today": today, "guest_id": int(guest_id)})
    return int(df.iat[0, 0]), int(df.iat[0, 1])
