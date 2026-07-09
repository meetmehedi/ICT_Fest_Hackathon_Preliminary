## Bug 1 — Access Token Expiry Calculated Incorrectly (Easy)
**File:** `app/auth.py`, line 50
**Bug:** `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)` was missing `minutes=`, so it defaulted to 15 *days* instead of 15 *minutes*.
**Fix:** Explicitly passed `minutes=ACCESS_TOKEN_EXPIRE_MINUTES`.

## Bug 2 — Logout Revoked Check Uses Wrong Claim (Medium)
**File:** `app/auth.py`, line 97
**Bug:** The revocation check `payload.get("sub") in _revoked_tokens` checked the user ID instead of the token's unique ID (`jti`). Logging out would never actually blacklist the token.
**Fix:** Changed to check `payload.get("jti")`.

## Bug 3 — Registration Does Not Return 409 for Duplicate Username (Easy)
**File:** `app/routers/auth.py`, line 37
**Bug:** When registering a duplicate username, the endpoint just returned HTTP 200 OK with the existing user's details, instead of raising `409 USERNAME_TAKEN`.
**Fix:** Raised `AppError(409, "USERNAME_TAKEN", ...)` if `existing is not None`.

## Bug 4 — Refresh Tokens Are Not Single-Use (Hard)
**File:** `app/routers/auth.py`
**Bug:** The `/refresh` endpoint did not invalidate the refresh token after it was used. This violated the security requirement that refresh tokens must be strictly single-use.
**Fix:** Added the old token's `jti` to the `_revoked_tokens` list before generating the new token pair.

## Bug 5 — Datetime Timezone Conversion Strips Offset (Medium)
**File:** `app/timeutils.py`, line 13
**Bug:** `parse_input_datetime` stripped the `tzinfo` from aware datetimes without first converting them to UTC. This effectively changed the absolute time to whatever the local time string was.
**Fix:** Added `.astimezone(timezone.utc)` before dropping the `tzinfo`.

## Bug 6 — Start Time Allows 5-Minute Grace Window in the Past (Easy)
**File:** `app/routers/bookings.py`, line 86
**Bug:** The `create_booking` check `start >= now - timedelta(minutes=5)` allowed bookings up to 5 minutes in the past, violating the "strictly in the future... no grace window" rule.
**Fix:** Changed check to strictly `start > now`.

## Bug 7 — Overlap Check Blocks Back-to-Back Bookings (Medium)
**File:** `app/routers/bookings.py`, line 50
**Bug:** The conflict check used `<=` and `>=`, causing a booking ending at 14:00 to conflict with a booking starting at 14:00.
**Fix:** Changed to strict `<` (`b.start_time < end and start < b.end_time`).

## Bug 8 — Missing Minimum Duration Check (Easy)
**File:** `app/routers/bookings.py`
**Bug:** Checked for maximum duration but failed to enforce `MIN_DURATION_HOURS`.
**Fix:** Added `if duration_hours < MIN_DURATION_HOURS: raise AppError(...)`.

## Bug 9 — Missing `end_time > start_time` Validation (Easy)
**File:** `app/routers/bookings.py`
**Bug:** Failed to validate that `end_time` is logically after `start_time`.
**Fix:** Added validation for `end <= start` to raise a 400 error.

## Bug 10 — `list_bookings` Ordering, Offset, and Limit (Medium)
**File:** `app/routers/bookings.py`, line 137
**Bug:** Ordered by `desc()` instead of `asc()`. Offset calculated as `page * limit` instead of `(page - 1) * limit`. Hardcoded `.limit(10)` instead of using the query parameter.
**Fix:** Corrected all three to `asc()`, `(page - 1) * limit`, and `.limit(limit)`.

## Bug 11 — `get_booking` Overwrites `start_time` (Easy)
**File:** `app/routers/bookings.py`, line 166
**Bug:** The endpoint accidentally reassigned `booking.start_time = booking.created_at` before serialization.
**Fix:** Removed the reassignment line.

