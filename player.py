import random
from character import Character
from item import Item
from data import (
    MAX_HP, LEVEL_HP_BONUS, LEVEL_ATK_BONUS, MIN_DAMAGE, TRAIN_CAP,
    exp_needed, CLAN_POOL, VILLAGES, NINJA_RANKS, RANK_NAMES, STYLES,
    GREEN, YELLOW, CYAN, RED, MAGENTA, RESET, BOLD, DIM, WHITE,
    RARITY_COLORS,
)


class Player(Character):
    """The player's shinobi. Inherits from Character and adds chakra, jutsu and progression."""

    TRAIN_CAP = TRAIN_CAP

    def __init__(self, name: str, clan: str, village: str = "Konoha"):
        super().__init__(name, MAX_HP, 10)

        self._clan    = clan
        self._village = village
        self._str: int = 1
        self._spd: int = 1
        self._end: int = 1

        self._level: int    = 1
        self._exp: int      = 0
        self._kills: int    = 0
        self._gold: int     = 50
        self._training: int = 0
        self._rank: str     = "Genin"

        self.inventory: list = []
        self._style         = None
        self.temp_atk_up    = 0

        self.signature_unlocked = False   # style ultimate (Jonin)
        self.custom_jutsu       = None    # (name, power, cost, desc) — Kage-Level
        self.awakened           = False   # Jonin awakening
        self.awaken_used        = False   # once per battle

        self.story_done: set = set()
        self.apply_bonuses()
        self._chakra: int = self.max_chakra

    # ── setup ────────────────────────────────────────────
    def apply_bonuses(self) -> None:
        s = CLAN_POOL[self._clan]["stats"]
        v = VILLAGES[self._village]["bonus"]
        self._str += s[0] + v[0]
        self._spd += s[1] + v[1]
        self._end += s[2] + v[2]

    # ── properties ───────────────────────────────────────
    @property
    def clan(self) -> str:        return self._clan
    @property
    def village(self) -> str:     return self._village
    @property
    def level(self) -> int:       return self._level
    @property
    def exp(self) -> int:         return self._exp
    @property
    def training(self) -> int:    return self._training

    @property
    def kills(self) -> int:       return self._kills
    @kills.setter
    def kills(self, v: int) -> None:  self._kills = max(0, v)

    @property
    def gold(self) -> int:        return self._gold
    @gold.setter
    def gold(self, v: int) -> None:   self._gold = max(0, v)

    @property
    def rank(self) -> str:        return self._rank
    @rank.setter
    def rank(self, v: str) -> None:   self._rank = v

    @property
    def style(self):              return self._style
    @style.setter
    def style(self, v) -> None:       self._style = v

    @property
    def str_stat(self) -> int:    return self._str
    @str_stat.setter
    def str_stat(self, v: int) -> None:  self._str = v

    @property
    def spd(self) -> int:         return self._spd
    @spd.setter
    def spd(self, v: int) -> None:       self._spd = v

    @property
    def end(self) -> int:         return self._end
    @end.setter
    def end(self, v: int) -> None:       self._end = v

    @property
    def atk(self) -> int:
        return self._attack_power + self._str + self.temp_atk_up

    @property
    def max_chakra(self) -> int:
        return 40 + 4 * self._level + 2 * self._end

    @property
    def chakra(self) -> int:
        return self._chakra
    @chakra.setter
    def chakra(self, v: int) -> None:
        self._chakra = max(0, min(v, self.max_chakra))

    @property
    def dodge_chance(self) -> float:
        return min(0.30, self._spd * 0.008)

    @property
    def jutsu_list(self) -> list:
        return STYLES[self._style]["jutsu"] if self._style else []

    @property
    def signature(self):
        if self._style and self.signature_unlocked:
            return STYLES[self._style]["ult"]
        return None

    def get_style_name(self) -> str:
        return f"{self._style} Release" if self._style else "None"

    # ── chakra ───────────────────────────────────────────
    def restore_chakra(self, amount: int) -> int:
        before = self._chakra
        self.chakra = self._chakra + amount
        return self._chakra - before

    def chakra_bar(self, length: int = 20) -> str:
        return self._bar(self._chakra, self.max_chakra, length, CYAN)

    # ── combat ───────────────────────────────────────────
    def attack(self, target: Character, awakened: bool = False) -> int:
        """Basic attack: weak but restores a little chakra."""
        dmg = max(MIN_DAMAGE, self.atk + random.randint(-2, 3))
        if awakened:
            dmg = dmg * 2
        target.hp -= dmg
        self.restore_chakra(6)
        return dmg

    def cast(self, target: Character, entry: tuple, awakened: bool = False):
        """entry = (name, power, cost, desc). Returns (damage, name) or None if not enough chakra."""
        name, power, cost, _ = entry
        if not awakened and self._chakra < cost:
            return None
        if not awakened:
            self._chakra -= cost
        dmg = int(self.atk * (1 + power / 50)) + random.randint(0, 4)
        if awakened:
            dmg = dmg * 2
        dmg = max(MIN_DAMAGE, dmg)
        target.hp -= dmg
        return dmg, name

    # ── progression ──────────────────────────────────────
    def gain_exp(self, amount: int) -> bool:
        self._exp += amount
        levelled = False
        while self._exp >= exp_needed(self._level):
            self._exp -= exp_needed(self._level)
            levelled   = True
            self.level_up()
        return levelled

    def level_up(self) -> None:
        self._level        += 1
        self._max_hp       += LEVEL_HP_BONUS
        self._hp            = self._max_hp
        self._attack_power += LEVEL_ATK_BONUS
        self._chakra        = self.max_chakra
        print(f"\n  {YELLOW}{BOLD}✦ LEVEL UP!  You are now Level {self._level}!{RESET}")
        print(f"  {GREEN}Max HP +{LEVEL_HP_BONUS}  |  ATK +{LEVEL_ATK_BONUS}  |  HP & chakra restored!{RESET}")

    def add_kill(self, count: int = 1) -> None:
        self._kills += count

    def add_gold(self, amount: int) -> None:
        self._gold += amount

    def spend_gold(self, amount: int) -> bool:
        if self._gold >= amount:
            self._gold -= amount
            return True
        return False

    def train_stat(self, stat: str) -> bool:
        if self._training >= self.TRAIN_CAP:
            return False
        if stat == "str":   self._str += 2
        elif stat == "spd": self._spd += 2
        elif stat == "end": self._end += 2
        else:
            return False
        self._training += 1
        return True

    def add_item(self, item_name: str) -> None:
        try:
            self.inventory.append(Item(item_name))
        except ValueError:
            pass

    def use_item(self, index: int) -> str:
        if index < 0 or index >= len(self.inventory):
            return f"{YELLOW}Invalid item index.{RESET}"
        return self.inventory.pop(index).use(self)

    def refresh_rank(self) -> bool:
        new = NINJA_RANKS[0][0]
        for name, threshold in NINJA_RANKS:
            if self._kills >= threshold:
                new = name
        if new != self._rank:
            self._rank = new
            return True
        return False

    def next_rank_info(self) -> tuple:
        for i, (name, _) in enumerate(NINJA_RANKS):
            if name == self._rank and i + 1 < len(NINJA_RANKS):
                nxt_name, nxt_thresh = NINJA_RANKS[i + 1]
                return nxt_name, max(0, nxt_thresh - self._kills)
        return "MAX RANK", 0

    def rank_index(self) -> int:
        return RANK_NAMES.index(self._rank) if self._rank in RANK_NAMES else 0

    # ── display ──────────────────────────────────────────
    def show_stats(self) -> None:
        info   = CLAN_POOL[self._clan]
        rcolor = RARITY_COLORS[info["rarity"]]
        print(f"  {BOLD}{self._name}{RESET}  |  Clan: {rcolor}{self._clan} ({info['rarity']}){RESET}  |  Village: {CYAN}{self._village}{RESET}")
        print(f"  Rank : {YELLOW}{self._rank}{RESET}  |  Level: {YELLOW}{self._level}{RESET}  |  EXP: {self._exp}/{exp_needed(self._level)}  |  Kills: {self._kills}")
        print(f"  HP   : {self.hp_bar()}")
        print(f"  CHK  : {self.chakra_bar()}")
        print(f"  ATK  : {self.atk}  STR: {self._str}  SPD: {self._spd}  END: {self._end}  |  Gold: {YELLOW}{self._gold}G{RESET}")
        style = self.get_style_name()
        line  = f"  Style: {CYAN}{style}{RESET}"
        if self.awakened:
            line += f"  |  {YELLOW}{BOLD}✦ AWAKENED{RESET}"
        if self.custom_jutsu:
            line += f"  |  Original: {MAGENTA}{self.custom_jutsu[0]}{RESET}"
        print(line)
        if self.inventory:
            print(f"  Bag  : {', '.join(i.name for i in self.inventory)}")
        else:
            print(f"  Bag  : {DIM}(empty){RESET}")

    def __str__(self) -> str:
        return (f"{BOLD}{self._name}{RESET} | Lv.{self._level} {self._rank} "
                f"(HP: {self._hp}/{self._max_hp})")

    def __repr__(self) -> str:
        return (f"Player(name={self._name!r}, clan={self._clan!r}, village={self._village!r}, "
                f"level={self._level}, kills={self._kills})")
