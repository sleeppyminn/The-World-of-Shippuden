import random
from character import Character
from data import MIN_DAMAGE, RED, RESET, BOLD


class Enemy(Character):
    """An opponent. Polymorphism: attack() behaves differently from Player.attack()."""

    def __init__(self, name: str, hp: int, attack_power: int,
                 enemy_type: str = "Shinobi", exp_reward: int = 30,
                 drop_table: tuple = None):
        super().__init__(name, hp, attack_power)
        self._enemy_type: str = enemy_type
        self._exp_reward: int = exp_reward
        self._drop_table      = drop_table
        self.last_crit: bool  = False

    @property
    def enemy_type(self) -> str:
        return self._enemy_type

    @property
    def exp_reward(self) -> int:
        return self._exp_reward

    def attack(self, target: Character) -> int:
        """Deal damage. The battle screen animates it; check last_crit for crits."""
        base    = self._attack_power + random.randint(-3, 3)
        is_crit = random.random() < 0.12
        damage  = max(MIN_DAMAGE, base * 2 if is_crit else base)
        target.hp -= damage
        self.last_crit = is_crit
        return damage

    def get_style_name(self) -> str:
        return self._enemy_type

    def drop_item(self):
        if self._drop_table is None:
            return None
        item_name, chance = self._drop_table
        return item_name if random.random() < chance else None

    def __str__(self) -> str:
        return (f"{RED}{BOLD}{self._name}{RESET} [{self._enemy_type}] "
                f"(HP: {self._hp}/{self._max_hp})")

    def __repr__(self) -> str:
        return (f"Enemy(name={self._name!r}, hp={self._hp}, "
                f"attack_power={self._attack_power}, type={self._enemy_type!r})")
