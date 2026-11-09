━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  THE WORLD OF SHIPPUDEN — Naruto Shippuden Text RPG
  Based on the structure of The World of Wisteria
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW TO RUN
  python main.py          (Python 3.8+, no packages needed)
  Optional, for the best sound:   pip install pygame
  Best in a modern terminal with truecolor (Windows Terminal, VS Code,
  iTerm2, GNOME Terminal...) at 80x24 or bigger.

UI NOTES
  - Animated title splash, gradient boxed panels, shinobi card dashboard
  - Battle screen redraws in place: HP bars drain with a ghost trail, the
    hit target flashes, your screen shakes when hit, damage numbers float up
  - Every chakra nature has its own jutsu effect; signature / original
    jutsu get a full-screen flash
  - Ctrl+C while story text is typing skips to the end of that panel
  - SHIPPUDEN_FAST=1 python main.py   turns off all animation delays
    (handy for testing; also automatic when output is piped)

SOUND & MUSIC  (new)
  5 looping music tracks:  title · village (menus) · story (world map/chapters)
                           battle (missions) · boss (story fights)
  41 sound effects: menu clicks, a different sound for each chakra nature
  (Fire, Water, Wind, Lightning, Earth, Shadow, Taijutsu, Genjutsu), signature/
  original jutsu charge-ups, hits, crits, dodge, guard, awakening, level-up,
  victory / defeat / promotion fanfares, gacha clan reveal, shop coins, save chime,
  and rhythm cues in the training mini-games.
  - Everything is original and synthesized (taiko, koto, shamisen, shakuhachi-style
    flute in Japanese scales). No copyrighted music.
  - Turn music / effects on or off:  main menu [3] Sound, or [S] in the game menu.
    Your choice is saved in shippuden_audio.json.
  - Players used, in order: pygame -> Windows built-in (winsound + MCI) ->
    afplay (macOS) / paplay / aplay / ffplay / play / mpv (Linux).
    No player found = the game just runs silent.
  - SHIPPUDEN_MUTE=1 python main.py     start muted
  - Want to change the sounds?  pip install numpy, edit tools/make_audio.py,
    run  python tools/make_audio.py   (rewrites everything in assets/)

FILE STRUCTURE
  main.py        entry point
  audio.py       music + sound effects (backend picker, throttling, settings)
  assets/        music/*.wav and sfx/*.wav (made by tools/make_audio.py)
  tools/         make_audio.py — the sound synthesizer
  character.py   Character(ABC)            — abstraction, encapsulation
  player.py      Player(Character)         — chakra, jutsu, ranks
  enemy.py       Enemy(Character)          — polymorphic attack()
  item.py        Item.use()
  game.py        game loop, battle, menus, save/load
  anim.py        UI engine: gradient panels, animated title, battle
                 screen (HP drain, hit flash, jutsu effects), banners
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
