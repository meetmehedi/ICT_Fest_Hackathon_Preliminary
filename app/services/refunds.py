"""Refund bookkeeping.

When a booking is cancelled a refund is calculated from its price and the
applicable notice tier, then written to the refund ledger with a processed
status. Amounts are stored in whole cents.
"""
import math
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import Booking, RefundLog


def log_refund(db: Session, booking: Booking, percent: int) -> RefundLog:
    # Spec: "rounds to the nearest cent, half-cents rounding up"
    raw = booking.price_cents * percent / 100.0
    amount_cents = math.floor(raw + 0.5)  # half-up rounding
    entry = RefundLog(
        booking_id=booking.id,
        amount_cents=amount_cents,
        status="processed",
        processed_at=datetime.utcnow(),
    )
    db.add(entry)
    db.flush()   # Write to DB within current transaction without committing
    db.refresh(entry)
    return entry
