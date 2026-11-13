# RF4 Assistant — Records filters v2.1

Changes:
- Restore **Все регионы** (`region=ALL`) as the default selection.
- Remove **Все водоёмы** from the waterbody dropdown.
- Default waterbody stays the first by `sort_order`, then name and ID.
- If an old URL passes an empty `waterbody_id`, fall back to the first waterbody.
- Keep automatic GET application of filters and period buttons.

Replace the two files relative to your Django project root. No migrations required.
