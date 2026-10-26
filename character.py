# ═══════════════════════════════════════════════════════
#  character.py — Abstract base class (OOP: Abstraction,
#                 Encapsulation, Magic Methods)
# ═══════════════════════════════════════════════════════

from abc import ABC, abstractmethod
from data import MIN_DAMAGE, BOLD, RESET, GREEN, YELLOW, RED, CYAN


class Character(ABC):
    """
    Abstract base class for everyone who can fight.
      - Abstraction  : abc.ABC + @abstractmethod
      - Encapsulation: _private attributes with @property accessors
      - Magic Methods: __str__, __repr__
    """

    def __init__(self, name: str, hp: int, attack_power: int):
        self._name: str         = name
        self._hp: int           = hp
        self._max_hp: int       = hp
        self._attack_power: int = attack_power

    # ── properties (encapsulation) ───────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = max(0, min(value, self._max_hp))

    @property
    def max_hp(self) -> int:
        return self._max_hp

    @max_hp.setter
    def max_hp(self, value: int) -> None:
        self._max_hp = max(1, value)

    @property
    def attack_power(self) -> int:
        return self._attack_power

    @attack_power.setter
    def attack_power(self, value: int) -> None:
        self._attack_power = max(1, value)

    # ── abstract methods (must be overridden) ────────────
    @abstractmethod
    def attack(self, target: "Character") -> int:
        """Deal damage to target. Returns damage dealt."""

    @abstractmethod
    def get_style_name(self) -> str:
        """Return the name of this character's fighting style."""

    # ── concrete shared methods ──────────────────────────
    def defend(self, incoming: int, reduction: int) -> int:
        taken = max(MIN_DAMAGE, incoming - reduction)
        self._hp = max(0, self._hp - taken)
        return taken

    def heal(self, amount: int = 9999) -> int:
        before   = self._hp
        self._hp = min(self._max_hp, self._hp + amount)
        return self._hp - before

    def full_heal(self) -> None:
        self._hp = self._max_hp

    def is_alive(self) -> bool:
        return self._hp > 0

    @staticmethod
    def _bar(cur: int, mx: int, length: int, color: str = None) -> str:
        ratio  = cur / mx if mx else 0
        filled = int(ratio * length)
        bar    = "█" * filled + "░" * (length - filled)
        if color is None:
            color = GREEN if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
        return f"{color}[{bar}]{RESET} {cur}/{mx}"

    def hp_bar(self, length: int = 20) -> str:
        return self._bar(self._hp, self._max_hp, length)

    # ── magic methods ────────────────────────────────────
    def __str__(self) -> str:
        return f"{BOLD}{self._name}{RESET} (HP: {self._hp}/{self._max_hp})"

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(name={self._name!r}, "
                f"hp={self._hp}, attack_power={self._attack_power})")
