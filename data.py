RESET   = "\033[0m"
RED     = "\033[31m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
BLUE    = "\033[34m"
MAGENTA = "\033[35m"
CYAN    = "\033[36m"
WHITE   = "\033[37m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

COLORS = {"RED": RED, "GREEN": GREEN, "YELLOW": YELLOW, "BLUE": BLUE,
          "MAGENTA": MAGENTA, "CYAN": CYAN, "WHITE": WHITE}

MAX_HP          = 100
LEVEL_HP_BONUS  = 15
LEVEL_ATK_BONUS = 3
MIN_DAMAGE      = 1
TRAIN_CAP       = 5


def exp_needed(level: int) -> int:
    """EXP required to climb from `level` to `level + 1`."""
    return 50 + 12 * (level - 1)


# ── Clans (gacha roll at character creation) ─────────────
CLAN_POOL = {
    # Common
    "Mitarashi":   {"rarity": "Common",    "stats": (2, 2, 3)},
    "Morino":      {"rarity": "Common",    "stats": (3, 1, 3)},
    "Yakushi":     {"rarity": "Common",    "stats": (2, 3, 2)},
    "Shiranui":    {"rarity": "Common",    "stats": (1, 2, 4)},
    "Akado":       {"rarity": "Common",    "stats": (3, 2, 2)},
    "Namiashi":    {"rarity": "Common",    "stats": (2, 1, 4)},
    # Uncommon
    "Yamanaka":    {"rarity": "Uncommon",  "stats": (3, 4, 3)},
    "Akimichi":    {"rarity": "Uncommon",  "stats": (5, 2, 4)},
    "Inuzuka":     {"rarity": "Uncommon",  "stats": (4, 4, 3)},
    "Aburame":     {"rarity": "Uncommon",  "stats": (3, 3, 5)},
    # Rare
    "Nara":        {"rarity": "Rare",      "stats": (3, 6, 6)},
    "Hyuga":       {"rarity": "Rare",      "stats": (5, 6, 4)},
    "Yuki":        {"rarity": "Rare",      "stats": (4, 7, 5)},
    "Hozuki":      {"rarity": "Rare",      "stats": (6, 5, 5)},
    "Sarutobi":    {"rarity": "Rare",      "stats": (6, 4, 6)},
    # Legendary
    "Hatake":      {"rarity": "Legendary", "stats": (6, 8, 5)},
    "Uchiha":      {"rarity": "Legendary", "stats": (7, 8, 5)},
    "Uzumaki":     {"rarity": "Legendary", "stats": (6, 5, 9)},
    "Kaguya":      {"rarity": "Legendary", "stats": (9, 5, 7)},
    "Senju":       {"rarity": "Legendary", "stats": (8, 5, 9)},
    "Namikaze":    {"rarity": "Legendary", "stats": (6, 10, 5)},
    # Mythic
    "Hagoromo":    {"rarity": "Mythic",    "stats": (12, 10, 12)},
    "Otsutsuki":   {"rarity": "Mythic",    "stats": (14, 11, 11)},
    # Secret
    "Yoo":         {"rarity": "Secret",    "stats": (15, 18, 15)},
    "Tolentino":   {"rarity": "Secret",    "stats": (17, 16, 16)},
    "Nona":        {"rarity": "Secret",    "stats": (18, 15, 17)},
}

RARITY_COLORS = {
    "Common": WHITE, "Uncommon": GREEN, "Rare": CYAN,
    "Legendary": YELLOW, "Mythic": MAGENTA, "Secret": RED,
}

RARITY_WEIGHTS = {
    "Common": 40, "Uncommon": 25, "Rare": 15,
    "Legendary": 5, "Mythic": 2, "Secret": 1,
}

# ── Home villages ────────────────────────────────────────
#   country = key of the country in story/ that counts as "home"
VILLAGES = {
    "Konoha": {"country": "fire",      "bonus": (1, 1, 1), "desc": "The Leaf — balanced and resourceful."},
    "Suna":   {"country": "wind",      "bonus": (0, 3, 0), "desc": "The Sand — quick, patient, desert-hardened."},
    "Kumo":   {"country": "lightning", "bonus": (2, 1, 0), "desc": "The Cloud — raw power and speed."},
    "Iwa":    {"country": "earth",     "bonus": (1, 0, 2), "desc": "The Stone — stubborn endurance."},
    "Kiri":   {"country": "water",     "bonus": (1, 2, 0), "desc": "The Mist — silent and precise."},
}

