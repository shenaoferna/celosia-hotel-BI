"""Hotel identity, color palette and business parameters."""

import datetime as dt

# Brand identity. A "celosía" is the wooden lattice on colonial balconies:
# it lets the breeze in and keeps the room private.
HOTEL = "Celosía"
HOTEL_DESCRIPTION = "Boutique hotel in Cartagena, Colombia, five minutes from the walled city"
TAGLINE = "The breeze comes in, the noise stays out."

# Today's date: used by every rule that depends on the current day
TODAY = dt.date.today()

# Colonial palette, inspired by the walled city: indigo doors, brass door knockers
# and bougainvillea on the balconies.
INDIGO = "#0C447C"         # main color: brand bar, titles, charts
INDIGO_DARK = "#082F57"    # sidebar
SKY = "#E6F1FB"            # very light blue: panel and card backgrounds
BRASS = "#EF9F27"          # gold accents, second chart color
BRASS_DARK = "#854F0B"     # text on gold backgrounds
SAGE = "#2E7D5B"           # balcony green: in house, low risk
BOUGAINVILLEA = "#B83F6C"  # primary buttons, cancellations, high risk
STONE = "#8C7F6E"          # coral stone of the city wall: neutral data

STATUS_COLOR = {"confirmed": BRASS, "in_house": SAGE, "checked_out": INDIGO, "cancelled": BOUGAINVILLEA}
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
