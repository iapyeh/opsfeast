"""Local, whole-second wall time for human views; never rewrite source data."""
from datetime import datetime


def local_datetime(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone() if parsed.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        return None


def format_time(value):
    local = local_datetime(value)
    return local.strftime('%Y-%m-%d %H:%M:%S') if local is not None else value


def human_times(value):
    """Copy a display value, converting zoned ISO timestamps at every depth."""
    if isinstance(value, dict):
        return {key: human_times(item) for key, item in value.items()}
    if isinstance(value, list):
        return [human_times(item) for item in value]
    if isinstance(value, tuple):
        return tuple(human_times(item) for item in value)
    return format_time(value)
