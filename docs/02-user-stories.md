# User Stories & Acceptance Criteria
**Project:** Celosía Hotel Reservation System · **Author:** Sara Henao Fernández

The stories are grouped into six epics. Acceptance criteria use the Given / When / Then format. Requirement IDs (FR-xx) and business rules (BR-xx) refer to the [Business Requirements Document](01-business-requirements.md).

**Personas**
- **Front-desk agent:** handles bookings, arrivals and departures.
- **Hotel manager:** runs the hotel and owns room inventory and seasons.
- **Revenue and marketing lead:** follows occupancy, channels and satisfaction.
- **Data analyst:** answers ad-hoc questions with SQL.

---

## Epic 1: Guest management

### US-01: Register a new guest
**As a** front-desk agent, **I want to** register a guest with their ID document and contact details, **so that** I can book rooms for them and keep their history.

- **Given** the registration form, **when** I enter a passport number with spaces or symbols, **then** the system rejects it and explains the valid format (6–12 letters or digits).
- **Given** a guest already exists with the same document type and number, **when** I try to register them again, **then** the system blocks the duplicate and tells me the guest already exists.
- **Given** valid data, **when** I submit the form, **then** the guest is saved and can be found by document immediately.

*Traces to: FR-01, BR-01, BR-02. Priority: Must.*

### US-02: Look up a guest and their history
**As a** front-desk agent, **I want to** find a guest by document number and see their past and upcoming stays, **so that** I can recognize repeat guests and answer their questions.

- **Given** a document number typed with dots or dashes (for example "1.036.654.321"), **when** I search, **then** the system ignores the formatting and finds the guest.
- **Given** a guest with reservations, **when** I open their profile, **then** I see every reservation with its dates, room, status and value.

*Traces to: FR-02. Priority: Must.*

### US-03: Delete a guest registered by mistake
**As a** hotel manager, **I want to** delete a guest record that was created by mistake, **so that** the guest list stays clean.

- **Given** a guest with no reservations, **when** I confirm the deletion, **then** the record is removed.
- **Given** a guest with one or more reservations, **when** I try to delete them, **then** the system blocks it and explains that their history would be lost.

*Traces to: BR-14. Priority: Could.*

## Epic 2: Reservations

### US-04: See only rooms that can actually be booked
**As a** front-desk agent, **I want to** see only the rooms that are free and big enough for the chosen dates and number of guests, **so that** I never offer a room I can't sell.

- **Given** check-in and check-out dates and a number of guests, **when** I search, **then** the system lists only active rooms with enough capacity and no overlapping confirmed or in-progress reservation.
- **Given** a room in maintenance, **when** I search any dates, **then** that room isn't listed.
- **Given** no room fits, **when** I search, **then** the system suggests trying other dates or fewer guests.

*Traces to: FR-03, BR-05, BR-06, BR-07. Priority: Must.*

### US-05: Get the correct price automatically
**As a** front-desk agent, **I want** the system to calculate the total price, **so that** every guest gets the same, correct quote.

- **Given** a room at 400,000 COP per night, 3 nights and a season with a 20% surcharge, **when** I select the room, **then** the total shown is 400,000 × 3 × 1.20 = 1,440,000 COP.
- **Given** no season covers the check-in date, **when** I try to book, **then** the system stops me and asks for the season to be created first.

*Traces to: FR-04, BR-09, BR-10. Priority: Must.*

### US-06: Create a reservation
**As a** front-desk agent, **I want to** confirm a booking for an adult guest and record the sales channel, **so that** the room is held and management knows where bookings come from.

- **Given** the guest is under 18, **when** I try to book, **then** the system blocks it and explains that only an adult can make the reservation.
- **Given** a check-out date that isn't after the check-in date, **when** I try to book, **then** the system shows an error.
- **Given** valid data, **when** I confirm, **then** the reservation is saved as "confirmed" with its channel, nights and total price.

*Traces to: FR-05, BR-03, BR-08, BR-11. Priority: Must.*

### US-07: Modify a reservation
**As a** front-desk agent, **I want to** change the dates, number of guests or room of a confirmed reservation, **so that** I can handle guests' change requests without cancelling and rebooking.

- **Given** a confirmed reservation, **when** I change the dates, **then** availability is checked again and the price is recalculated with the new season and nights.
- **Given** a reservation that is already in progress, completed or cancelled, **when** I try to modify it, **then** the system doesn't allow it.

*Traces to: FR-06. Priority: Must.*

### US-08: Cancel a reservation
**As a** front-desk agent, **I want to** cancel a confirmed reservation, **so that** the room becomes available again and the cancellation is recorded for analysis.

- **Given** a confirmed reservation, **when** I cancel it, **then** its status changes to "cancelled" and the room appears as available for those dates.
- **Given** a cancelled reservation, **when** I look at the cancellation report, **then** it's counted there.

*Traces to: FR-07, BR-11. Priority: Must.*

## Epic 3: Front-desk operations

### US-09: Check a guest in
**As a** front-desk agent, **I want to** see today's arrivals and check guests in with one click, **so that** the system shows who is in the hotel.

- **Given** a confirmed reservation whose stay includes today, **when** I click check-in, **then** the status changes to "in progress" and the exact time is recorded.
- **Given** a reservation whose check-in date is in the future, **when** I try to check the guest in, **then** the system doesn't allow it.

*Traces to: FR-08, BR-11, BR-12. Priority: Must.*

### US-10: Check a guest out
**As a** front-desk agent, **I want to** check out departing guests, **so that** the room is released and the stay is closed.

