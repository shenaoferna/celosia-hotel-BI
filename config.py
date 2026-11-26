"""Hotel identity, color palette and business parameters."""

import datetime as dt

# Brand identity. A "celosía" is the wooden lattice on colonial balconies:
# it lets the breeze in and keeps the room private.
HOTEL = "Celosía"
HOTEL_DESCRIPTION = "Boutique hotel in Cartagena, Colombia, five minutes from the walled city"
TAGLINE = "The breeze comes in, the noise stays out."

# Today's date: used by every rule that depends on the current day
TODAY = dt.date.today()

# Ink and antique gold palette: near-black ink, one antique gold accent and warm ivory,
# the restrained look of classic luxury hotels.
INK = "#1C1C1C"            # main color: brand bar, titles, charts
INK_DARK = "#111111"       # sidebar
IVORY = "#F3EEE3"          # warm off-white: panel and card backgrounds
GOLD = "#916E27"           # antique gold: primary buttons, accents, second chart color
GOLD_DARK = "#5E4615"      # text on gold backgrounds
OLIVE = "#4F6B4A"          # muted green: in house, low risk
CRIMSON = "#8E2F2F"        # deep red: cancellations, high risk, rooms in maintenance
STONE = "#8C7F6E"          # warm gray: neutral data

STATUS_COLOR = {"confirmed": GOLD, "in_house": OLIVE, "checked_out": INK, "cancelled": CRIMSON}
STATUSES = ["confirmed", "in_house", "checked_out", "cancelled"]
# Life cycle: confirmed --check-in--> in_house --check-out--> checked_out ; confirmed --cancel--> cancelled

# Codes stored in the database (required by the DDL's CHECK constraints) and the label the app shows
CHANNELS = {"direct": "Direct (hotel website or phone)", "booking": "Booking.com / OTA", "agency": "Travel agency",
            "walk_in": "Walk-in (no reservation)"}
STATUS_LABEL = {"confirmed": "Confirmed", "in_house": "In house", "checked_out": "Checked out",
                "cancelled": "Cancelled"}
ROOM_TYPE_LABEL = {"single": "Single", "double": "Double", "suite": "Suite", "family": "Family"}
CHANNEL_LABEL = {"direct": "Direct", "booking": "Booking.com", "agency": "Travel agency", "walk_in": "Walk-in"}

# Business assumptions (not stored in the database): commission each channel charges on the reservation amount
COMMISSION = {"direct": 0.0, "walk_in": 0.0, "booking": 0.18, "agency": 0.12}

# Earned revenue = completed stays and guests in house. On the books = confirmed reservations still to come.
REVENUE_NOTE = ("Earned: completed stays and guests in house. On the books: confirmed reservations that "
                "haven't happened yet, that is, expected revenue.")

# Format of each ID type: the same one the DDL's ck_guest_id_format CHECK enforces
ID_FORMAT = {
    "CC":  (r"^[0-9]{5,10}$",    "A national ID (CC) has only digits, between 5 and 10."),
    "CE":  (r"^[0-9]{4,7}$",     "A foreign resident ID (CE) has only digits, between 4 and 7."),
    "PAS": (r"^[A-Z0-9]{6,12}$", "A passport has letters and digits, between 6 and 12 characters, with no spaces or symbols."),
}
