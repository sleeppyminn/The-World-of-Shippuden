import json
import os
import random
import time

from player import Player
from enemy import Enemy
from data import (
    RESET, RED, GREEN, YELLOW, CYAN, BOLD, DIM, MAGENTA, BLUE, WHITE, COLORS,
    CLAN_POOL, RARITY_COLORS, RARITY_WEIGHTS, VILLAGES,
    NINJA_RANKS, RANK_NAMES,
    STYLES, STYLE_NAMES, CUSTOM_JUTSU_TEMPLATE,
    ITEMS, SHOP_STOCK, SHOP_PRICES, MISSIONS, GRADUATION_TRIALS,
    exp_needed,
)
from anim import (
    ascii_header, battle_header, title_splash, animated_main_menu,
    jutsu_banner, ultimate_flash, style_colored, STYLE_RGB,
)
import story
from story.common import RANK_STATS, boss_stats


# ── tiny UI helpers ──────────────────────────────────────
def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def divider(char: str = "─", width: int = 48) -> None:
    print(DIM + char * width + RESET)


def header(title: str, color: str = None) -> None:
    ascii_header(title, STYLE_RGB.get(color) if color else None)


def pause(msg: str = "[ Press ENTER to continue ]") -> None:
    input(DIM + msg + RESET)


def slow_print(lines: list, delay: float = 0.05) -> None:
    for line in lines:
        for ch in line:
            print(ch, end="", flush=True)
            time.sleep(delay * 0.4)
        print()
        time.sleep(delay)


def flush_stdin() -> None:
    try:
        import termios
        termios.tcflush(0, termios.TCIFLUSH)
    except Exception:
        pass


def get_valid_input(min_val: int, max_val: int) -> int:
    flush_stdin()
    while True:
        try:
            choice = int(input("  > "))
            if min_val <= choice <= max_val:
                return choice
            print(f"  {YELLOW}Enter a number between {min_val} and {max_val}.{RESET}")
        except ValueError:
            print(f"  {RED}Invalid input — please enter a number.{RESET}")