- **Given** a reservation in progress, **when** I click check-out, **then** the status changes to "completed" and the time is recorded.
- **Given** a reservation that isn't in progress, **when** I try to check the guest out, **then** the system tells me it isn't in progress.

*Traces to: FR-08, BR-11. Priority: Must.*

### US-11: Rate a completed stay
**As a** front-desk agent, **I want to** record the guest's 1–5 satisfaction rating at check-out, **so that** management can track satisfaction.

- **Given** a completed stay, **when** I save a rating from 1 to 5, **then** it's stored with the reservation.
- **Given** a stay that hasn't finished, **when** I try to rate it, **then** the system doesn't allow it.

*Traces to: FR-12, BR-13. Priority: Should.*

## Epic 4: Inventory and pricing

### US-12: Take a room out of service
**As a** hotel manager, **I want to** put a room into maintenance and reactivate it later, **so that** it isn't sold while it's being repaired.

- **Given** an active room with upcoming reservations, **when** I switch it to maintenance, **then** the system warns me how many reservations are affected before I confirm.
- **Given** a room in maintenance, **when** an agent searches for availability, **then** the room isn't offered.

*Traces to: FR-10, BR-07. Priority: Should.*

### US-13: Manage seasons
**As a** hotel manager, **I want to** create seasons with a surcharge, **so that** prices follow demand (for example December and Easter week).

- **Given** a new season whose dates overlap an existing one, **when** I save it, **then** the system rejects it, because every day must belong to exactly one season.
- **Given** a season name that already exists, **when** I save it, **then** the system rejects the duplicate.
- **Given** a season with reservations, **when** I try to delete it, **then** the system blocks it.

*Traces to: FR-11, BR-09, BR-14. Priority: Must.*

## Epic 5: Analytics

### US-14: Track hotel performance
**As a** revenue and marketing lead, **I want to** see occupancy, revenue, channels, booking lead time and satisfaction, and compare a month with the same month last year, **so that** I can make pricing and marketing decisions.

- **Given** a selected month, **when** I open the performance page, **then** I see occupancy, realized revenue (completed and in-progress stays) and expected revenue (confirmed future stays), shown separately.
- **Given** any table on the page, **when** I click export, **then** I get an Excel file.
- **Given** I'm a data analyst, **when** I write a query on the SQL page, **then** only `SELECT` statements run, and nothing can be changed.

*Traces to: FR-09, FR-13, FR-14, FR-15, FR-16. Priority: Should.*

---

## Epic 6: Cancellation risk

### US-15: See a new booking's cancellation risk before confirming
**As a** front-desk agent, **I want to** see how likely a new booking is to be cancelled before I confirm it, **so that** I can ask for a deposit when the risk is high.

- **Given** I've chosen the guest, dates, channel and room, **when** I reach the confirmation step, **then** I see the risk level (high, medium or low), how many of every 100 similar bookings were cancelled in the past, and the recommended action.
- **Given** a walk-in guest arriving today, **when** I reach the confirmation step, **then** the risk is low, because walk-ins have never cancelled.
- **Given** the model can't be calculated (for example, not enough history), **when** I confirm, **then** the booking is still saved normally.

*Traces to: FR-17. Priority: Should.*

### US-16: Prioritize upcoming reservations by risk
**As a** front-desk agent, **I want** a list of upcoming reservations ranked by cancellation risk, **so that** I can confirm the riskiest ones a week before arrival.

- **Given** the risk page, **when** I pick "next 30 days" and "high", **then** I see those reservations from highest to lowest risk, with the guest, room, arrival date, channel, value and recommended action.
- **Given** the list, **when** I look at the summary, **then** I see how much revenue is in high-risk reservations and how much could be lost.
- **Given** I'm the hotel manager, **when** I open "How the model works", **then** I see its accuracy on recent bookings, the real cancellation rate of each level, and which variables matter most.

*Traces to: FR-18, BO-6. Priority: Should.*

---

## Traceability matrix

| Requirement | User story | Implemented in |
|---|---|---|
| FR-01 | US-01 | `app_pages/guests.py`, `rules.py`, DDL `ck_guest_id_format` |
| FR-02 | US-02 | `app_pages/guests.py`, `rules.py` |
| FR-03 | US-04 | `app_pages/new_reservation.py` |
| FR-04 | US-05 | `app_pages/new_reservation.py` |
| FR-05 | US-06 | `app_pages/new_reservation.py`, DDL `ck_reservation_*` |
| FR-06 | US-07 | `app_pages/reservations.py` |
| FR-07 | US-08 | `app_pages/reservations.py` |
| FR-08 | US-09, US-10 | `app_pages/today.py`, `app_pages/reservations.py`, `rules.py` |
| FR-09 | US-14 | `app_pages/occupancy_map.py` |
| FR-10 | US-12 | `app_pages/rooms.py` |
| FR-11 | US-13 | `app_pages/seasons.py` |
| FR-12 | US-11 | `app_pages/reservations.py`, DDL `ck_reservation_rating_status` |
| FR-13 | US-14 | `app_pages/performance.py` |
| FR-14 | US-14 | `app_pages/customers.py` |
| FR-15 | US-14 | `app_pages/sql_queries.py` |
| FR-16 | US-14 | `ui.py` |
| FR-17 | US-15 | `app_pages/new_reservation.py`, `risk.py` |
| FR-18 | US-16 | `app_pages/cancellation_risk.py`, `risk.py` |
