from datetime import datetime

from fastapi import HTTPException


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") + "Z" if dt else None


def parse_day(value: str | None, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, "Dates must look like YYYY-MM-DD")
    if end_of_day and len(value) <= 10:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt
