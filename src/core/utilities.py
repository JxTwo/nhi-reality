from datetime import datetime, timezone
from django.utils.timezone import is_aware

def normalize_date(obj):
    dt = obj.published_at
    # Convert date to datetime if needed
    if isinstance(dt, datetime):
        pass  # already datetime
    else:
        dt = datetime.combine(dt, datetime.min.time())

    # Convert to naive UTC
    if is_aware(dt):
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