class Game:
    SAVE_FILE = "shippuden_save.json"

    def __init__(self):
        self.player: Player = None

    # ═════════════════════════════════════════════════════
    #  main flow
    # ═════════════════════════════════════════════════════
    def run(self) -> None:
        title_splash()
        while True:
            animated_main_menu()
            choice = get_valid_input(0, 2)
            if choice == 0:
                print(f"\n  {DIM}Believe it. See you next time, shinobi.{RESET}\n")
                break
            if choice == 2:
                if not self._load_game():
                    continue
            else:
                self.player = self._create_character()
                self._intro_story()
            self.game_loop()

            clear()
            print(f"\n  {BOLD}Play again?{RESET}")
            print("  [1] Yes — back to the main menu")
            print("  [0] No  — exit")
            if get_valid_input(0, 1) == 0:
                print(f"\n  {DIM}Believe it. See you next time, shinobi.{RESET}\n")
                break

    def game_loop(self) -> None:
        while True:
            clear()
            header("THE WORLD OF SHIPPUDEN")
            self.player.show_stats()
            nxt, needed = self.player.next_rank_info()
            if nxt != "MAX RANK":
                print(f"  Next rank in {needed} kill(s): {YELLOW}{nxt}{RESET}")
            print()
            self.display_menu()
            kage = self.player.rank == "Kage-Level"
            choice = get_valid_input(0, 9 if kage else 8)

            if   choice == 1: self._mission_board()
            elif choice == 2: self._story_map()
            elif choice == 3: self._train()
            elif choice == 4: self._style_menu()
            elif choice == 5: self._use_item_screen()
            elif choice == 6: self._visit_shop()
            elif choice == 7: self._show_rank_progress()
            elif choice == 8: self._save_game()
            elif choice == 9 and kage: self._forge_original_jutsu()
            elif choice == 0:
                clear()
                return

    def display_menu(self) -> None:
        total = story.total_chapters()
        done  = len(self.player.story_done)
        print("  [1] Mission Board   — quick D to S-rank jobs")
        print(f"  [2] Story Missions  — {done}/{total} chapters cleared")
        print("  [3] Train")
        print("  [4] Style & Jutsu")
        print("  [5] Use Item")
        print("  [6] Shop")
        print("  [7] Rank Progress")
        print("  [8] Save Game")
        if self.player.rank == "Kage-Level":
            print(f"  [9] {YELLOW}Forge Original Jutsu{RESET}")
        print("  [0] Quit")

    # ═════════════════════════════════════════════════════
    #  battle
    # ═════════════════════════════════════════════════════
    def start_battle(self, enemy_name: str, enemy_hp: int, enemy_atk: int,
                     is_story: bool = False, gold_reward: int = 0,
                     kill_reward: int = 1, exp_reward: int = 0,
                     drop_table: tuple = None) -> bool:
        p = self.player
        enemy = Enemy(enemy_name, enemy_hp, enemy_atk, exp_reward=exp_reward, drop_table=drop_table)

        p.chakra       = p.max_chakra
        p.awaken_used  = False
        blocking       = False

        clear()
        header("BATTLE")
        print(f"  {enemy}\n")
        time.sleep(0.4)

        while p.is_alive() and enemy.is_alive():
            clear()
            battle_header()
            print(f"  {RED}{BOLD}{enemy_name}{RESET}\n")
            divider()
            print(f"  YOU   HP : {p.hp_bar()}")
            print(f"        CHK: {p.chakra_bar()}")
            print(f"  ENEMY HP : {enemy.hp_bar()}")
            divider()
            print(f"\n  {BOLD}Your turn:{RESET}")
            print("  [1] Attack          (+6 chakra)")
            print(f"  [2] Jutsu           ({p.get_style_name()})")
            print("  [3] Guard           (reduce damage, +10 chakra)")
            print("  [4] Use Item")
            sig = p.signature
            if sig:
                print(f"  [5] {YELLOW}SIGNATURE: {sig[0]}{RESET}  {DIM}(cost {sig[2]}){RESET}")
            if p.custom_jutsu:
                print(f"  [6] {MAGENTA}ORIGINAL: {p.custom_jutsu[0]}{RESET}  {DIM}(cost {p.custom_jutsu[2]}){RESET}")
            can_awaken = p.awakened and not p.awaken_used
            if can_awaken:
                aw_name = STYLES[p.style]["awaken"][0] if p.style else "Awakening"
                print(f"  [M] {YELLOW}{BOLD}✦ {aw_name}{RESET}  {DIM}(once per battle — costs 10 HP){RESET}")

            awakened_turn = False
            consumed      = False   # did we spend our turn?
            while not consumed:
                action = input("\n  > ").strip().lower()

                if action == "m" and can_awaken and not awakened_turn:
                    awakened_turn  = True
                    p.awaken_used  = True
                    p.hp           = max(1, p.hp - 10)
                    name, desc     = STYLES[p.style]["awaken"]
                    print(f"\n  {YELLOW}{BOLD}✦ {name.upper()} ✦{RESET}")
                    print(f"  {DIM}{desc}{RESET}")
                    print(f"  {RED}-10 HP{RESET}  |  {GREEN}Damage ×2 and free chakra this turn!{RESET}")
                    continue

                if action == "1":
                    dmg  = p.attack(enemy, awakened_turn)
                    tag  = f" {YELLOW}[AWAKENED]{RESET}" if awakened_turn else ""
                    print(f"\n  You strike for {GREEN}{dmg}{RESET} damage!{tag}")
                    consumed = True

                elif action == "2":
                    jutsu = p.jutsu_list
                    if not jutsu:
                        print(f"\n  {YELLOW}You haven't chosen a style yet.{RESET}")
                        continue
                    print(f"\n  {BOLD}{p.get_style_name()} jutsu:{RESET}")
                    for i, (jn, jp, jc, jd) in enumerate(jutsu, 1):
                        ok = awakened_turn or p.chakra >= jc
                        col = "" if ok else DIM
                        print(f"  {col}[{i}] {jn} — dmg ×{1 + jp / 50:.2f}, cost {jc}{RESET}")
                        print(f"  {DIM}      {jd}{RESET}")
                    print("  [0] Cancel")
                    fc = get_valid_input(0, len(jutsu))
                    if fc == 0:
                        continue
                    result = p.cast(enemy, jutsu[fc - 1], awakened_turn)
                    if result is None:
                        print(f"  {YELLOW}Not enough chakra! (need {jutsu[fc - 1][2]}){RESET}")
                        continue
                    dmg, jname = result
                    jutsu_banner(p.style, jname)
                    print(f"  {DIM}{jutsu[fc - 1][3]}{RESET}")
                    print(f"  You deal {style_colored(p.style, str(dmg))} damage!")
                    consumed = True

                elif action == "3":
                    blocking = True
                    p.restore_chakra(10)
                    print(f"\n  {BLUE}You guard and gather your chakra.{RESET}")
                    consumed = True

                elif action == "4":
                    if self._use_item_in_combat():
                        consumed = True

                elif action in ("5", "6") and (sig if action == "5" else p.custom_jutsu):
                    entry  = sig if action == "5" else p.custom_jutsu
                    result = p.cast(enemy, entry, awakened_turn)
                    if result is None:
                        print(f"  {YELLOW}Not enough chakra! (need {entry[2]}){RESET}")
                        continue
                    dmg, jname = result
                    ultimate_flash(p.style, jname)
                    print(f"  {DIM}{entry[3]}{RESET}")
                    print(f"  You unleash {GREEN}{BOLD}{dmg}{RESET} damage!!")
                    consumed = True

                else:
                    print(f"  {DIM}Invalid — try again.{RESET}")

            if not enemy.is_alive():
                break

            # ── enemy turn ──
            if blocking:
                reduction = 5 + p.end // 3
                raw   = enemy.attack_power + random.randint(-3, 3)
                taken = max(1, raw - reduction)
                p.hp -= taken
                print(f"\n  {enemy_name} attacks! {RED}{taken}{RESET} damage (blocked {reduction}).")
            elif random.random() < p.dodge_chance:
                print(f"\n  {CYAN}{enemy_name} attacks — you slip past it! (dodged){RESET}")
            else:
                enemy.attack(p)
            blocking = False
            time.sleep(0.8)

        print()
        p.temp_atk_up = 0
        if p.is_alive():
            print(f"  {GREEN}{BOLD}You defeated {enemy_name}!{RESET}")
            p.full_heal()
            p.chakra = p.max_chakra
            print(f"  {DIM}HP and chakra restored.{RESET}")

            if not is_story:
                p.add_kill(kill_reward)
                p.add_gold(gold_reward)
                print(f"  +{kill_reward} kill(s)  |  +{gold_reward}G  |  +{exp_reward} EXP")
                if exp_reward > 0:
                    p.gain_exp(exp_reward)
            if drop_table:
                dropped = enemy.drop_item()
                if dropped:
                    p.add_item(dropped)
                    print(f"\n  {YELLOW}Item found: {dropped}!{RESET}")
                    print(f"  {DIM}{ITEMS[dropped]['desc']}{RESET}")
            pause()
            return True

        p.hp = 0
        print(f"  {RED}{BOLD}You were defeated…{RESET}")
        pause()
        return False

    def _use_item_in_combat(self) -> bool:
        p = self.player
        if not p.inventory:
            print(f"\n  {YELLOW}Your bag is empty.{RESET}")
            return False
        print(f"\n  {BOLD}Items:{RESET}")
        for i, item in enumerate(p.inventory, 1):
            print(f"  [{i}] {item}")
        print("  [0] Cancel")
        c = get_valid_input(0, len(p.inventory))
        if c == 0:
            return False
        print(f"\n  {p.use_item(c - 1)}")
        return True

    # ═════════════════════════════════════════════════════
    #  mission board
    # ═════════════════════════════════════════════════════
    def _mission_board(self) -> None:
        p = self.player
        while True:
            clear()
            header("MISSION BOARD")
            avail = [m for m in MISSIONS if RANK_NAMES.index(m[1]) <= p.rank_index()]
            for i, (letter, _, _, title, brief, enemy, drop) in enumerate(avail, 1):
                print(f"  [{i}] {YELLOW}[{letter}-Rank]{RESET} {title}")
                print(f"      {DIM}{brief}{RESET}")
            print("\n  [0] Back")
            c = get_valid_input(0, len(avail))
            if c == 0:
                return
            letter, mrank, k, title, brief, enemy, drop = avail[c - 1]
            hp, atk = boss_stats(mrank, k)
            hp, atk = int(hp * 0.45), int(atk * 0.85)   # missions are quicker than bosses
            e_lo = RANK_STATS[mrank][4]
            exp   = int(e_lo * 0.45)
            gold  = exp // 2 + 5
            kills = 1 if letter in ("D", "C") else 2 if letter in ("B", "A") else 3
            clear()
            header(title.upper())
            print(f"  {brief}\n")
            pause("[ ENTER to accept the mission ]")
            self.start_battle(enemy, hp, atk, gold_reward=gold, kill_reward=kills,
                              exp_reward=exp, drop_table=drop)
            if p.refresh_rank():
                self._rank_up_scene()

    # ═════════════════════════════════════════════════════
    #  story missions
    # ═════════════════════════════════════════════════════
    def _home_country(self) -> str:
        return VILLAGES[self.player.village]["country"]

    def _story_map(self) -> None:
        p = self.player
        while True:
            clear()
            header("THE SHINOBI WORLD")
            print("  Every nation has its own story. Choose where to go.\n")
            for i, c in enumerate(story.COUNTRIES, 1):
                chapters = story.CHAPTERS_BY_COUNTRY[c["key"]]
                done = sum(1 for ch in chapters if ch["id"] in p.story_done)
                col  = COLORS.get(c["color"], WHITE)
                home = f"  {YELLOW}★ HOME{RESET}" if c["key"] == self._home_country() else ""
                print(f"  [{i}] {col}{BOLD}{c['name']}{RESET} — {c['village']}  ({done}/{len(chapters)}){home}")
                print(f"      {DIM}{c['blurb']}{RESET}\n")
            print("  [0] Back")
            c = get_valid_input(0, len(story.COUNTRIES))
            if c == 0:
                return
            self._country_chapters(story.COUNTRIES[c - 1])

    def _country_chapters(self, country: dict) -> None:
        p        = self.player
        chapters = story.CHAPTERS_BY_COUNTRY[country["key"]]
        col      = COLORS.get(country["color"], WHITE)
        while True:
            clear()
            header(country["name"].upper())
            print(f"  {col}{country['village']}{RESET} — {DIM}{country['blurb']}{RESET}\n")
            if country["key"] == self._home_country():
                print(f"  {YELLOW}Home soil: +15% EXP on every chapter here.{RESET}\n")
            for i, ch in enumerate(chapters, 1):
                flag = self._chapter_flag(chapters, i - 1)
                lvl  = ch["rec_level"]
                lcol = YELLOW if p.level < lvl - 2 else DIM
                print(f"  [{i}] {ch['title']}  {flag}  {lcol}Rec. Lv {lvl}{RESET}")
            print("\n  [0] Back")
            c = get_valid_input(0, len(chapters))
            if c == 0:
                return
            ch = chapters[c - 1]
            reason = self._chapter_locked_reason(chapters, c - 1)
            if reason:
                print(f"\n  {YELLOW}Locked. {reason}{RESET}")
                pause()
                continue
            first_time = ch["id"] not in p.story_done
            self._play_chapter(ch, country, first_time)

    def _chapter_locked_reason(self, chapters: list, idx: int):
        p, ch = self.player, chapters[idx]
        if RANK_NAMES.index(ch["rank"]) > p.rank_index():
            return f"Reach rank {ch['rank']} first."
        if idx > 0 and chapters[idx - 1]["id"] not in p.story_done:
            return "Clear the previous chapter first."
        return None

    def _chapter_flag(self, chapters: list, idx: int) -> str:
        ch = chapters[idx]
        if ch["id"] in self.player.story_done:
            return f"{DIM}[done]{RESET}"
        reason = self._chapter_locked_reason(chapters, idx)
        if reason is None:
            return f"{GREEN}[NEW]{RESET}"
        if reason.startswith("Reach"):
            return f"{DIM}[locked — need rank: {ch['rank']}]{RESET}"
        return f"{DIM}[locked — clear previous chapter]{RESET}"

    def _play_chapter(self, ch: dict, country: dict, first_time: bool) -> None:
        p = self.player
        bonus = 1.15 if country["key"] == self._home_country() else 1.0
        exp   = int(ch["exp"] * bonus)

        if ch.get("stages"):
            won = self._play_multi_stage(ch)
        else:
            won = self._play_single_boss(ch)

        if not won:
            p.full_heal()
            print(f"\n  {YELLOW}You fall… but the story isn't over yet.{RESET}")
            print(f"  {DIM}HP restored. Recover and try again.{RESET}")
            pause()
            return

        clear()
        divider("*")
        print(f"  {GREEN}{BOLD}CHAPTER COMPLETE — {ch['title']}{RESET}")
        divider("*")
        for line in ch["victory_lines"]:
            print("  " + line)
        print()

        if first_time:
            p.story_done.add(ch["id"])
            p.add_kill(ch["kills"])
            p.add_gold(ch["gold"])
            print(f"  {GREEN}+{exp} EXP  |  +{ch['gold']}G  |  +{ch['kills']} kills{RESET}")
            p.gain_exp(exp)
            if ch.get("reward"):
                p.add_item(ch["reward"])
                print(f"  {YELLOW}Reward: {ch['reward']}!{RESET}")
        else:
            print(f"  {DIM}(Replay — no extra rewards.){RESET}")
        pause()

        if p.refresh_rank():
            self._rank_up_scene()
        self._try_awaken()

    def _play_single_boss(self, ch: dict) -> bool:
        clear()
        header(ch["title"])
        for line in ch["lines"]:
            print("  " + line)
        print()
        if ch.get("choice"):
            self._play_choice(ch["choice"])
        pause("[ Prepare yourself — ENTER to fight ]")
        return self.start_battle(ch["boss"], ch["boss_hp"], ch["boss_atk"], is_story=True)

    def _play_multi_stage(self, ch: dict) -> bool:
        clear()
        header(ch["title"])
        for line in ch["lines"]:
            print("  " + line)
        print(f"\n  {DIM}This chapter has {len(ch['stages'])} stages.{RESET}\n")
        pause("[ ENTER to begin ]")

        for i, st in enumerate(ch["stages"], 1):
            choice_done = False
            while True:
                clear()
                print(f"\n  {BOLD}{YELLOW}[ {st['label']} ]{RESET}\n")
                for line in st["lines"]:
                    print("  " + line)
                print()
                if st.get("choice") and not choice_done:
                    self._play_choice(st["choice"])
                    choice_done = True
                pause("[ Prepare yourself — ENTER to fight ]")
                if self.start_battle(st["boss"], st["boss_hp"], st["boss_atk"], is_story=True):
                    clear()
                    divider("*")
                    print(f"  {GREEN}{BOLD}STAGE {i} CLEAR{RESET}")
                    divider("*")
                    for line in st["victory_lines"]:
                        print("  " + line)
                    print()
                    pause()
                    break
                self.player.full_heal()
                print(f"\n  {YELLOW}You fall… HP restored. Retrying this stage.{RESET}")
                pause()
        return True

    def _play_choice(self, choice: dict) -> None:
        p = self.player
        print(f"  {BOLD}{choice['prompt']}{RESET}")
        for i, (text, _, _) in enumerate(choice["options"], 1):
            print(f"  [{i}] {text}")
        c = get_valid_input(1, len(choice["options"]))
        _, result, reward = choice["options"][c - 1]
        print(f"\n  {CYAN}{result}{RESET}\n")
        if reward.get("str"):  p.str_stat += reward["str"]
        if reward.get("spd"):  p.spd      += reward["spd"]
        if reward.get("end"):  p.end      += reward["end"]
        if reward.get("gold"): p.add_gold(reward["gold"])
        if reward.get("item"): p.add_item(reward["item"])
        if reward.get("exp"):  p.gain_exp(reward["exp"])
        time.sleep(0.6)

    # ═════════════════════════════════════════════════════
    #  rank-up, awakening, custom jutsu
    # ═════════════════════════════════════════════════════
    def _rank_up_scene(self) -> None:
        clear()
        header("PROMOTION")
        print(f"  {YELLOW}{BOLD}You have been promoted to {self.player.rank}!{RESET}")
        print(f"  {DIM}The village will remember your name.{RESET}\n")
        pause()

    def _try_awaken(self) -> None:
        p = self.player
        if p.awakened or not p.style or p.rank_index() < RANK_NAMES.index("Jonin"):
            return
        name, desc = STYLES[p.style]["awaken"]
        clear()
        header("SOMETHING STIRS WITHIN YOU")
        slow_print([
            "  Years of battle have changed you.",
            "  Your chakra is climbing beyond anything you’ve felt before.",
            "",
            f"  {name}.",
            "",
        ])
        pause("[ ENTER to awaken ]")
        p.awakened = True
        p.signature_unlocked = True
        clear()
        divider("═")
        print(f"\n  {YELLOW}{BOLD}✦ {name.upper()} AWAKENED ✦{RESET}\n")
        divider("═")
        slow_print([
            f"  {desc}", "",
            "  Press [M] in battle once per fight:",
            "  Damage ×2 and free chakra for one turn — costs 10 HP.", "",
            f"  {YELLOW}Signature jutsu unlocked: {STYLES[p.style]['ult'][0]}{RESET}",
            "",
        ])
        pause()

    def _forge_original_jutsu(self) -> None:
        p = self.player
        clear()
        header("FORGE ORIGINAL JUTSU")
        if p.custom_jutsu:
            print(f"  Your original jutsu: {MAGENTA}{BOLD}{p.custom_jutsu[0]}{RESET}")
            print(f"  {DIM}{p.custom_jutsu[3]}{RESET}\n")
            print("  [1] Rename it")
            print("  [0] Back")
            if get_valid_input(0, 1) == 0:
                return
        else:
            slow_print([
                "  At Kage-Level, a shinobi stops copying techniques and invents their own.",
                "  Name the jutsu that will be yours alone.", "",
            ])
        while True:
            name = input("  Jutsu name: ").strip()
            if name:
                break
            print("  Name cannot be empty.")
        desc = input("  One-line description: ").strip() or "A technique born from your own battles."
        p.custom_jutsu = (name, CUSTOM_JUTSU_TEMPLATE["power"], CUSTOM_JUTSU_TEMPLATE["cost"], desc)
        print(f"\n  {GREEN}{BOLD}{name}{RESET} is now in your arsenal!")
        print(f"  {DIM}Battle slot [6] — damage ×{1 + CUSTOM_JUTSU_TEMPLATE['power'] / 50:.2f}, cost {CUSTOM_JUTSU_TEMPLATE['cost']}.{RESET}")
        pause()

    # ═════════════════════════════════════════════════════
    #  training
    # ═════════════════════════════════════════════════════
    def _train(self) -> None:
        p = self.player
        clear()
        header("TRAINING GROUNDS")
        if p.training >= Player.TRAIN_CAP:
            print(f"  {YELLOW}You've pushed your body to its limit for now.{RESET}")
            print(f"  {DIM}(Training cap of {Player.TRAIN_CAP} sessions reached){RESET}")
            pause()
            return

        print(f"  Sessions remaining: {Player.TRAIN_CAP - p.training}/{Player.TRAIN_CAP}\n")
        print("  Pass the mini-game to gain the stat. Fail — gain nothing.\n")
        print("  [1] Strength   — Stone Breaker     (STR +2)")
        print("  [2] Speed      — Lightning Dash    (SPD +2)")
        print("  [3] Endurance  — Chakra Control    (END +2)")
        print("  [0] Back\n")
        c = get_valid_input(0, 3)
        if c == 0:
            return

        stat  = {1: "str", 2: "spd", 3: "end"}[c]
        label = {1: "STR", 2: "SPD", 3: "END"}[c]
        passed = {1: self._minigame_strength, 2: self._minigame_speed, 3: self._minigame_endurance}[c]()

        if passed:
            p.train_stat(stat)
            new_val = getattr(p, "str_stat" if stat == "str" else stat)
            print(f"\n  {GREEN}{BOLD}Training successful! {label} increased to {new_val}!{RESET}")
        else:
            p._training += 1
            print(f"\n  {RED}You pushed hard but couldn't break through this time.{RESET}")
            print(f"  {DIM}Session used. Try a different approach next time.{RESET}")
        pause()

    def _minigame_strength(self) -> bool:
        clear()
        header("STONE BREAKER — STRENGTH TRIAL")
        slow_print([
            "  A massive boulder sits before you.",
            "  Your sensei points at the cracks.",
            "  'Strike them in order. Muscle memory is everything.'", "",
        ])
        pause("[ ENTER to begin ]")
        seq    = random.choices(["L", "R", "U", "D"], k=5)
        labels = {"L": "Left", "R": "Right", "U": "Up", "D": "Down"}
        print(f"\n  {BOLD}Memorize the strike sequence:{RESET}")
        print(f"  {CYAN}{' → '.join(labels[s] for s in seq)}{RESET}\n")
        time.sleep(2.5)
        clear()
        header("STONE BREAKER — STRIKE!")
        print(f"  Enter: {BOLD}L{RESET}=Left  {BOLD}R{RESET}=Right  {BOLD}U{RESET}=Up  {BOLD}D{RESET}=Down\n")
        correct = 0
        for i, expected in enumerate(seq, 1):
            while True:
                ans = input(f"  Strike {i}/5: ").strip().upper()
                if ans in labels:
                    break
                print(f"  {RED}Enter L, R, U, or D.{RESET}")
            if ans == expected:
                print(f"  {GREEN}✔  Crack!{RESET}")
                correct += 1
            else:
                print(f"  {RED}✘  The stone holds. (Was: {labels[expected]}){RESET}")
        passed = correct >= 4
        print(f"\n  {GREEN if passed else YELLOW}{'The boulder shatters!' if passed else 'The boulder barely moved.'} ({correct}/5, need 4+){RESET}")
        time.sleep(1)
        return passed

    def _minigame_speed(self) -> bool:
        clear()
        header("LIGHTNING DASH — SPEED TRIAL")
        slow_print([
            "  Your sensei stands at the end of the track.",
            "  'When the signal comes — move. Don't think. Move.'", "",
        ])
        pause("[ ENTER to get ready ]")
        for count in ["3", "2", "1", f"{GREEN}{BOLD}GO!{RESET}"]:
            clear()
            header("LIGHTNING DASH — SPEED TRIAL")
            print(f"\n  {BOLD}{count}{RESET}\n")
            time.sleep(0.9 if "GO" not in count else 0.1)
        target = random.choice(["RENAN", "JULIANNE", "BENEDICT", "PATRICK", "SIXSEVEN",
                                "RASENGAN", "CHAKRA", "KUNAI", "SHURIKEN", "SHARINGAN"])
        clear()
        header("LIGHTNING DASH — GO!")
        print(f"\n  Type this word as fast as you can:\n")
        print(f"  {YELLOW}{BOLD}  {target}  {RESET}\n")
        start   = time.time()
        ans     = input("  > ").strip().upper()
        elapsed = time.time() - start
        print()
        if ans == target and elapsed <= 3.5:
            print(f"  {GREEN}{BOLD}Like lightning! ({elapsed:.2f}s — target ≤3.5s){RESET}")
            return True
        if ans == target:
            print(f"  {YELLOW}Correct word, but too slow ({elapsed:.2f}s — need ≤3.5s).{RESET}")
        else:
            print(f"  {RED}Wrong word typed. Focus!{RESET}")
        return False

    def _minigame_endurance(self) -> bool:
        clear()
        header("CHAKRA CONTROL — ENDURANCE TRIAL")
        slow_print([
            "  Your sensei sits across from you, eyes closed.",
            "  'Chakra control is rhythm. Match mine.'", "",
        ])
        pause("[ ENTER to begin ]")
        rounds, interval, tolerance = 5, 2.0, 0.6
        passed_rounds = 0
        print(f"\n  Press ENTER every {interval} seconds to match the rhythm.")
        print(f"  {DIM}({rounds} pulses — hit within ±{tolerance}s each time){RESET}\n")
        pause("[ ENTER to start the first pulse ]")
        for i in range(1, rounds + 1):
            print(f"  Pulse {i}/{rounds}… ", end="", flush=True)
            start = time.time()
            input("")
            elapsed = time.time() - start
            if abs(elapsed - interval) <= tolerance:
                print(f"  {GREEN}✔  Perfect pulse ({elapsed:.2f}s){RESET}")
                passed_rounds += 1
            else:
                way = "too fast" if elapsed < interval else "too slow"
                print(f"  {RED}✘  Off rhythm ({elapsed:.2f}s — {way}){RESET}")
            time.sleep(0.3)
        passed = passed_rounds >= 4
        print(f"\n  {GREEN if passed else YELLOW}{'Perfect control!' if passed else 'Your chakra wavered.'} ({passed_rounds}/{rounds}, need 4+){RESET}")
        time.sleep(1)
        return passed

    # ═════════════════════════════════════════════════════
    #  style, items, shop, rank
    # ═════════════════════════════════════════════════════
    def _style_menu(self) -> None:
        p = self.player
        clear()
        header("STYLE & JUTSU")
        print(f"  Current style: {CYAN}{BOLD}{p.get_style_name()}{RESET}\n")
        for jn, jp, jc, jd in p.jutsu_list:
            print(f"  • {jn} — dmg ×{1 + jp / 50:.2f}, cost {jc}")
            print(f"    {DIM}{jd}{RESET}")
        if p.signature:
            print(f"\n  {YELLOW}★ Signature: {p.signature[0]} — dmg ×{1 + p.signature[1] / 50:.2f}, cost {p.signature[2]}{RESET}")
        if p.custom_jutsu:
            print(f"  {MAGENTA}★ Original : {p.custom_jutsu[0]} — dmg ×{1 + p.custom_jutsu[1] / 50:.2f}, cost {p.custom_jutsu[2]}{RESET}")
        print("\n  [1] Switch style")
        print("  [0] Back")
        if get_valid_input(0, 1) == 1:
            self._choose_style()

    def _choose_style(self) -> None:
        p = self.player
        clear()
        header("CHOOSE YOUR CHAKRA NATURE")
        for i, name in enumerate(STYLE_NAMES, 1):
            first = STYLES[name]["jutsu"][0][0]
            print(f"  [{i}] {style_colored(name, name)}  {DIM}— opens with {first}{RESET}")
        c = get_valid_input(1, len(STYLE_NAMES))
        p.style = STYLE_NAMES[c - 1]
        print(f"\n  You now follow the path of {style_colored(p.style, p.get_style_name())}.")
        pause()

    def _use_item_screen(self) -> None:
        p = self.player
        clear()
        header("YOUR BAG")
        if not p.inventory:
            print(f"  {DIM}(empty){RESET}")
            pause()
            return
        for i, item in enumerate(p.inventory, 1):
            print(f"  [{i}] {item}")
        print("  [0] Back")
        c = get_valid_input(0, len(p.inventory))
        if c:
            print(f"\n  {p.use_item(c - 1)}")
            pause()

    def _visit_shop(self) -> None:
        p = self.player
        while True:
            clear()
            header("ICHIRAKU & SUPPLY SHOP")
            print(f"  Gold: {YELLOW}{p.gold}G{RESET}\n")
            for i, name in enumerate(SHOP_STOCK, 1):
                print(f"  [{i}] {name:<16} {YELLOW}{SHOP_PRICES[name]:>3}G{RESET}  {DIM}{ITEMS[name]['desc']}{RESET}")
            print("  [0] Leave")
            c = get_valid_input(0, len(SHOP_STOCK))
            if c == 0:
                return
            name = SHOP_STOCK[c - 1]
            if p.spend_gold(SHOP_PRICES[name]):
                p.add_item(name)
                print(f"\n  {GREEN}Bought {name}!{RESET}")
            else:
                print(f"\n  {RED}Not enough gold.{RESET}")
            pause()

    def _show_rank_progress(self) -> None:
        p = self.player
        clear()
        header("RANK PROGRESS")
        for name, threshold in NINJA_RANKS:
            marker = f"{YELLOW}◄ you are here{RESET}" if name == p.rank else ""
            col = GREEN if p.kills >= threshold else DIM
            print(f"  {col}{name:<15} {threshold:>4} kills{RESET}  {marker}")
        print(f"\n  Total kills: {p.kills}")
        nxt, need = p.next_rank_info()
        if nxt != "MAX RANK":
            print(f"  {need} more to reach {YELLOW}{nxt}{RESET}.")
        pause()

    # ═════════════════════════════════════════════════════
    #  save / load
    # ═════════════════════════════════════════════════════
    def _save_game(self) -> None:
        p = self.player
        data = {
            "name": p.name, "clan": p.clan, "village": p.village,
            "level": p.level, "exp": p.exp, "kills": p.kills, "gold": p.gold,
            "rank": p.rank, "hp": p.hp, "max_hp": p.max_hp,
            "str": p.str_stat, "spd": p.spd, "end": p.end,
            "atk_base": p.attack_power, "training": p.training,
            "style": p.style, "awakened": p.awakened,
            "signature_unlocked": p.signature_unlocked,
            "custom_jutsu": list(p.custom_jutsu) if p.custom_jutsu else None,
            "story_done": sorted(p.story_done),
            "inventory": [i.name for i in p.inventory],
        }
        try:
            with open(self.SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n  {GREEN}✦ Game saved to {self.SAVE_FILE}{RESET}")
        except OSError as e:
            print(f"\n  {RED}Save failed: {e}{RESET}")
        pause()

    def _load_game(self) -> bool:
        try:
            with open(self.SAVE_FILE, encoding="utf-8") as f:
                d = json.load(f)
        except FileNotFoundError:
            print(f"\n  {YELLOW}No save file found ({self.SAVE_FILE}).{RESET}")
            pause()
            return False
        except (OSError, ValueError) as e:
            print(f"\n  {RED}Load failed: {e}{RESET}")
            pause()
            return False

        p = Player(d["name"], d["clan"], d.get("village", "Konoha"))
        p._level        = d.get("level", 1)
        p._exp          = d.get("exp", 0)
        p._kills        = d.get("kills", 0)
        p._gold         = d.get("gold", 50)
        p._rank         = d.get("rank", "Genin")
        p._max_hp       = d.get("max_hp", p.max_hp)
        p._hp           = d.get("hp", p.max_hp)
        p._str          = d.get("str", p.str_stat)
        p._spd          = d.get("spd", p.spd)
        p._end          = d.get("end", p.end)
        p._attack_power = d.get("atk_base", p.attack_power)
        p._training     = d.get("training", 0)
        p.style         = d.get("style")
        p.awakened      = d.get("awakened", False)
        p.signature_unlocked = d.get("signature_unlocked", False)
        cj = d.get("custom_jutsu")
        p.custom_jutsu  = tuple(cj) if cj else None
        p.story_done    = set(d.get("story_done", []))
        p.chakra        = p.max_chakra
        for name in d.get("inventory", []):
            p.add_item(name)

        self.player = p
        clear()
        print(f"\n  {GREEN}✦ Save loaded — welcome back, {p.name}.{RESET}\n")
        p.show_stats()
        pause()
        return True

    # ═════════════════════════════════════════════════════
    #  character creation
    # ═════════════════════════════════════════════════════
    def _create_character(self) -> Player:
        clear()
        header("CHARACTER CREATION")
        while True:
            name = input("  Enter your name: ").strip()
            if name:
                break
            print("  Name cannot be empty.")

        print(f"\n  {BOLD}Choose your hidden village:{RESET}\n")
        vnames = list(VILLAGES.keys())
        for i, v in enumerate(vnames, 1):
            b = VILLAGES[v]["bonus"]
            print(f"  [{i}] {CYAN}{v}{RESET} — {VILLAGES[v]['desc']}  {DIM}(STR +{b[0]} SPD +{b[1]} END +{b[2]}){RESET}")
        village = vnames[get_valid_input(1, len(vnames)) - 1]
        print(f"\n  Village chosen: {CYAN}{village}{RESET}")
        pause("  [ ENTER to reveal your clan ]")

        clan = self._clan_roll_scene()
        self.player = Player(name, clan, village)
        self._choose_style()
        self._graduation_trial()

        print(f"\n  {GREEN}Character created!{RESET}")
        self.player.show_stats()
        pause()
        return self.player

    def _clan_roll_scene(self) -> str:
        clear()
        header("CLAN AWAKENING")
        names = list(CLAN_POOL.keys())
        for _ in range(18):
            print(f"\r  Rolling…  {random.choice(names):12}", end="", flush=True)
            time.sleep(0.08)
        pool = []
        for n, d in CLAN_POOL.items():
            pool.extend([n] * RARITY_WEIGHTS[d["rarity"]])
        chosen = random.choice(pool)
        info   = CLAN_POOL[chosen]
        rcolor = RARITY_COLORS[info["rarity"]]
        print(f"\r  ✦  Clan: {rcolor}{BOLD}{chosen:12}{RESET}  ({info['rarity']})   ")
        print(f"  Bonus  : STR +{info['stats'][0]}  SPD +{info['stats'][1]}  END +{info['stats'][2]}\n")
        pause()
        return chosen

    def _graduation_trial(self) -> None:
        clear()
        header("ACADEMY GRADUATION TRIAL")
        slow_print([
            "  Before you earn a forehead protector, three tests stand in your way.",
            "  Pass them all, and you’ll be a Genin of your village.", "",
        ])
        pause("[ ENTER to begin the trial ]")
        for t in GRADUATION_TRIALS:
            while not self.start_battle(t["name"], t["hp"], t["atk"], is_story=True):
                self.player.full_heal()
                print(f"  {YELLOW}The proctor lets you retry.{RESET}")
                pause()
        clear()
        print(f"\n  {GREEN}{BOLD}You pass! The headband is yours.{RESET}\n")
        pause()

    def _intro_story(self) -> None:
        p = self.player
        clear()
        header("YOUR STORY BEGINS")
        slow_print([
            f"  Your name is {p.name}, of the {p.clan} clan.",
            f"  You wear the headband of {p.village}.",
            "  The Akatsuki are on the move, and the five great nations are restless.",
            "  Every country has its own trouble. Every village has its own scars.",
            "  Take missions. Earn rank. Walk through every land.",
            "  And when the world needs shinobi — be ready.", "",
        ])
        pause()
