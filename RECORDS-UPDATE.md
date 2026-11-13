# RF4 Assistant — bait catalog and missing icons

The update builds on the previous records integration v1.1. It does not change the existing unique catch fingerprint, so existing catches and collections remain intact.

## What changed

- `records.Bait`: unique name and locally saved WebP icon (`baits`).
- `records.Catch`: nullable `bait1` and `bait2` foreign keys, with `PROTECT` on deletion.
- The exact source `bait` text is preserved for diagnostics and fingerprint compatibility.
- A schema/data migration populates bait references in previously collected catches.
- `fish.Fish.image` added for fish icons (the previous model had no image field).
- After a weekly collection the standalone worker attempts to fetch missing icons from the official RF4 `/res/` URLs. Only the first bait has a source icon. If the second bait later appears first, the same catalog row will receive its icon.
- Download failures are logged, do not block persistence, and may be retried in a later collection.
- Icon filenames are UUID-based WebP files. Already existing image files are not overwritten.

## Install (Windows PowerShell, from project root)

1. Back up `db.sqlite3` and `media/`.
2. Stop the standalone collector. Replace project files with the contents of `rf4-django-v1/` from this archive. Keep your existing `db.sqlite3` and `media/`.
3. Run:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test records
.\.venv\Scripts\python.exe manage.py collect_weekly_records --regions RU GL
```

You do not need to reimport the test-project database. A periodic collection is started separately:

```powershell
.\.venv\Scripts\python.exe manage.py collect_weekly_records --loop --interval-minutes 15
```

Note: RF4 listings show only a limited top-N number of catches per fish. Counted records are not all game catches. The catalog matches bait names exactly; aliases are not automatically merged.
