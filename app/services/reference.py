"""Human-facing booking reference codes.

Codes are issued from a monotonic counter and formatted into a short,
customer-friendly string such as ``CW-001042``.
"""
import threading

_counter = {"value": None}
_lock = threading.Lock()


def next_reference_code(db) -> str:
    with _lock:
        if _counter["value"] is None:
            from ..models import Booking
            latest_booking = db.query(Booking).order_by(Booking.reference_code.desc()).first()
            if latest_booking:
                ref = latest_booking.reference_code
                try:
                    num_part = int(ref.split("-")[1])
                    _counter["value"] = max(1000, num_part + 1)
                except (IndexError, ValueError):
                    _counter["value"] = 1000
            else:
                _counter["value"] = 1000

        current = _counter["value"]
        _counter["value"] = current + 1
    return f"CW-{current:06d}"