# ── Ninja ranks (earned by kills — missions & story bosses) ──
NINJA_RANKS = [
    ("Genin",          0),
    ("Chunin",         6),
    ("Special Jonin", 16),
    ("Jonin",         30),
    ("ANBU",          48),
    ("Elite Jonin",   70),
    ("Sannin-Class",  95),
    ("Kage-Level",   125),
]
RANK_NAMES = [r[0] for r in NINJA_RANKS]

# ── Jutsu styles ─────────────────────────────────────────
#   jutsu entry = (name, power, chakra_cost, description)
#   damage = ATK + power + small roll
STYLES = {
    "Fire": {
        "jutsu": [
            ("Fire Release: Fireball Jutsu",          8,  8,  "A huge ball of flame — the classic opener."),
            ("Fire Release: Phoenix Sage Flower",    12, 11,  "Small fireballs scatter and burn from every angle."),
            ("Fire Release: Dragon Flame Bullet",    17, 15,  "A dragon of fire chases the enemy down."),
            ("Fire Release: Great Fire Destruction", 23, 20,  "A wall of flame that scours the ground."),
            ("Fire Release: Ash Pile Burning",       30, 26,  "Smoke ignites into a cloud of flame."),
        ],
        "ult": ("Fire Release: Great Fire Annihilation", 55, 40, "A sea of fire that swallows the horizon."),
        "awaken": ("Sharingan", "Crimson eyes spin to life. Every movement slows to a crawl."),
    },
    "Water": {
        "jutsu": [
            ("Water Release: Water Gun",             8,  8,  "A compressed jet of water, sharp as a blade."),
            ("Water Release: Water Wall",            11, 10, "A rising wall that crashes down."),
            ("Water Release: Water Dragon Bullet",   17, 15, "A dragon of water that coils around the enemy."),
            ("Water Release: Water Prison",          22, 19, "A sphere of water that traps the enemy."),
            ("Water Release: Great Waterfall",       30, 26, "A cascade of water crashes over the battlefield."),
        ],
        "ult": ("Water Release: Great Exploding Water Colliding Wave", 55, 40, "A tidal wave of impossible size."),
        "awaken": ("Hidden Mist Mastery", "Mist coils around you. The enemy can no longer tell where you end."),
    },
    "Wind": {
        "jutsu": [
            ("Wind Release: Air Bullet",             8,  8,  "A compressed gust like a cannonball."),
            ("Wind Release: Wind Blade",             12, 11, "A razor-thin blade of wind."),
            ("Wind Release: Great Breakthrough",     17, 15, "A hurricane that blows the enemy back."),
            ("Wind Release: Vacuum Wave",            23, 20, "Cutting winds of near-vacuum."),
            ("Wind Release: Gale Palm",              30, 26, "A palm strike that tears the air."),
        ],
        "ult": ("Wind Release: Rasenshuriken", 55, 40, "A spinning storm of wind chakra with a thousand edges."),
        "awaken": ("Sage Mode", "Nature’s chakra floods your veins. The wind itself fights for you."),
    },
    "Lightning": {
        "jutsu": [
            ("Lightning Release: Static Pulse",      8,  8,  "A crackling jolt through the enemy’s guard."),
            ("Lightning Release: Chidori Senbon",    12, 11, "Needles of lightning, aimed at pressure points."),
            ("Lightning Release: Lightning Beast",   17, 15, "A hound of lightning that bites on contact."),
            ("Lightning Release: Chidori",           23, 20, "A thousand birds sing as the palm strikes."),
            ("Lightning Release: Thunder Cloud Blade", 30, 26, "A sword of storm and thunder."),
        ],
        "ult": ("Lightning Release: Kirin", 55, 40, "Heaven’s lightning, dragged down by a single hand."),
        "awaken": ("Lightning Armor", "Lightning cloaks your whole body. Every reflex fires faster than thought."),
    },
    "Earth": {
        "jutsu": [
            ("Earth Release: Stone Fist",            8,  8,  "A fist of rock that smashes the guard."),
            ("Earth Release: Mud Wall",              11, 10, "A rising wall that slams into the enemy."),
            ("Earth Release: Rock Shower",           17, 15, "A rain of heavy boulders."),
            ("Earth Release: Earth Dragon Bullet",   23, 20, "A dragon of mud lunges from the ground."),
            ("Earth Release: Stone Golem",           30, 26, "A hulking golem pounds the field."),
        ],
        "ult": ("Earth Release: Earth Style Great Quake", 55, 40, "The ground itself turns on the enemy."),
        "awaken": ("Stone Skin", "Your body hardens to granite. Strikes glance off you like rain on a cliff."),
    },
    "Shadow": {
        "jutsu": [
            ("Shadow Imitation Jutsu",               8,  8,  "Your shadow stretches and pins the enemy."),
            ("Shadow Sewing Needles",                12, 11, "Shadow needles stab through the guard."),
            ("Shadow Neck Bind",                     17, 15, "A tendril of shadow wraps and squeezes."),
            ("Shadow Possession Strike",             23, 20, "Your foe’s own limbs are turned against them."),
            ("Shadow Stitching Spiral",              30, 26, "A spiral of shadows that cuts everything in its path."),
        ],
        "ult": ("Shadow Style: Eclipse Crush", 55, 40, "All shadows converge for a single crushing blow."),
        "awaken": ("Shadow Veil", "You blur into your own shadow. The enemy strikes at echoes."),
    },
    "Taijutsu": {
        "jutsu": [
            ("Leaf Hurricane",                       8,  8,  "A spinning kick that blasts the enemy back."),
            ("Dynamic Entry",                        12, 11, "A flying kick that crashes through defenses."),
            ("Primary Lotus",                        17, 15, "A bandaged spin that slams the enemy down."),
            ("Hidden Lotus",                         23, 20, "A brutal, high-speed combo that opens one gate."),
            ("Evening Elephant",                     30, 26, "An air-splitting barrage of punches."),
        ],
        "ult": ("Eight Gates: Night Guy", 55, 40, "A burst of speed that is itself a weapon."),
        "awaken": ("Gate of Opening", "You open the first gate. Muscles scream. Speed rises beyond mortal limits."),
    },
    "Genjutsu": {
        "jutsu": [
            ("Genjutsu: Demonic Illusion",           8,  8,  "A false world warps the enemy’s mind."),
            ("Genjutsu: Tree Binding Death",         12, 11, "Illusory vines restrain and hurt the foe."),
            ("Genjutsu: Hell Viewing",               17, 15, "The enemy sees the most terrible thing imaginable."),
            ("Genjutsu: Nightmare Ripple",           23, 20, "A ripple of dread peels the mind in layers."),
            ("Genjutsu: Mirror Maze",                30, 26, "A hundred reflections, a hundred wounds."),
        ],
        "ult": ("Genjutsu: Endless Dream", 55, 40, "The enemy is trapped in an infinite loop of defeat."),
        "awaken": ("Mangekyo Awakening", "Your eyes shift and twist. The world bends to the shape of your will."),
    },
}
STYLE_NAMES = list(STYLES.keys())

