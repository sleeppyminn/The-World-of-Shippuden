# ═══════════════════════════════════════════════════════
#  story/common.py — chapter builder shared by every country
#  Boss stats are computed from the chapter's rank + a
#  "k" value (0.0 = easy end of the rank, 1.0 = hard end),
#  so you never have to hand-balance HP/ATK again.
# ═══════════════════════════════════════════════════════

# rank: (hp_lo, hp_hi, atk_lo, atk_hi, exp_lo, exp_hi, kills)
RANK_STATS = {
    "Genin":         (60,   100,   9,  14,  60,  80, 2),
    "Chunin":        (115,  165,  15,  20,  90, 120, 2),
    "Special Jonin": (180,  240,  21,  27, 130, 170, 3),
    "Jonin":         (260,  340,  28,  35, 180, 230, 3),
    "ANBU":          (380,  490,  36,  45, 240, 300, 4),
    "Elite Jonin":   (520,  640,  46,  56, 320, 380, 4),
    "Sannin-Class":  (700,  860,  57,  68, 400, 460, 5),
    "Kage-Level":    (950, 1200,  69,  85, 480, 560, 5),
}


def _lerp(lo: int, hi: int, k: float) -> int:
    return int(lo + (hi - lo) * k)


# Balance multipliers (tuned with a Monte-Carlo battle simulation so that an
# on-level player needs ~8 turns per boss and ends around 30-50% HP).
HP_MULT  = {"Genin": 2.3, "Chunin": 2.6, "Special Jonin": 3.2, "Jonin": 3.4,
            "ANBU": 3.5, "Elite Jonin": 3.0, "Sannin-Class": 2.5, "Kage-Level": 2.2}
ATK_MULT = {"Genin": 1.0, "Chunin": 1.0, "Special Jonin": 1.1, "Jonin": 1.1,
            "ANBU": 1.1, "Elite Jonin": 1.05, "Sannin-Class": 1.0, "Kage-Level": 0.9}

# Level a player is expected to be at when they reach each rank's chapters
REC_LEVEL = {"Genin": 3, "Chunin": 7, "Special Jonin": 13, "Jonin": 21,
             "ANBU": 27, "Elite Jonin": 33, "Sannin-Class": 36, "Kage-Level": 41}


def boss_stats(rank: str, k: float) -> tuple:
    hp_lo, hp_hi, a_lo, a_hi, *_ = RANK_STATS[rank]
    hp  = _lerp(hp_lo, hp_hi, k) * HP_MULT[rank]
    atk = _lerp(a_lo, a_hi, k) * ATK_MULT[rank]
    return int(hp), int(atk)


def chapter(cid, title, rank, k, lines, boss, victory,
            reward=None, choice=None, stages=None, exp=None, gold=None):
    """Build one chapter dict.

    cid      unique id, e.g. "fire_01"  (used in save files)
    stages   optional list of stage dicts (see stage()) for multi-fight chapters
    choice   optional dict -> see game._play_choice()
    reward   optional item name dropped on first clear
    """
    _, _, _, _, e_lo, e_hi, kills = RANK_STATS[rank]
    hp, atk = boss_stats(rank, k)
    total_exp = exp if exp is not None else _lerp(e_lo, e_hi, k)
    return {
        "id": cid, "title": title, "rank": rank, "rec_level": REC_LEVEL[rank],
        "lines": lines, "boss": boss, "boss_hp": hp, "boss_atk": atk,
        "victory_lines": victory,
        "exp": total_exp,
        "gold": gold if gold is not None else total_exp // 3,
        "kills": kills,
        "reward": reward,
        "choice": choice,
        "stages": stages,
    }


def stage(rank, label, k, lines, boss, victory, choice=None):
    hp, atk = boss_stats(rank, k)
    return {"label": label, "lines": lines, "boss": boss,
            "boss_hp": hp, "boss_atk": atk,
            "victory_lines": victory, "choice": choice}


def choice(prompt, a, b):
    """a / b = (button text, result line, reward dict)
       reward keys: gold, exp, str, spd, end, item"""
    return {"prompt": prompt, "options": [a, b]}
