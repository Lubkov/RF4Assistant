"""Parse RF4 bait title into at most two independent catalog references."""


def split_baits(value):
    parts = [part.strip() for part in (value or "").split(";") if part.strip()]
    if len(parts) > 2:
        raise ValueError(f"Expected no more than two baits, got: {value!r}")
    return tuple(parts + [None] * (2 - len(parts)))
