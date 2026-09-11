"""
Day-code computation.

Priority: if a date sits within 4 days *before* a fixture, it is labelled
relative to that upcoming match (MD-4...MD-1) -- taper into the next game
takes priority. Otherwise, if it sits within 2 days *after* a fixture, it is
labelled relative to that match (MD+1/MD+2). This means a congested run
(e.g. a 3-4 day turnaround) compresses or skips recovery days rather than
compressing the taper -- matching the "adapting to shorter microcycles"
guidance in the source framework. Any single day can be overridden manually
in the app.
"""

from datetime import date, timedelta
from constants import DEFAULT_TYPE


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_dates(week_start: date):
    return [week_start + timedelta(days=i) for i in range(7)]


def fmt_day_header(d: date) -> str:
    # Built manually rather than with the platform-specific "%-d" / "%#d"
    # strftime flags, so this works the same on Linux, macOS and Windows.
    return f"{d.strftime('%a').upper()} {d.day} {d.strftime('%b')}"


def fmt_week_range(week_start: date) -> str:
    dates = week_dates(week_start)
    a, b = dates[0], dates[6]
    if a.month == b.month:
        return f"{a.day}–{b.day} {a.strftime('%b')} {a.year}"
    return f"{a.day} {a.strftime('%b')} – {b.day} {b.strftime('%b')} {b.year}"


def compute_day_code(d: date, fixtures: list[dict]):
    """
    fixtures: list of dicts with a 'date' key holding a date object (or
    ISO string -- both are handled), sorted or not.
    Returns (code, fixture_dict_or_None).
    """
    def fx_date(f):
        v = f["date"]
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    for f in fixtures:
        if fx_date(f) == d:
            return "MD", f

    prev, next_ = None, None
    for f in fixtures:
        fd = fx_date(f)
        if fd < d and (prev is None or fd > fx_date(prev)):
            prev = f
        if fd > d and (next_ is None or fd < fx_date(next_)):
            next_ = f

    n = (fx_date(next_) - d).days if next_ else None
    p = (d - fx_date(prev)).days if prev else None

    if n is not None and 1 <= n <= 4:
        return f"MD-{n}", next_
    if p is not None and 1 <= p <= 2:
        return f"MD+{p}", prev
    return None, (next_ or prev)


def effective_code(d: date, session: dict | None, fixtures: list[dict]):
    """Returns (code, fixture, is_auto)."""
    computed_code, fixture = compute_day_code(d, fixtures)
    override = (session or {}).get("day_code_override")
    if override:
        return override, fixture, False
    return computed_code, fixture, True


def default_session_type(code: str | None) -> str:
    if code and code in DEFAULT_TYPE:
        return DEFAULT_TYPE[code]
    return "Training"
