# Business Requirements Document (BRD)
**Project:** Celosía Hotel Reservation System
**Author:** Sara Henao Fernández, Business Analyst
**Version:** 1.1 · **Status:** Approved for build · v1.1 adds cancellation risk (FR-17, FR-18)

> Celosía is a fictional hotel created for a university case study. This document records the requirements the system was designed to meet. The "current state" describes a typical small independent hotel and is assumed, not observed.

---

## 1. Executive summary

Celosía is a 23-room boutique hotel in Cartagena, Colombia. Reservations are kept in a shared spreadsheet and confirmed by phone and WhatsApp, so the front desk can't see room availability reliably, rooms get double-booked, and management has no trustworthy numbers on occupancy or revenue.

This project delivers:
- a **relational database** that becomes the single source of truth for guests, rooms, seasons and reservations
- a **front-desk app** that prevents invalid bookings and handles check-in and check-out
- **built-in analytics** for occupancy, revenue, channels and guest satisfaction
- **a cancellation risk model** that flags bookings likely to be cancelled, so staff can protect the revenue

## 2. Business problem

| Pain point | Impact |
|---|---|
| Availability is checked by hand in a spreadsheet | Double bookings, slow answers to guests, and lost sales while staff search |
| Prices are calculated by hand from a rate sheet and seasonal surcharges | Inconsistent quotes and revenue leakage |
| Guest data is duplicated and incomplete (same person, different spellings) | No guest history and no repeat-guest recognition |
| Check-in and check-out times are not recorded | No visibility of arrival patterns for staffing |
| About 1 in 10 bookings is cancelled, often close to arrival, and staff can't tell which ones | Rooms stay empty that could have been resold, and deposits are asked of everyone or of no one |
| No consolidated reporting | Management can't answer basic questions: occupancy this month vs. last year, best sales channel, why guests cancel |

## 3. Business objectives

| ID | Objective | Measure of success |
|---|---|---|
| BO-1 | Eliminate double bookings | 0 overlapping reservations for the same room (enforced by the system) |
| BO-2 | Quote prices consistently | 100% of reservations priced by the system using the official formula |
| BO-3 | Reduce the time to create a booking | A front-desk agent can complete a booking in under 2 minutes |
| BO-4 | Build a reliable guest history | One record per guest, identified by document type and number |
| BO-5 | Give management self-service performance data | Occupancy, revenue, channel and satisfaction reports available without manual work |
| BO-6 | Reduce revenue lost to cancellations | Every booking gets a risk level at booking time. The "high risk" group cancels at least twice as often as the average, so deposits can be targeted |

## 4. Scope

**In scope**
- Guest registration and lookup
- Room inventory and room status (active or in maintenance)
- Seasons with surcharges
- Creating, modifying, cancelling and rating reservations
- Check-in and check-out
- Occupancy map and dashboards
- Read-only SQL queries for analysts
- Excel export
- Cancellation risk level for new and upcoming reservations (v1.1)

**Out of scope (future phases)**
- Online booking by guests
- Payment processing and invoicing
- Integration with Booking.com and other channels (channel manager)
- Housekeeping and maintenance work orders
- Multi-property support
- Dynamic pricing
- Collecting deposits automatically (the system recommends a deposit; staff request it outside the system)

## 5. Stakeholders

See [Stakeholder analysis](04-stakeholder-analysis.md). The main stakeholders are the hotel manager (sponsor), the front-desk team (primary users), the revenue and marketing lead, guests, and IT/data support.

## 6. Business rules

| ID | Rule | Where it's enforced |
|---|---|---|
| BR-01 | A guest is identified by document type and document number. No two guests share both. | Database (UNIQUE) |
| BR-02 | Document format: national ID (CC) is 5–10 digits, foreign ID (CE) is 4–7 digits, passport (PAS) is 6–12 letters or digits | Database (CHECK) and app |
| BR-03 | Only an adult (18 or older) can make a reservation | App |
| BR-04 | A reservation is for exactly one room. A group needing several rooms makes several reservations. | Data model |
| BR-05 | The number of guests can't exceed the room's capacity (1–6) | App and database |
| BR-06 | A room can't have two active reservations with overlapping dates. Cancelled reservations don't block the room. | App |
| BR-07 | Rooms in maintenance can't be booked | App |
| BR-08 | Check-out must be after check-in, and nights = check-out date − check-in date | Database (CHECK) |
| BR-09 | Every date belongs to exactly one season. The reservation takes the season of its check-in date. | App |
| BR-10 | Total price = nightly room price × nights × (1 + season surcharge / 100), fixed at booking time | App |
| BR-11 | Reservation life cycle: confirmed → in progress (check-in) → completed (check-out), or confirmed → cancelled | Database (CHECK) and app |
| BR-12 | Check-in is only possible on or after the check-in date and before the check-out date | App |
| BR-13 | A stay can only be rated (1–5) after it's completed | Database (CHECK) |
| BR-14 | Guests, rooms or seasons with reservations can't be deleted, so history is never lost | Database (foreign keys) and app |