## Bug 12 — Refund Policy `< 24h` Returns 50% (Medium)
**File:** `app/routers/bookings.py`, line 206
**Bug:** `notice_hours < 24` fell into the `else` block which was set to `refund_percent = 50` instead of `0`.
**Fix:** Corrected the else block to `refund_percent = 0`.

## Bug 13 — `refund_amount_cents` Inconsistency (Medium)
**File:** `app/routers/bookings.py`, lines 208–210
**Bug:** Cancel response computed `refund_amount_cents` independently from `log_refund()`. With different rounding, they could diverge. Spec mandates they be equal.
**Fix:** `log_refund()` returns the RefundLog entry; `refund_amount_cents = refund_log.amount_cents`.

## Bug 14 — Refund Rounding Uses Truncation Instead of Half-Up (Medium)
**File:** `app/services/refunds.py`, line 17
**Bug:** `int(refund_dollars * 100)` truncates instead of rounding. Spec requires half-cents round up.
**Fix:** `math.floor(booking.price_cents * percent / 100.0 + 0.5)`.

## Bug 15 — Reference Code Counter Is Not Atomic (Hard)
**File:** `app/services/reference.py`
**Bug:** Non-atomic read-modify-write with a `time.sleep(0.12)` between read and write guarantees duplicate codes under concurrency.
**Fix:** Protected with `threading.Lock()`, removed the sleep.

## Bug 16 — Rate Limiter Records Request Before Checking Limit (Hard)
**File:** `app/services/ratelimit.py`
**Bug:** Request appended to bucket before the limit check, plus a `time.sleep(0.1)` created race conditions. The 21st request always passed.
**Fix:** Check `len(bucket) >= _MAX_REQUESTS` before appending; protected with `threading.Lock()`.

## Bug 17 — Room Stats Use Inconsistent In-Memory Cache (Hard)
**File:** `app/services/stats.py`
**Bug:** In-memory read-modify-write with `time.sleep(0.1)` between read and write guaranteed stale/wrong stats under concurrent bookings/cancellations.
**Fix:** Removed in-memory cache. `stats.get()` now queries DB directly with `COUNT`/`SUM` aggregates for always-consistent results.

## Additional Fix — Cache Invalidation Gaps
**Files:** `app/routers/bookings.py`
**Bug:** Creating a booking did not invalidate the usage report cache. Cancelling a booking did not invalidate the availability cache.
**Fix:** Added `cache.invalidate_report(user.org_id)` on create, and `cache.invalidate_availability(...)` on cancel.

## Bug 18 — Deadlock in Notifications Service (Hard)
**File:** `app/services/notifications.py`
**Bug:** `notify_created` acquired `_email_lock` then `_audit_lock`, while `notify_cancelled` acquired `_audit_lock` then `_email_lock`. This classic lock-order inversion causes deadlocks under concurrent load.
**Fix:** Modified both functions to always acquire locks in the same order (`_email_lock` then `_audit_lock`).

## Bug 19 — Double Cancel Race Condition (Hard)
**File:** `app/routers/bookings.py`, `app/services/refunds.py`
**Bug:** `log_refund` committed its transaction, then `_settlement_pause()` ran before setting `booking.status = "cancelled"` and committing. This allowed a concurrent cancel request to pass the `booking.status == "cancelled"` check, resulting in multiple refunds.
**Fix:** `log_refund` now uses `db.flush()` instead of `db.commit()`. The status change and refund log are committed atomically in the router after `log_refund` returns. Removed the artificial `_settlement_pause()`.

## Bug 20 — Multi-Tenancy Bypass in Export (Hard)
**File:** `app/services/export.py`
**Bug:** When `include_all=True` and `room_id` was provided, the export used `fetch_bookings_raw(db, room_id)` which queried the `bookings` table directly without joining `Room` and checking `org_id`. This allowed an admin to export bookings from another organization's room.
**Fix:** Modified `generate_export` to always use `_fetch_scoped(db, org_id, None, room_id)` for the `include_all` case, which enforces the `org_id` isolation.