CUSTOM_JUTSU_TEMPLATE = {"power": 65, "cost": 45}   # Kage-Level original jutsu

# ── Items ────────────────────────────────────────────────
ITEMS = {
    "Dango Skewer":     {"desc": "A sweet snack. Restores 25 HP.",                   "type": "heal",    "value": 25},
    "Ichiraku Ramen":   {"desc": "A hot bowl of ramen. Restores 45 HP.",             "type": "heal",    "value": 45},
    "Ration Bar":       {"desc": "Standard field ration. Restores 40 HP.",           "type": "heal",    "value": 40},
    "Medic Scroll":     {"desc": "Sealed medical ninjutsu. Restores 70 HP.",         "type": "heal",    "value": 70},
    "Soldier Pill":     {"desc": "A battlefield pill. Restores 80 HP.",              "type": "heal",    "value": 80},
    "Tsunade's Elixir": {"desc": "Rare medicine. Fully restores HP.",                "type": "heal",    "value": 9999},
    "Chakra Pill":      {"desc": "Restores 40 chakra.",                              "type": "chakra",  "value": 40},
    "Explosive Tag":    {"desc": "+5 ATK for the next battle.",                      "type": "atk_up",  "value": 5},
    "Akimichi Pill":    {"desc": "+10 END permanently. (Tastes awful.)",             "type": "end_up",  "value": 10},
    "Speed Scroll":     {"desc": "+3 SPD permanently.",                              "type": "spd_up",  "value": 3},
    "Sage Scroll":      {"desc": "A scroll of natural energy. +5 STR permanently.",  "type": "str_up",  "value": 5},
}