## 7. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Register a guest with name, document, date of birth, email, phone and country, validating the document format | Must |
| FR-02 | Search for a guest by document and show their reservation history | Must |
| FR-03 | Show only the rooms available for the selected dates and number of guests | Must |
| FR-04 | Calculate and show the total price before the booking is confirmed | Must |
| FR-05 | Create a reservation with a sales channel (direct, Booking/OTA, travel agency, walk-in) | Must |
| FR-06 | Modify a confirmed reservation's dates, guests or room, recalculating the price | Must |
| FR-07 | Cancel a confirmed reservation | Must |
| FR-08 | Show the day's arrivals and departures and register check-in and check-out with a timestamp | Must |
| FR-09 | Show an occupancy map of each room for each day of the month | Should |
| FR-10 | Change a room's status between active and maintenance, warning if it has upcoming reservations | Should |
| FR-11 | Create seasons without overlapping dates, and delete seasons that have no reservations | Must |
| FR-12 | Record a 1–5 satisfaction rating for completed stays | Should |
| FR-13 | Show performance analytics: occupancy, realized and expected revenue, channels, booking lead time, year-over-year comparison, arrival and departure times | Should |
| FR-14 | Show customer analytics: satisfaction, frequent guests, cancellations, countries of origin | Should |
| FR-15 | Let analysts run read-only SQL queries | Could |
| FR-16 | Export any table to Excel | Could |
| FR-17 | Before confirming a new reservation, show its cancellation risk level (high, medium or low), the historical cancellation rate for that level, and the recommended action | Should |
| FR-18 | List upcoming confirmed reservations ranked by cancellation risk, with the revenue at risk, filters by period and level, and an explanation of how the model works | Should |

User stories and acceptance criteria for each requirement are in [User stories](02-user-stories.md).

## 8. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Data integrity | Business rules that the database can check are enforced with constraints, so invalid data can't be saved even outside the app |
| NFR-02 | Security | All queries are parameterized (no SQL injection). Credentials are never stored in the code or the repository. The SQL page is read-only. |
| NFR-03 | Reliability | Every write runs in a transaction that either fully commits or fully rolls back |
| NFR-04 | Usability | Errors are shown in plain language that tells the user what to do next |
| NFR-05 | Performance | Screens load in a few seconds for the hotel's data volume (thousands of reservations) |
| NFR-06 | Maintainability | Modular code with one responsibility per file and a single database-access layer |
| NFR-07 | Cost | Runs on free tiers (Oracle Always Free and Streamlit Community Cloud) |
| NFR-08 | Model integrity | The risk model only uses data known at booking time. It's validated on the most recent bookings (trained on older ones), retrained automatically every hour, and never blocks a booking if it fails |
| NFR-09 | Explainability | Staff see a level and a recommended action, not a raw score. The model page shows its accuracy and which variables matter most |

## 9. Data requirements

Star schema with one fact table (`reservation`) and three dimensions (`guest`, `room`, `season`). See the [data model in the README](../README.md#data-model).

**Data the system doesn't store:**
- Guest age, which is calculated from the date of birth.
- Room occupancy, which is calculated from reservations.

## 10. Assumptions and constraints

- One property, 23 rooms on 7 floors, four room types: single, double, suite and family.
- Rates are set per room, not per room type.
- Channel commissions are a reporting assumption, not stored in the database: 18% for Booking/OTA and 12% for travel agencies.
- Free-tier hosting means the app and the database can go to sleep when unused.

## 11. Risks

| Risk | Mitigation |
|---|---|
| Staff keep using the spreadsheet in parallel | Make the system faster than the spreadsheet for daily tasks, and retire the spreadsheet after go-live |
| Wrong season set-up leads to wrong prices | Prevent overlapping seasons, and block bookings when no season covers the check-in date |
| The risk model is wrong or becomes outdated | Show its accuracy on recent bookings, retrain it automatically, and present it as a recommendation, never as an automatic rule |
| Guests feel treated unfairly by the model | It doesn't use sensitive personal data beyond age and country. The action is a standard deposit policy, applied consistently to high-risk bookings |
| Database credentials leak | Keep secrets out of the repository, and use the wallet and secrets file only on the server |