## Bug 21 — `get_booking` Allows Cross-Member Read (Medium)
**File:** `app/routers/bookings.py`
**Bug:** The endpoint checked that the room belonged to the caller's organization (`Room.org_id == user.org_id`), but did not enforce Rule 10 ("Members may read and cancel only their own bookings"). A member could query another member's booking ID and read it.
**Fix:** Added `if user.role != "admin" and booking.user_id != user.id: raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found")`.

## Bug 22 & Bug 23 — Concurrency Races in Booking Creation (Hard)
**File:** `app/routers/bookings.py`
**Bug:** The `_has_conflict()` and `_check_quota()` functions read from the database, experienced an artificial delay (`time.sleep()`), and then the booking was inserted. This created two huge race windows.
**Fix:** Created a global `_booking_lock = threading.Lock()` and wrapped the conflict check, quota check, and `db.commit()` inside this lock to make the check-and-insert sequence atomic across concurrent requests.

## Bug 24 — Missing Duplicate Name Check on Room Creation (Medium)
**File:** `app/routers/rooms.py`
**Bug:** The `create_room` endpoint did not check if a room with the same name already existed in the organization. If a duplicate was inserted, SQLite's unique constraint threw an `IntegrityError`, resulting in a 500 Internal Server Error instead of the required 409 Conflict.
**Fix:** Added an explicit query for `existing = db.query(Room).filter(...)` and raised a 409 `ROOM_NAME_TAKEN` AppError.

## Bug 25 — Missing Validation on Room Capacity and Rate (Easy)
**File:** `app/routers/rooms.py`
**Bug:** Pydantic's `RoomCreateRequest` did not enforce the business rules that capacity must be `> 0` and hourly rate `>= 0`. Negative values could be stored.
**Fix:** Added an explicit check in `create_room` to ensure `capacity > 0` and `hourly_rate_cents >= 0`, raising a 400 Bad Request otherwise.

## Bug 26 — Missing Database UniqueConstraint on Room (Medium)
**File:** `app/models.py`
**Bug:** The `Room` model did not have `__table_args__ = (UniqueConstraint("org_id", "name"),)` defined, meaning the database layer did not actually enforce room name uniqueness per organization. If the application-level check failed or was bypassed, the database would happily store duplicates.
**Fix:** Added the `UniqueConstraint` to the `Room` model.

## Bug 27 — Missing Unique Constraint on Reference Code (Medium)
**File:** `app/models.py`
**Bug:** The business rules dictate that reference codes must be unique system-wide. The `reference_code` column on the `Booking` model was missing `unique=True`.
**Fix:** Added `unique=True` to the `reference_code` column definition.

## Bug 28 — Room Creation Fails to Invalidate Report Cache (Medium)
**File:** `app/routers/rooms.py`
**Bug:** The `create_room` endpoint did not invalidate the organization's usage report cache. Since the usage report returns a list of *all* rooms in the organization (even those with 0 bookings), a newly created room would not appear in the report until the cache naturally expired.
**Fix:** Added `cache.invalidate_report(admin.org_id)` to the end of `create_room`.

## Bug 29 — Missing Past Booking Check on Cancellation (Hard)
**File:** `app/routers/bookings.py`
**Bug:** The `cancel_booking` endpoint calculated the notice period, but did not check if the booking had already started or was in the past. If a past booking was canceled, the `notice.total_seconds()` would be negative, which fell through to the `else` block (0% refund) and successfully cancelled the past booking, violating the rule: "Cancelling is prohibited if start_time is in the past".
**Fix:** Added an explicit check `if booking.start_time <= datetime.utcnow(): raise AppError(400, "PAST_BOOKING", ...)` to prevent past cancellations.

## Bug 30 — Admin List Bookings Missing Org Scope (Hard)
**File:** `app/routers/bookings.py`
**Bug:** The `list_bookings` endpoint unconditionally filtered by `Booking.user_id == user.id`. This meant that even organization admins could only see their own personal bookings, rather than all bookings across the organization, violating Rule 9.
**Fix:** Added a conditional check. If `user.role == "admin"`, it joins `Room` and filters by `Room.org_id == user.org_id`.
