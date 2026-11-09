# ═══════════════════════════════════════════════════════
#  story/__init__.py — registry of every country's story
#
#  TO ADD A NEW COUNTRY:
#    1. copy any country file (e.g. fire.py) to a new name
#    2. change COUNTRY + write more chapters in CHAPTERS
#    3. import it below and add it to ORDER
#  TO ADD MORE CHAPTERS TO A COUNTRY: just append to its CHAPTERS list.
#  Chapter ids must be unique (they're stored in save files).
# ═══════════════════════════════════════════════════════

from . import fire, wind, lightning, earth, water, rain, iron, grass

ORDER = [fire, wind, lightning, earth, water, rain, iron, grass]

COUNTRIES = [m.COUNTRY for m in ORDER]
CHAPTERS_BY_COUNTRY = {m.COUNTRY["key"]: m.CHAPTERS for m in ORDER}


def total_chapters() -> int:
    return sum(len(c) for c in CHAPTERS_BY_COUNTRY.values())


def all_chapters() -> list:
    return [c for m in ORDER for c in m.CHAPTERS]


def _check_unique() -> None:
    ids = [c["id"] for c in all_chapters()]
    assert len(ids) == len(set(ids)), "Duplicate chapter ids!"


_check_unique()
