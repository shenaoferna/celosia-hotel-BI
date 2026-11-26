# Celosía: Hotel Reservation Database & Management App

> *The breeze comes in, the noise stays out.*

**🔗 Live app: [YOUR-APP-NAME.streamlit.app](https://YOUR-APP-NAME.streamlit.app)**. If it's asleep, click "Yes, get this app back up" and wait about a minute. Screenshots are below.

Celosía is a **fictional** 23-room boutique hotel in Cartagena, Colombia. This project takes it from business requirements to a working system:

1. **Business analysis:** requirements, user stories, process maps and a stakeholder analysis ([`docs/`](docs/)).
2. **An Oracle database** with a star-schema design for guests, rooms, seasons and reservations.
3. **A Python + Streamlit app** for the front desk to book rooms, check guests in and out, and analyze hotel performance.
4. **A machine learning model** that learns from the hotel's own booking history and flags reservations likely to be cancelled, so the front desk can ask for a deposit before it's too late.

`Business analysis` · `Requirements` · `BPMN` · `SQL` · `Oracle` · `Data modeling` · `Python` · `Streamlit` · `BI` · `Machine learning`

Built for the Introduction to Business Intelligence course at Universidad EAFIT.

---

## Screenshots

| Daily overview and check-in | New reservation |
|---|---|
| ![Daily overview](images/daily_overview.png) | ![New reservation](images/new_reservation.png) |

| Occupancy map | Performance analysis |
|---|---|
| ![Occupancy map](images/occupancy_map.png) | ![Performance](images/performance.png) |

| Cancellation risk page |
|---|
| ![Cancellation risk](images/cancellation_risk.png) |

## Cancellation risk model

Cancelled bookings leave rooms empty that could have been sold. The app scores every reservation for cancellation risk, using only what is known at booking time:
- days of lead time
- sales channel
- nights and number of guests
- nightly rate and season surcharge
- room type, and arrival day and month
- the guest's age, country, and past stays and cancellations

**Where it shows up**
- **New reservation:** before confirming, the agent sees the risk level and what to do. For example: *"High risk: ask for a deposit and confirm a week before arrival."*
- **Cancellation risk page:** every upcoming reservation, ranked by risk, with the revenue that could be lost, an Excel export, and a tab explaining how the model works.

**How it was built**
- It's a Random Forest retrained every hour from the database (Python and scikit-learn).
- **It's validated over time, not with a random split.** It was trained on the oldest 75% of bookings and tested on the newest 25%, the way it would be used in real life.
- The high, medium and low cutoffs come from cross-validated predictions, so the cancellation rate shown for each level is real, not optimistic.

| Result on the newest 25% of bookings | |
|---|---|
| AUC | 0.71 |
| Average cancellation rate | 10% |
| Cancellation rate in the "high risk" group (top 20% of scores) | **21%**, 2.1 times the average |
| Share of all cancellations caught by the "high risk" group | 42% |

The strongest signals are the **sales channel** (Booking.com cancels most and walk-ins never cancel), **lead time**, and the **guest's past cancellations**.

> The test data is synthetic, so these numbers show the method, not a real hotel. The same approach on real hotel data (my [cancellation prediction project](https://github.com/YOUR-USERNAME/hotel-booking-cancellation-prediction)) reached an AUC of 0.91.

## Business analysis documents

| Document | What it covers |
|---|---|
| [Business Requirements Document](docs/01-business-requirements.md) | Problem, objectives, scope, business rules, functional and non-functional requirements |
| [User stories](docs/02-user-stories.md) | 16 user stories with acceptance criteria, grouped by epic, with a traceability matrix |
| [Process maps](docs/03-process-maps.md) | As-is and to-be check-in and booking processes |
| [Stakeholder analysis](docs/04-stakeholder-analysis.md) | Stakeholders, interests, influence and RACI |

## What the app does

**Front desk**
- **Today:** see the hotel's status floor by floor on any date, and check today's guests in and out.
- **New reservation:** find the guest, search by dates and guests, and choose from cards showing only the rooms that are available, with the calculated price.
- **Reservations:** search, cancel or modify reservations, and rate completed stays.
- **Guests:** register new guests, view their history, and delete guests who have no reservations.

**Hotel**
- **Occupancy map:** see which rooms are occupied on each day of the month.
- **Rooms:** put a room into maintenance or reactivate it.
- **Seasons:** create seasons and delete seasons that have no reservations.

**Cancellation risk**
- **When booking:** shows the new reservation's risk level and the recommended action before confirming.
- **Cancellation risk page:** lists upcoming reservations ranked by risk, shows the revenue at risk, and explains the model.

**Analytics**
- **Performance:** occupancy, revenue, sales channels, booking lead time, month vs. the same month last year, and arrival and departure times.
- **Customers:** satisfaction, most frequent guests, cancellations and countries of origin.
- **SQL queries:** run your own read-only queries.

Every table can be **downloaded to Excel**.

## Data model

The database has **4 tables in a star schema**:
- **`reservation`** is the fact table. Each row is one room booked by one guest for one stay.
- **`guest`**, **`room`** and **`season`** are the dimensions.

All relationships are one-to-many.

```mermaid
erDiagram
    GUEST ||--o{ RESERVATION : "makes"
    ROOM ||--o{ RESERVATION : "is booked in"
    SEASON ||--o{ RESERVATION : "classifies"

    GUEST {
        NUMBER gu_guest_id PK
        VARCHAR2 gu_name
        VARCHAR2 gu_id_type
        VARCHAR2 gu_id_number
        DATE gu_birth_date
        VARCHAR2 gu_email
        VARCHAR2 gu_phone
        VARCHAR2 gu_country
    }
    ROOM {
        NUMBER ro_room_id PK
        VARCHAR2 ro_number
        VARCHAR2 ro_type
        NUMBER ro_capacity
        NUMBER ro_floor
        NUMBER ro_nightly_rate
        VARCHAR2 ro_status
    }
    SEASON {
        NUMBER se_season_id PK
        VARCHAR2 se_name
        DATE se_start_date
        DATE se_end_date
        NUMBER se_surcharge
    }
    RESERVATION {
        NUMBER re_reservation_id PK
        NUMBER re_guest_id FK
        NUMBER re_room_id FK
        NUMBER re_season_id FK
        DATE re_booking_date
        DATE re_check_in_date
        DATE re_check_out_date
        NUMBER re_nights
        NUMBER re_guests
        NUMBER re_total_amount
        VARCHAR2 re_status
        VARCHAR2 re_channel
        NUMBER re_rating
        DATE re_check_in_time
        DATE re_check_out_time
    }
```

### Normalization

The tables are in **third normal form (3NF)**, with three deliberate exceptions in the fact table:

- **1NF:** each cell holds a single value, and each reservation is exactly one room. If a family books two rooms, that's two rows.
- **2NF:** every primary key is a single column, so no attribute can depend on only part of a key.
- **3NF:** the nightly price belongs to each room, not to the room type (suites 402 and 602 have different prices). The surcharge belongs to the season, and the country belongs to the guest. None of these are repeated in `reservation`.
- **Not stored because they can be calculated:**
  - A guest's age is calculated from their date of birth.
  - Whether a room is free depends on the date, so it's calculated from reservations. `ro_status` only says whether the room is in service.

**Deliberate exceptions in `reservation`**, which are common practice for a star-schema fact table:

| Column | Could be calculated from | Why it's stored | How consistency is enforced |
|---|---|---|---|
| `re_nights` | check-out − check-in | It's the measure almost every analysis uses | A CHECK constraint requires it to match the dates |
| `re_total_amount` | price × nights × surcharge | It's what was charged at booking time. If rates change later, the reservation keeps its original value | The app calculates it when booking or modifying |
| `re_season_id` | the check-in date | It joins the reservation to its season with a foreign key, like any dimension | The app assigns it from the check-in date |

## Business rules

**Enforced by the database (CHECK, UNIQUE and FK constraints)**
- No two guests can have the same document type and number.
- A national ID (CC) has only digits. A passport has letters and digits.
- A room holds 1 to 6 people.
- Check-out must be after check-in, and the number of nights must match the dates.
- A stay can only be rated once it has ended.

**Enforced by the app**, because these rules need another table, other rows or today's date:
- The guests fit in the room.
- The room is active and free on those dates.
- The season matches the check-in date.
- Total price = nightly price × nights × (1 + season surcharge / 100).
- The guest making the booking is an adult.

**Reservation life cycle**

```mermaid
stateDiagram-v2
    [*] --> confirmed: booked
    confirmed --> in_house: check-in
    in_house --> checked_out: check-out
    confirmed --> cancelled: cancelled
    checked_out --> [*]
    cancelled --> [*]
```

## How the code is built

- **Modular.** Each file has one job (connection, rules, interface), and each app page lives in its own file in `app_pages/`. File, function and variable names are in English too.
- **Centralized connection.** Only `db.py` talks to Oracle. It creates a connection pool once, and the rest of the code uses its `query()`, `scalar()` and `execute_write()` functions.
- **Parameterized queries.** Every value is passed as a bind variable, so the app isn't vulnerable to SQL injection.
- **Transactions and error handling.**
  - Every write uses `COMMIT` or `ROLLBACK`.
  - Oracle errors are translated into clear messages, for example "Can't delete: other reservations depend on this record."
- **No credentials in the code.** User, passwords and wallet are read from `.streamlit/secrets.toml`, which is excluded with `.gitignore`.
- **Consistent English naming.** Tables, columns, constraints and stored codes are in English (for example `reservation.re_status = 'in_house'`), with a short prefix per table (`gu_`, `ro_`, `se_`, `re_`) so every column name says where it comes from. The app turns codes into readable labels (`in_house` → "In house") in one place, `config.py`.
- **Branded interface.** A Colonial palette inspired by Cartagena's walled city: a navy brand bar with a gold lattice pattern, room cards for booking, pill buttons in bougainvillea, and color-coded status and risk badges. It's set in `.streamlit/config.toml` and `ui.py`.
- **Safe SQL page.** Free queries accept only `SELECT` and run in a read-only transaction.

## Test data

| Table | Rows |
|---|---|
| guest | 1,281 |
| room | 23 |
| season | 14 |
| reservation | 2,087 |

The data is invented but behaves like a real hotel's:
- Occupancy is higher in December and Easter week.
- Suites sell less than doubles, and family rooms fill up during school holidays.
- Guests come from 19 countries, and the data includes cancellations and arrivals at different times of day.

It runs from January 2025 to February 2027, with reservation statuses calculated as of November 10, 2026.

## Repository structure

| File | What it is |
|---|---|
| `DDL_hotel.sql` | Creates the 4 tables and their constraints. Run it first |
| `DML_hotel.sql` | Loads the test data. Run it after the DDL |
| `main.py` | Starts the app: navigation and general error handling |
| `config.py` | Hotel identity, color palette and business parameters |
| `.streamlit/config.toml` | Visual theme (Colonial palette: navy, gold and bougainvillea) |
| `db.py` | The single Oracle connection: reads, writes and error messages |
| `ui.py` | Shared visual pieces: tables, charts, Excel export |
| `rules.py` | Business rules checked by the app: age, document format, check-in and check-out |
| `risk.py` | Cancellation risk model: features, training, time-based validation and risk levels |
| `app_pages/` | One app page per file (named `app_pages` because Streamlit reserves `pages/`) |
| `docs/` | Business analysis documents |
| `images/` | Screenshots |
| `requirements.txt` | Python libraries |

## How to run it

### 1. Create the database
1. Create a free **Oracle Autonomous Database** (Always Free) and download its **wallet**.
2. Connect to it from SQL Developer using the wallet.
3. Run `DDL_hotel.sql` with **F5**. This creates the 4 tables.
4. Run `DML_hotel.sql` with **F5**. This loads the data and takes 1–3 minutes.

### 2. Run the app
1. Install the libraries: `pip install -r requirements.txt`
2. Unzip the wallet into a folder, for example `C:/oracle/wallet_hotel/wallet`.
3. Next to `main.py`, create a `.streamlit` folder, and inside it a `secrets.toml` file:
   ```toml
   [oracle]
   user = "ADMIN"
   password = "your_database_password"
   dsn = "adbhotel_low"
   config_dir = "C:/oracle/wallet_hotel/wallet"
   wallet_password = "your_wallet_password"
   ```
   **This file contains your passwords. Never upload it to GitHub.**
4. Run `streamlit run main.py`

### 3. Publish it online (Streamlit Community Cloud)
1. Sign in at [share.streamlit.io](https://share.streamlit.io) with GitHub and click **Create app**.
2. Choose this repository, branch `main`, main file `main.py`. In **Advanced settings**, pick Python 3.12.
3. In **Secrets**, paste the database settings. There's no wallet folder in the cloud, so the wallet goes inside the secrets:
   ```toml
   [oracle]
   user = "ADMIN"
   password = "your_database_password"
   wallet_password = "your_wallet_password"
   dsn = "(description= ... )"   # the full line for adbhotel_low, copied from tnsnames.ora
   ewallet_pem = """
   -----BEGIN ENCRYPTED PRIVATE KEY-----
   ... the whole content of ewallet.pem ...
   -----END CERTIFICATE-----
   """
   ```
4. Click **Deploy**. The secrets stay private: they're never shown in the repository.

---

**Author:** Sara Henao Fernández · Introduction to Business Intelligence, Universidad EAFIT
[LinkedIn](https://www.linkedin.com/in/YOUR-PROFILE) · [Portfolio](https://github.com/YOUR-USERNAME)