SHOP_STOCK  = ["Dango Skewer", "Ichiraku Ramen", "Soldier Pill", "Chakra Pill", "Explosive Tag"]
SHOP_PRICES = {
    "Dango Skewer": 15, "Ichiraku Ramen": 25, "Soldier Pill": 45,
    "Chakra Pill": 30, "Explosive Tag": 30,
}

# ── Mission board ────────────────────────────────────────
#   (letter, min_rank, k, title, briefing, enemy, drop)
MISSIONS = [
    ("D", "Genin", 0.0, "Stray Cat Retrieval",
     "The daimyo’s wife has lost her cat — again. This time it has claws out.",
     "Tora the Runaway Cat", ("Dango Skewer", 0.40)),
    ("D", "Genin", 0.3, "Bandits at the Bridge",
     "A group of thugs is shaking down travellers at the old stone bridge.",
     "Bridge Bandit", ("Ichiraku Ramen", 0.30)),
    ("C", "Chunin", 0.2, "Escort the Merchant",
     "A spice merchant needs safe passage through a forest known for ambushes.",
     "Rogue Ninja Ambusher", ("Ration Bar", 0.35)),
    ("C", "Chunin", 0.7, "The Missing-nin Camp",
     "A low-level missing-nin has built a hideout near the border.",
     "Missing-nin Raider", ("Explosive Tag", 0.30)),
    ("B", "Special Jonin", 0.2, "Smuggler’s Cove",
     "A smuggling ring is moving forbidden scrolls through the coast.",
     "Smuggler Captain", ("Medic Scroll", 0.25)),
    ("B", "Special Jonin", 0.7, "The Poison Mist",
     "A poison-user has contaminated a river village’s water supply.",
     "Poison Master", ("Chakra Pill", 0.30)),
    ("A", "Jonin", 0.2, "The Rogue Jonin",
     "A former Jonin has turned traitor and stolen village secrets.",
     "Rogue Jonin", ("Soldier Pill", 0.25)),
    ("A", "Jonin", 0.8, "The Curse-Mark Experiment",
     "An old Sound lab has woken up. Something is wearing a curse seal.",
     "Cursed Experiment", ("Speed Scroll", 0.15)),
    ("S", "ANBU", 0.3, "Akatsuki Courier",
     "An Akatsuki courier carrying a scroll of S-rank intel has been spotted.",
     "Akatsuki Courier", ("Tsunade's Elixir", 0.15)),
    ("S", "Elite Jonin", 0.5, "The Edo Tensei Remnant",
     "A reanimated warrior has slipped through the lines. End it.",
     "Reanimated Warrior", ("Akimichi Pill", 0.15)),
    ("S", "Sannin-Class", 0.7, "The Legendary Sannin’s Shadow",
     "A shadow of the old Sannin has been sighted — and it won’t talk.",
     "Sannin’s Shade", ("Sage Scroll", 0.12)),
]

# ── Graduation trial (fights at character creation) ─────
GRADUATION_TRIALS = [
    {"name": "Training Dummy",       "hp": 25, "atk": 4},
    {"name": "Iruka’s Shadow Clone", "hp": 40, "atk": 6},
    {"name": "Mizuki — Rogue Instructor", "hp": 55, "atk": 8},
]
