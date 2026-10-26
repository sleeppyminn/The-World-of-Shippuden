━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  THE WORLD OF SHIPPUDEN — Naruto Shippuden Text RPG
  Based on the structure of The World of Wisteria
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW TO RUN
  python main.py          (Python 3.8+, no packages needed)

FILE STRUCTURE
  main.py        entry point
  character.py   Character(ABC)            — abstraction, encapsulation
  player.py      Player(Character)         — chakra, jutsu, ranks
  enemy.py       Enemy(Character)          — polymorphic attack()
  item.py        Item.use()
  game.py        game loop, battle, menus, save/load
  anim.py        animated text / banners
  data.py        clans, jutsu styles, items, missions, ranks
  story/         ONE FILE PER COUNTRY (chapters live here)
    common.py    chapter() builder + boss balance tables
    fire.py wind.py lightning.py earth.py
    water.py rain.py iron.py grass.py

CURRENT STORY: 50 chapters
  Fire 12 | Wind 7 | Lightning 6 | Earth 5 | Water 5 | Rain 5 | Iron 5 | Grass/Sound 5

HOW TO ADD MORE CHAPTERS (goal: ~200)
  1. Open a country file, e.g. story/fire.py
  2. Append to CHAPTERS:
       ch("fire_13", "CHAPTER 13 — TITLE", "Sannin-Class", 0.7,
          ["intro line", ...], "Boss Name", ["victory line", ...])
     arguments: id, title, rank, k (0=easy..1=hard in that rank),
     intro lines, boss name, victory lines
     optional: reward="Item", choice=choice(...), stages=[stage(...), ...]
  3. Boss HP/ATK/EXP/gold/kills are computed automatically from rank + k.
  NEW COUNTRY: copy a country file, then add it to ORDER in story/__init__.py.
  Chapter ids must be unique (they are stored in save files).

GAMEPLAY
  Mission Board (D–S rank) for kills/gold, Story Missions by country,
  Training mini-games, Shop, Chakra system (jutsu cost chakra),
  Jonin awakening ([M] in battle), Signature jutsu, Kage-Level original jutsu,
  Save/Load (shippuden_save.json).
  Clan roll is a gacha: Common → Secret.
