"""Live per-room booking statistics.

Stats are queried directly from the database so they are always consistent
with the actual booking table, even under concurrent activity.
"""
from sqlalchemy import func

# These are kept for API compatibility but do nothing — DB is source of truth.
def record_create(room_id: int, price_cents: int) -> None:
    pass


def record_cancel(room_id: int, price_cents: int) -> None:
    pass


def get(room_id: int, db=None) -> dict:
    """Return confirmed-booking count and total revenue for the room.

    Callers that have a db session should pass it in; the router does this
    by importing and calling this function with the session.
    """
    if db is None:
        # Fallback: return zeros (should not happen in practice)
        return {"count": 0, "revenue": 0}
    from ..models import Booking
    row = (
        db.query(
            func.count(Booking.id).label("count"),
            func.coalesce(func.sum(Booking.price_cents), 0).label("revenue"),
        )
        .filter(Booking.room_id == room_id, Booking.status == "confirmed")
        .one()
    )
    return {"count": row.count, "revenue": row.revenue}
