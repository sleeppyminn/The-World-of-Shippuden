import json
import random
import textwrap
import time

from player import Player
from enemy import Enemy
from data import (
    RESET, RED, GREEN, YELLOW, CYAN, BOLD, DIM, MAGENTA, BLUE,
    CLAN_POOL, RARITY_WEIGHTS, VILLAGES,
    NINJA_RANKS, RANK_NAMES,
    STYLES, STYLE_NAMES, CUSTOM_JUTSU_TEMPLATE,
    ITEMS, SHOP_STOCK, SHOP_PRICES, MISSIONS, GRADUATION_TRIALS,
)
import anim
import audio
from anim import (
    FAST, GOLD, ORANGE, SKY, LEAF, CRIMSON, VIOLET, PAPER,
    COLOR_RGB, RARITY_RGB, STYLE_RGB,
    rgb, mix, fit, spread, center, pw, mpad, say, show, panel, opt, menu_panel,
    bar, ascii_header, story_panel, banner, victory_banner, defeat_banner,
    style_colored, flush_stdin, countdown_bar, title_splash, animated_main_menu,
    clan_reveal, BattleScreen, big_text,
)
import story
from story.common import RANK_STATS, boss_stats


# ── tiny UI helpers ──────────────────────────────────────
def clear() -> None:
    anim.clear()


def header(title: str, color=None) -> None:
    ascii_header(title, color if isinstance(color, tuple) else None)


def pause(msg: str = "ENTER to continue") -> None:
    flush_stdin()
    input(mpad() + f"{DIM}▸ {msg}{RESET} ")
    audio.sfx("ui_move")


def get_valid_input(min_val: int, max_val: int, extra=()):
    """Ask for a number in [min_val, max_val]. `extra` = single letters that are also accepted."""
    flush_stdin()
    pre = mpad()
    while True:
        raw = input(f"{pre}{rgb(*GOLD)}{BOLD}»{RESET} ").strip().lower()
        if raw in extra:
            audio.sfx("ui_select")
            return raw
        try:
            choice = int(raw)
        except ValueError:
            audio.sfx("ui_error")
            say("Invalid input — please enter a number.", (240, 90, 80))
            continue
        if min_val <= choice <= max_val:
            audio.sfx("ui_back" if choice == 0 else "ui_select")
            return choice
        audio.sfx("ui_error")
        say(f"Enter a number between {min_val} and {max_val}.", (250, 205, 80))


def ask_text(prompt: str) -> str:
    flush_stdin()
    return input(mpad() + f"{rgb(*GOLD)}{prompt}{RESET} ").strip()


def short_title(title: str) -> str:
    return title.split("—", 1)[-1].strip() if title.startswith("CHAPTER") and "—" in title else title


class Game:
    SAVE_FILE = "shippuden_save.json"

    def __init__(self):
        self.player: Player = None

    # ═════════════════════════════════════════════════════
    #  main flow
    # ═════════════════════════════════════════════════════
    def run(self) -> None:
        audio.init()
        audio.music("title")
        title_splash()
        while True:
            audio.music("title")
            animated_main_menu()
            choice = get_valid_input(0, 3)
            if choice == 0:
                say("Believe it. See you next time, shinobi.", (170, 170, 185))
                break
            if choice == 3:
                self._sound_menu()
                continue
            if choice == 2:
                if not self._load_game():
                    continue
            else:
                self.player = self._create_character()
                self._intro_story()
            self.game_loop()

            clear()
            menu_panel("PLAY AGAIN?", [(1, "Yes", "back to the main menu")], ORANGE, SKY, back="No — exit")
            if get_valid_input(0, 1) == 0:
                say("Believe it. See you next time, shinobi.", (170, 170, 185))
                break

    def game_loop(self) -> None:
        while True:
            audio.music("village")
            clear()
            header("THE WORLD OF SHIPPUDEN")
            self.player.show_stats()
            nxt, needed = self.player.next_rank_info()
            if nxt != "MAX RANK":
                say(f"{DIM}Next rank in {needed} kill(s): {RESET}{YELLOW}{nxt}{RESET}")
            self.display_menu()
            kage = self.player.rank == "Kage-Level"
            choice = get_valid_input(0, 9 if kage else 8, extra=("s",))

            if   choice == 1: self._mission_board()
            elif choice == 2: self._story_map()
            elif choice == 3: self._train()
            elif choice == 4: self._style_menu()
            elif choice == 5: self._use_item_screen()
            elif choice == 6: self._visit_shop()
            elif choice == 7: self._show_rank_progress()
            elif choice == 8: self._save_game()
            elif choice == "s": self._sound_menu()
            elif choice == 9 and kage: self._forge_original_jutsu()
            elif choice == 0:
                clear()
                return

    @staticmethod
    def _mi(n, label, desc, half, hot=False) -> str:
        col = f"{rgb(*GOLD)}{BOLD}[{n}]{RESET}"
        lab = f"{YELLOW}{BOLD}{label}{RESET}" if hot else f"{BOLD}{label}{RESET}"
        return fit(f"{col} {lab}  {DIM}{desc}{RESET}", half)

    def display_menu(self) -> None:
        total = story.total_chapters()
        done = len(self.player.story_done)
        half = (pw() - 4) // 2
        mi = lambda *a, **k: self._mi(*a, half=half, **k)
        left = [mi(1, "Mission Board", "D–S rank jobs"),
                mi(2, "Story Missions", f"{done}/{total} cleared"),
                mi(3, "Train", "STR · SPD · END"),
                mi(4, "Style & Jutsu", "chakra nature")]
        right = [mi(5, "Use Item", "your bag"),
                 mi(6, "Shop", "Ichiraku & gear"),
                 mi(7, "Rank Progress", "promotions"),
                 mi(8, "Save Game", ""),
                self._mi("S", "Sound", "music & effects", half)]
        if self.player.rank == "Kage-Level":
            left.append(mi(9, "Forge Jutsu", "your own", hot=True))
        right.append(mi(0, "Quit", ""))
        show(panel(columns_rows(left, right), "MENU", ORANGE, SKY))

    # ═════════════════════════════════════════════════════
    #  battle
    # ═════════════════════════════════════════════════════
    def _battle_menu(self, p, awakened_turn: bool) -> list:
        inner = pw() - 4
        half = inner // 2

        def b(n, label, note=""):
            return f"{rgb(*GOLD)}{BOLD}[{n}]{RESET} {BOLD}{label}{RESET}" + (f" {DIM}{note}{RESET}" if note else "")

        rows = [fit(b(1, "Attack", "+6 chakra"), half) + b(2, "Jutsu", p.get_style_name()),
                fit(b(3, "Guard", "+10 chakra"), half) + b(4, "Use Item")]
        sig = p.signature
        if sig:
            rows.append(f"{rgb(*GOLD)}{BOLD}[5]{RESET} {YELLOW}{BOLD}SIGNATURE{RESET} {sig[0]}  {DIM}cost {sig[2]}{RESET}")
        if p.custom_jutsu:
            rows.append(f"{rgb(*GOLD)}{BOLD}[6]{RESET} {MAGENTA}{BOLD}ORIGINAL{RESET} {p.custom_jutsu[0]}  {DIM}cost {p.custom_jutsu[2]}{RESET}")
        if p.awakened and not p.awaken_used and not awakened_turn:
            aw = STYLES[p.style]["awaken"][0] if p.style else "Awakening"
            rows.append(f"{rgb(*GOLD)}{BOLD}[M]{RESET} {YELLOW}{BOLD}✦ {aw}{RESET}  {DIM}once per battle · costs 10 HP{RESET}")
        return rows

    def start_battle(self, enemy_name: str, enemy_hp: int, enemy_atk: int,
                     is_story: bool = False, gold_reward: int = 0,
                     kill_reward: int = 1, exp_reward: int = 0,
                     drop_table: tuple = None) -> bool:
        p = self.player
        enemy = Enemy(enemy_name, enemy_hp, enemy_atk, exp_reward=exp_reward, drop_table=drop_table)

        p.chakra       = p.max_chakra
        p.awaken_used  = False
        blocking       = False

        before = audio.current()
        audio.music("boss" if is_story else "battle")
        clear()
        scr = BattleScreen(p, enemy)
        scr.intro(enemy_name)
        turn = 0

        while p.is_alive() and enemy.is_alive():
            turn += 1
            scr.turn = turn
            awakened_turn = False
            consumed      = False
            scr.hint      = ""

            while not consumed:
                title = "YOUR TURN" + ("  ·  ✦ AWAKENED ✦" if awakened_turn else "")
                scr.set_menu(title, self._battle_menu(p, awakened_turn), scr.hint)
                action = scr.ask()
                scr.hint = ""
                sig = p.signature

                if action == "m" and p.awakened and not p.awaken_used and not awakened_turn:
                    awakened_turn = True
                    p.awaken_used = True
                    p.hp          = max(1, p.hp - 10)
                    name, desc    = STYLES[p.style]["awaken"]
                    scr.awaken(name, desc)
                    continue

                if action == "1":
                    dmg = p.attack(enemy, awakened_turn)
                    scr.player_attack(dmg, awakened=awakened_turn)
                    consumed = True

                elif action == "2":
                    jutsu = p.jutsu_list
                    if not jutsu:
                        scr.hint = "You haven't chosen a style yet."
                        continue
                    lines = []
                    for i, (jn, jp, jc, jd) in enumerate(jutsu, 1):
                        ok  = awakened_turn or p.chakra >= jc
                        num = f"{rgb(*GOLD)}{BOLD}[{i}]{RESET}"
                        lab = jn if ok else f"{DIM}{jn}{RESET}"
                        lines.append(spread(f"{num} {lab}", f"{DIM}×{1 + jp / 50:.2f}  {jc} CHK{RESET}", pw() - 4))
                    lines.append(f"{rgb(*GOLD)}{BOLD}[0]{RESET} Cancel")
                    scr.set_menu(f"{p.get_style_name().upper()}", lines)
                    sel = scr.ask()
                    if not sel.isdigit() or int(sel) == 0:
                        continue
                    if int(sel) > len(jutsu):
                        scr.hint = "Invalid — try again."
                        continue
                    entry  = jutsu[int(sel) - 1]
                    result = p.cast(enemy, entry, awakened_turn)
                    if result is None:
                        scr.hint = f"Not enough chakra! (need {entry[2]})"
                        continue
                    dmg, jname = result
                    scr.player_attack(dmg, style=p.style, name=jname, awakened=awakened_turn)
                    scr.say(f"{DIM}{entry[3]}{RESET}")
                    consumed = True

                elif action == "3":
                    blocking = True
                    scr.guard(p.restore_chakra(10))
                    consumed = True

                elif action == "4":
                    if not p.inventory:
                        scr.hint = "Your bag is empty."
                        continue
                    lines = []
                    for i, item in enumerate(p.inventory, 1):
                        lines.append(f"{rgb(*GOLD)}{BOLD}[{i}]{RESET} {BOLD}{item.name}{RESET}  {DIM}{item.desc}{RESET}")
                    lines.append(f"{rgb(*GOLD)}{BOLD}[0]{RESET} Cancel")
                    scr.set_menu("BAG", lines)
                    sel = scr.ask()
                    if not sel.isdigit() or int(sel) == 0:
                        continue
                    if int(sel) > len(p.inventory):
                        scr.hint = "Invalid — try again."
                        continue
                    audio.sfx("heal")
                    scr.say(p.use_item(int(sel) - 1))
                    scr.sync()
                    consumed = True

                elif action in ("5", "6") and (sig if action == "5" else p.custom_jutsu):
                    entry  = sig if action == "5" else p.custom_jutsu
                    result = p.cast(enemy, entry, awakened_turn)
                    if result is None:
                        scr.hint = f"Not enough chakra! (need {entry[2]})"
                        continue
                    dmg, jname = result
                    scr.player_attack(dmg, style=p.style, name=jname, ult=True, awakened=awakened_turn)
                    scr.say(f"{DIM}{entry[3]}{RESET}")
                    consumed = True

                else:
                    scr.hint = "Invalid — try again."

            if not enemy.is_alive():
                break

            # ── enemy turn ──
            if blocking:
                reduction = 5 + p.end // 3
                raw   = enemy.attack_power + random.randint(-3, 3)
                taken = max(1, raw - reduction)
                p.hp -= taken
                scr.enemy_attack(taken, blocked=reduction)
            elif random.random() < p.dodge_chance:
                scr.dodge()
            else:
                dmg = enemy.attack(p)
                scr.enemy_attack(dmg, crit=enemy.last_crit)
            blocking = False
            scr.set_menu("…", [f"{DIM}The enemy is moving…{RESET}"])

        scr.finish()
        p.temp_atk_up = 0
        if p.is_alive():
            p.full_heal()
            p.chakra = p.max_chakra
            audio.music(None)
            clear()
            victory_banner()
            lines = [f"{GREEN}{BOLD}You defeated {enemy_name}!{RESET}", f"{DIM}HP and chakra restored.{RESET}"]
            if not is_story:
                p.add_kill(kill_reward)
                p.add_gold(gold_reward)
                lines.append("")
                lines.append(f"{GREEN}+{kill_reward} kill(s){RESET}   {YELLOW}+{gold_reward}G{RESET}   {rgb(190, 120, 255)}+{exp_reward} EXP{RESET}")
            dropped = enemy.drop_item() if drop_table else None
            if dropped:
                p.add_item(dropped)
                lines += ["", f"{YELLOW}{BOLD}Item found: {dropped}!{RESET}", f"{DIM}{ITEMS[dropped]['desc']}{RESET}"]
            show(panel(lines, "SPOILS", GOLD, ORANGE, pw()))
            if not is_story:
                audio.sfx("coin")
            if not is_story and exp_reward > 0:
                p.gain_exp(exp_reward)
            pause()
            audio.music(before or "village")
            return True

        p.hp = 0
        audio.music(None)
        clear()
        defeat_banner()
        say("You were defeated…", (240, 90, 80))
        pause()
        audio.music(before or "village")
        return False

    # ═════════════════════════════════════════════════════
    #  mission board
    # ═════════════════════════════════════════════════════
    def _mission_board(self) -> None:
        p = self.player
        rank_col = {"D": (200, 200, 205), "C": (110, 220, 120), "B": (90, 200, 255), "A": (255, 205, 70), "S": (255, 80, 90)}
        while True:
            clear()
            header("MISSION BOARD", SKY)
            avail = [m for m in MISSIONS if RANK_NAMES.index(m[1]) <= p.rank_index()]
            entries = []
            for i, (letter, _, _, title, brief, enemy, drop) in enumerate(avail, 1):
                tag = f"{rgb(*rank_col.get(letter, PAPER))}{BOLD}[{letter}-Rank]{RESET}"
                entries.append((i, title, brief, tag))
            menu_panel("AVAILABLE JOBS", entries, SKY, VIOLET)
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
            header(title.upper(), rank_col.get(letter))
            story_panel(f"{letter}-RANK BRIEFING", [brief], rank_col.get(letter, SKY))
            say(f"{DIM}Reward: +{exp} EXP · +{gold}G · +{kills} kill(s){RESET}")
            pause("ENTER to accept the mission")
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
        inner = pw() - 4
        audio.music("story")
        while True:
            clear()
            header("THE SHINOBI WORLD", LEAF)
            rows = [f"{DIM}Every nation has its own story. Choose where to go.{RESET}", ""]
            for i, c in enumerate(story.COUNTRIES, 1):
                chapters = story.CHAPTERS_BY_COUNTRY[c["key"]]
                done = sum(1 for ch in chapters if ch["id"] in p.story_done)
                col  = COLOR_RGB.get(c["color"], PAPER)
                home = f"  {YELLOW}★ HOME{RESET}" if c["key"] == self._home_country() else ""
                left = (f"{rgb(*GOLD)}{BOLD}[{i}]{RESET} {rgb(*col)}{BOLD}{c['name']}{RESET} "
                        f"{DIM}— {c['village']}{RESET}{home}")
                right = f"{bar(done, len(chapters), 10, 'x')} {DIM}{done}/{len(chapters)}{RESET}"
                rows.append(spread(left, right, inner))
            rows += ["", f"{rgb(*GOLD)}{BOLD}[0]{RESET} Back"]
            show(panel(rows, "WORLD MAP", LEAF, SKY))
            c = get_valid_input(0, len(story.COUNTRIES))
            if c == 0:
                return
            self._country_chapters(story.COUNTRIES[c - 1])

    def _country_chapters(self, country: dict) -> None:
        p        = self.player
        chapters = story.CHAPTERS_BY_COUNTRY[country["key"]]
        col      = COLOR_RGB.get(country["color"], PAPER)
        inner    = pw() - 4
        while True:
            clear()
            header(country["name"].upper(), col)
            rows = [f"{rgb(*col)}{BOLD}{country['village']}{RESET}"]
            rows += [f"{DIM}{l}{RESET}" for l in textwrap.wrap(country["blurb"], inner)]
            if country["key"] == self._home_country():
                rows.append(f"{YELLOW}★ Home soil: +15% EXP on every chapter here.{RESET}")
            rows.append("")
            for i, ch in enumerate(chapters, 1):
                reason = self._chapter_locked_reason(chapters, i - 1)
                done   = ch["id"] in p.story_done
                lvl    = ch["rec_level"]
                lcol   = YELLOW if p.level < lvl - 2 else DIM
                if done:
                    flag = f"{GREEN}✔ done{RESET}"
                elif reason is None:
                    flag = f"{GREEN}{BOLD}NEW{RESET}"
                elif reason.startswith("Reach"):
                    flag = f"{DIM}locked · {ch['rank']}{RESET}"
                else:
                    flag = f"{DIM}locked{RESET}"
                title = short_title(ch["title"])
                left  = f"{rgb(*GOLD)}{BOLD}[{i:>2}]{RESET} " + (f"{DIM}{title}{RESET}" if reason and not done else f"{BOLD}{title}{RESET}")
                rows.append(spread(left, f"{flag}  {lcol}Lv {lvl}{RESET}", inner))
            rows += ["", f"{rgb(*GOLD)}{BOLD}[ 0]{RESET} Back"]
            show(panel(rows, f"{country['name'].upper()} · {sum(1 for c in chapters if c['id'] in p.story_done)}/{len(chapters)}", col, SKY))
            c = get_valid_input(0, len(chapters))
            if c == 0:
                return
            ch = chapters[c - 1]
            reason = self._chapter_locked_reason(chapters, c - 1)
            if reason:
                audio.sfx("ui_error")
                say(f"Locked. {reason}", (250, 205, 80))
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

    def _play_chapter(self, ch: dict, country: dict, first_time: bool) -> None:
        p = self.player
        bonus = 1.15 if country["key"] == self._home_country() else 1.0
        exp   = int(ch["exp"] * bonus)
        col   = COLOR_RGB.get(country["color"], PAPER)

        audio.sfx("gong")
        if ch.get("stages"):
            won = self._play_multi_stage(ch, col)
        else:
            won = self._play_single_boss(ch, col)

        if not won:
            p.full_heal()
            say("You fall… but the story isn't over yet.", (250, 205, 80))
            say(f"{DIM}HP restored. Recover and try again.{RESET}")
            pause()
            return

        clear()
        audio.sfx("success")
        header("CHAPTER COMPLETE", (110, 220, 120))
        lines = [f"{GREEN}{BOLD}{ch['title']}{RESET}", ""] + list(ch["victory_lines"])
        story_panel("EPILOGUE", lines, (110, 220, 120), SKY)

        if first_time:
            p.story_done.add(ch["id"])
            p.add_kill(ch["kills"])
            p.add_gold(ch["gold"])
            rew = [f"{rgb(190, 120, 255)}+{exp} EXP{RESET}   {YELLOW}+{ch['gold']}G{RESET}   {GREEN}+{ch['kills']} kills{RESET}"]
            if ch.get("reward"):
                p.add_item(ch["reward"])
                rew.append(f"{YELLOW}{BOLD}Reward: {ch['reward']}!{RESET}")
            show(panel(rew, "REWARDS", GOLD, ORANGE, pw()))
            audio.sfx("coin")
            p.gain_exp(exp)
        else:
            say(f"{DIM}(Replay — no extra rewards.){RESET}")
        pause()

        if p.refresh_rank():
            self._rank_up_scene()
        self._try_awaken()

    def _play_single_boss(self, ch: dict, col) -> bool:
        clear()
        header(ch["title"], col)
        story_panel("STORY", ch["lines"], col)
        if ch.get("choice"):
            self._play_choice(ch["choice"])
        pause("Prepare yourself — ENTER to fight")
        return self.start_battle(ch["boss"], ch["boss_hp"], ch["boss_atk"], is_story=True)

    def _play_multi_stage(self, ch: dict, col) -> bool:
        clear()
        header(ch["title"], col)
        story_panel("STORY", ch["lines"], col)
        say(f"{DIM}This chapter has {len(ch['stages'])} stages.{RESET}")
        pause("ENTER to begin")

        for i, st in enumerate(ch["stages"], 1):
            choice_done = False
            while True:
                clear()
                header(f"STAGE {i}/{len(ch['stages'])}", col)
                story_panel(st["label"].upper(), st["lines"], col)
                if st.get("choice") and not choice_done:
                    self._play_choice(st["choice"])
                    choice_done = True
                pause("Prepare yourself — ENTER to fight")
                if self.start_battle(st["boss"], st["boss_hp"], st["boss_atk"], is_story=True):
                    clear()
                    header(f"STAGE {i} CLEAR", (110, 220, 120))
                    story_panel("AFTERMATH", st["victory_lines"], (110, 220, 120))
                    pause()
                    break
                self.player.full_heal()
                say("You fall… HP restored. Retrying this stage.", (250, 205, 80))
                pause()
        return True

    def _play_choice(self, choice: dict) -> None:
        p = self.player
        rows = [f"{BOLD}{choice['prompt']}{RESET}", ""]
        for i, (text, _, _) in enumerate(choice["options"], 1):
            rows += opt(i, text)
        show(panel(rows, "A CHOICE", VIOLET, SKY))
        c = get_valid_input(1, len(choice["options"]))
        _, result, reward = choice["options"][c - 1]
        say(result, SKY)
        if reward.get("str"):  p.str_stat += reward["str"]
        if reward.get("spd"):  p.spd      += reward["spd"]
        if reward.get("end"):  p.end      += reward["end"]
        if reward.get("gold"): p.add_gold(reward["gold"])
        if reward.get("item"): p.add_item(reward["item"])
        if reward.get("exp"):  p.gain_exp(reward["exp"])
        time.sleep(0.6 if not FAST else 0)

    # ═════════════════════════════════════════════════════
    #  rank-up, awakening, custom jutsu
    # ═════════════════════════════════════════════════════
    def _rank_up_scene(self) -> None:
        clear()
        audio.sfx("rank_up")
        banner("PROMOTED", [(255, 150, 30), (255, 220, 90), (255, 255, 230)])
        show(panel([f"{YELLOW}{BOLD}You have been promoted to {self.player.rank}!{RESET}",
                    f"{DIM}The village will remember your name.{RESET}"], "PROMOTION", GOLD, ORANGE, pw(), kind="double"))
        pause()

    def _try_awaken(self) -> None:
        p = self.player
        if p.awakened or not p.style or p.rank_index() < RANK_NAMES.index("Jonin"):
            return
        name, desc = STYLES[p.style]["awaken"]
        scol = STYLE_RGB.get(p.style, GOLD)
        clear()
        header("SOMETHING STIRS WITHIN YOU", scol)
        story_panel("AWAKENING", [
            "Years of battle have changed you.",
            "Your chakra is climbing beyond anything you’ve felt before.",
            "",
            f"{name}.",
        ], scol)
        pause("ENTER to awaken")
        p.awakened = True
        p.signature_unlocked = True
        clear()
        audio.sfx("awaken")
        banner("AWAKENED", [dimc_(scol, .6), scol, (255, 255, 255)])
        story_panel(f"✦ {name.upper()} ✦", [
            desc, "",
            "Press [M] in battle once per fight:",
            "Damage ×2 and free chakra for one turn — costs 10 HP.", "",
            f"Signature jutsu unlocked: {STYLES[p.style]['ult'][0]}",
        ], scol, mix(scol, (255, 255, 255), .5))
        pause()

    def _forge_original_jutsu(self) -> None:
        p = self.player
        clear()
        header("FORGE ORIGINAL JUTSU", VIOLET)
        if p.custom_jutsu:
            show(panel([f"Your original jutsu: {MAGENTA}{BOLD}{p.custom_jutsu[0]}{RESET}",
                        f"{DIM}{p.custom_jutsu[3]}{RESET}", ""] + opt(1, "Rename it"), "YOUR TECHNIQUE", VIOLET))
            if get_valid_input(0, 1) == 0:
                return
        else:
            story_panel("KAGE-LEVEL", [
                "At Kage-Level, a shinobi stops copying techniques and invents their own.",
                "Name the jutsu that will be yours alone.",
            ], VIOLET)
        while True:
            name = ask_text("Jutsu name »")
            if name:
                break
            say("Name cannot be empty.", (250, 205, 80))
        desc = ask_text("One-line description »") or "A technique born from your own battles."
        p.custom_jutsu = (name, CUSTOM_JUTSU_TEMPLATE["power"], CUSTOM_JUTSU_TEMPLATE["cost"], desc)
        show(panel([f"{GREEN}{BOLD}{name}{RESET} is now in your arsenal!",
                    f"{DIM}Battle slot [6] — damage ×{1 + CUSTOM_JUTSU_TEMPLATE['power'] / 50:.2f}, cost {CUSTOM_JUTSU_TEMPLATE['cost']}.{RESET}"],
                   "FORGED", VIOLET, GOLD, pw(), kind="double"))
        pause()

    # ═════════════════════════════════════════════════════
    #  training
    # ═════════════════════════════════════════════════════
    def _train(self) -> None:
        p = self.player
        clear()
        header("TRAINING GROUNDS", LEAF)
        if p.training >= Player.TRAIN_CAP:
            show(panel([f"{YELLOW}You've pushed your body to its limit for now.{RESET}",
                        f"{DIM}(Training cap of {Player.TRAIN_CAP} sessions reached){RESET}"], "TRAINING", LEAF))
            pause()
            return

        left = Player.TRAIN_CAP - p.training
        head = [f"Sessions remaining  {bar(left, Player.TRAIN_CAP, 14, 'x')} {left}/{Player.TRAIN_CAP}",
                f"{DIM}Pass the mini-game to gain the stat. Fail — gain nothing.{RESET}"]
        menu_panel("TRAIN", [(1, "Strength", "Stone Breaker — STR +2"),
                             (2, "Speed", "Lightning Dash — SPD +2"),
                             (3, "Endurance", "Chakra Control — END +2")], LEAF, SKY, head=head)
        c = get_valid_input(0, 3)
        if c == 0:
            return

        stat  = {1: "str", 2: "spd", 3: "end"}[c]
        label = {1: "STR", 2: "SPD", 3: "END"}[c]
        passed = {1: self._minigame_strength, 2: self._minigame_speed, 3: self._minigame_endurance}[c]()

        audio.sfx("success" if passed else "fail")
        if passed:
            p.train_stat(stat)
            new_val = getattr(p, "str_stat" if stat == "str" else stat)
            show(panel([f"{GREEN}{BOLD}Training successful! {label} increased to {new_val}!{RESET}"], "RESULT", (110, 220, 120), SKY, pw()))
        else:
            p._training += 1
            show(panel([f"{RED}You pushed hard but couldn't break through this time.{RESET}",
                        f"{DIM}Session used. Try a different approach next time.{RESET}"], "RESULT", CRIMSON, ORANGE, pw()))
        pause()

    def _minigame_strength(self) -> bool:
        clear()
        header("STONE BREAKER — STRENGTH TRIAL", ORANGE)
        story_panel("SENSEI", [
            "A massive boulder sits before you.",
            "Your sensei points at the cracks.",
            "“Strike them in order. Muscle memory is everything.”",
        ], ORANGE)
        pause("ENTER to begin")
        seq    = random.choices(["L", "R", "U", "D"], k=5)
        labels = {"L": "Left", "R": "Right", "U": "Up", "D": "Down"}
        arrows = {"L": "←", "R": "→", "U": "↑", "D": "↓"}
        acol   = {"L": (90, 200, 255), "R": (255, 150, 60), "U": (110, 220, 120), "D": (230, 120, 255)}
        inner  = pw() - 4
        seq_txt = "    ".join(f"{rgb(*acol[s])}{BOLD}{arrows[s]}{RESET}" for s in seq)
        show(panel([center(f"{BOLD}Memorize the strike sequence{RESET}", inner), "",
                    center(seq_txt, inner), ""], "MEMORIZE", ORANGE))
        countdown_bar(3.0, "memorize", ORANGE)
        clear()
        header("STONE BREAKER — STRIKE!", ORANGE)
        say(f"Enter  {BOLD}L{RESET}=Left  {BOLD}R{RESET}=Right  {BOLD}U{RESET}=Up  {BOLD}D{RESET}=Down")
        correct = 0
        for i, expected in enumerate(seq, 1):
            while True:
                ans = ask_text(f"Strike {i}/5 »").upper()
                if ans in labels:
                    break
                say("Enter L, R, U, or D.", (240, 90, 80))
            if ans == expected:
                audio.sfx("hit_heavy")
                say(f"{GREEN}✔  Crack!{RESET}")
                correct += 1
            else:
                audio.sfx("ui_error")
                say(f"{RED}✘  The stone holds. (Was: {labels[expected]}){RESET}")
        passed = correct >= 4
        col = (110, 220, 120) if passed else (250, 205, 80)
        say(f"{'The boulder shatters!' if passed else 'The boulder barely moved.'} ({correct}/5, need 4+)", col)
        time.sleep(1 if not FAST else 0)
        return passed

    def _minigame_speed(self) -> bool:
        clear()
        header("LIGHTNING DASH — SPEED TRIAL", (255, 240, 90))
        story_panel("SENSEI", [
            "Your sensei stands at the end of the track.",
            "“When the signal comes — move. Don't think. Move.”",
        ], (255, 240, 90))
        pause("ENTER to get ready")
        for count, cols in (("3", [(255, 80, 80), (255, 160, 100)]), ("2", [(255, 170, 50), (255, 220, 100)]),
                            ("1", [(255, 230, 80), (255, 255, 180)]), ("GO!", [(80, 230, 120), (220, 255, 220)])):
            clear()
            audio.sfx("success" if count == "GO!" else "ui_select")
            banner(count, cols, 6)
            time.sleep((0.55 if count != "GO!" else 0.1) if not FAST else 0)
        target = random.choice(["RENAN", "JULIANNE", "BENEDICT", "PATRICK", "SIXSEVEN",
                                "RASENGAN", "CHAKRA", "KUNAI", "SHURIKEN", "SHARINGAN"])
        clear()
        header("LIGHTNING DASH — GO!", (255, 240, 90))
        say("Type this word as fast as you can:")
        banner(target, [(255, 200, 60), (255, 255, 255)], 5)
        flush_stdin()
        start   = time.time()
        ans     = input(mpad() + f"{rgb(*GOLD)}{BOLD}»{RESET} ").strip().upper()
        elapsed = time.time() - start
        if ans == target and elapsed <= 3.5:
            say(f"{BOLD}Like lightning! ({elapsed:.2f}s — target ≤3.5s){RESET}", (110, 220, 120))
            return True
        if ans == target:
            say(f"Correct word, but too slow ({elapsed:.2f}s — need ≤3.5s).", (250, 205, 80))
        else:
            say("Wrong word typed. Focus!", (240, 90, 80))
        return False

    def _minigame_endurance(self) -> bool:
        clear()
        header("CHAKRA CONTROL — ENDURANCE TRIAL", SKY)
        story_panel("SENSEI", [
            "Your sensei sits across from you, eyes closed.",
            "“Chakra control is rhythm. Match mine.”",
        ], SKY)
        pause("ENTER to begin")
        rounds, interval, tolerance = 5, 2.0, 0.6
        passed_rounds = 0
        say(f"Watch the rhythm — one pulse every {interval:.0f} seconds.")
        for _ in range(3):
            countdown_bar(interval, "pulse", SKY)
            audio.sfx("chakra")
            say(f"{rgb(*SKY)}{BOLD}◉ PULSE{RESET}") if not FAST else None
        say(f"Now press ENTER every {interval:.0f} seconds to match it.")
        say(f"{DIM}({rounds} pulses — hit within ±{tolerance}s each time){RESET}")
        pause("ENTER to start the first pulse")
        for i in range(1, rounds + 1):
            flush_stdin()
            start = time.time()
            input(mpad() + f"{DIM}Pulse {i}/{rounds}…{RESET} ")
            elapsed = time.time() - start
            audio.sfx("chakra")
            if abs(elapsed - interval) <= tolerance:
                say(f"{GREEN}✔  Perfect pulse ({elapsed:.2f}s){RESET}")
                passed_rounds += 1
            else:
                way = "too fast" if elapsed < interval else "too slow"
                say(f"{RED}✘  Off rhythm ({elapsed:.2f}s — {way}){RESET}")
            time.sleep(0.3 if not FAST else 0)
        passed = passed_rounds >= 4
        col = (110, 220, 120) if passed else (250, 205, 80)
        say(f"{'Perfect control!' if passed else 'Your chakra wavered.'} ({passed_rounds}/{rounds}, need 4+)", col)
        time.sleep(1 if not FAST else 0)
        return passed

    # ═════════════════════════════════════════════════════
    #  style, items, shop, rank
    # ═════════════════════════════════════════════════════
    def _style_menu(self) -> None:
        p = self.player
        clear()
        header("STYLE & JUTSU", STYLE_RGB.get(p.style, SKY))
        inner = pw() - 4
        rows = [f"Current style: {style_colored(p.style, p.get_style_name())}", ""]
        for jn, jp, jc, jd in p.jutsu_list:
            rows.append(spread(f"{style_colored(p.style, '•')} {BOLD}{jn}{RESET}", f"{DIM}×{1 + jp / 50:.2f} · {jc} CHK{RESET}", inner))
            rows.append(f"    {DIM}{jd}{RESET}")
        if p.signature:
            rows += ["", f"{YELLOW}★ Signature: {p.signature[0]} — ×{1 + p.signature[1] / 50:.2f}, cost {p.signature[2]}{RESET}"]
        if p.custom_jutsu:
            rows.append(f"{MAGENTA}★ Original : {p.custom_jutsu[0]} — ×{1 + p.custom_jutsu[1] / 50:.2f}, cost {p.custom_jutsu[2]}{RESET}")
        rows += [""] + opt(1, "Switch style") + opt(0, "Back")
        show(panel(rows, "CHAKRA NATURE", STYLE_RGB.get(p.style, SKY)))
        if get_valid_input(0, 1) == 1:
            self._choose_style()

    def _choose_style(self) -> None:
        p = self.player
        clear()
        header("CHOOSE YOUR CHAKRA NATURE", VIOLET)
        entries = []
        for i, name in enumerate(STYLE_NAMES, 1):
            first = STYLES[name]["jutsu"][0][0]
            entries.append((i, style_colored(name, name), f"opens with {first}"))
        menu_panel("NATURES", entries, VIOLET, SKY, back=None)
        c = get_valid_input(1, len(STYLE_NAMES))
        p.style = STYLE_NAMES[c - 1]
        say(f"You now follow the path of {style_colored(p.style, p.get_style_name())}.")
        pause()

    def _use_item_screen(self) -> None:
        p = self.player
        clear()
        header("YOUR BAG", GOLD)
        if not p.inventory:
            show(panel([f"{DIM}(empty){RESET}"], "BAG", GOLD))
            pause()
            return
        entries = [(i, item.name, item.desc) for i, item in enumerate(p.inventory, 1)]
        menu_panel("BAG", entries, GOLD, ORANGE, back="Back")
        c = get_valid_input(0, len(p.inventory))
        if c:
            audio.sfx("heal")
            say(p.use_item(c - 1))
            pause()

    def _visit_shop(self) -> None:
        p = self.player
        while True:
            clear()
            header("ICHIRAKU & SUPPLY SHOP", ORANGE)
            entries = [(i, name, ITEMS[name]["desc"], f"{YELLOW}{SHOP_PRICES[name]}G{RESET}")
                       for i, name in enumerate(SHOP_STOCK, 1)]
            menu_panel("SHOP", entries, ORANGE, GOLD, back="Leave",
                       head=[f"Gold  {YELLOW}{BOLD}{p.gold}G{RESET}"])
            c = get_valid_input(0, len(SHOP_STOCK))
            if c == 0:
                return
            name = SHOP_STOCK[c - 1]
            if p.spend_gold(SHOP_PRICES[name]):
                p.add_item(name)
                audio.sfx("coin")
                say(f"Bought {name}!", (110, 220, 120))
            else:
                audio.sfx("ui_error")
                say("Not enough gold.", (240, 90, 80))
            pause()

    def _show_rank_progress(self) -> None:
        p = self.player
        clear()
        header("RANK PROGRESS", GOLD)
        rows = []
        for name, threshold in NINJA_RANKS:
            reached = p.kills >= threshold
            dot = f"{GREEN}●{RESET}" if reached else f"{DIM}○{RESET}"
            here = f"  {YELLOW}{BOLD}◄ you are here{RESET}" if name == p.rank else ""
            col = "" if reached else DIM
            rows.append(f"{dot} {col}{name:<15} {threshold:>4} kills{RESET}{here}")
        nxt, need = p.next_rank_info()
        rows += ["", f"Total kills: {BOLD}{p.kills}{RESET}"]
        if nxt != "MAX RANK":
            rows.append(f"{need} more to reach {YELLOW}{BOLD}{nxt}{RESET}.")
        show(panel(rows, "LADDER OF SHINOBI", GOLD, ORANGE))
        pause()

    # ═════════════════════════════════════════════════════
    #  sound settings
    # ═════════════════════════════════════════════════════
    def _sound_menu(self) -> None:
        while True:
            clear()
            header("SOUND", SKY)
            c = audio.settings()
            onoff = lambda v: f"{GREEN}{BOLD}ON{RESET}" if v else f"{RED}{BOLD}OFF{RESET}"
            head = [f"{DIM}Audio engine:{RESET} {audio.backend_name()}"]
            if not audio.available():
                head += [f"{YELLOW}No audio player was found, so the game runs silent.{RESET}",
                         f"{DIM}Fix: pip install pygame   (Linux: install pulseaudio-utils / alsa-utils){RESET}"]
            menu_panel("SOUND", [(1, "Music", f"background loops  {onoff(c['music'])}"),
                                 (2, "Sound effects", f"hits, jutsu, menus  {onoff(c['sfx'])}"),
                                 (3, "Test", "play a taiko hit")], SKY, VIOLET, head=head)
            ch = get_valid_input(0, 3)
            if ch == 0:
                return
            if ch == 1:
                audio.set_music(not c["music"])
            elif ch == 2:
                audio.set_sfx(not c["sfx"])
            else:
                audio.sfx("title_boom")
                time.sleep(0.4)

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
            audio.sfx("save")
            show(panel([f"{GREEN}{BOLD}✦ Game saved{RESET} {DIM}to {self.SAVE_FILE}{RESET}"], "SAVED", (110, 220, 120), SKY, pw()))
        except OSError as e:
            say(f"Save failed: {e}", (240, 90, 80))
        pause()

    def _load_game(self) -> bool:
        try:
            with open(self.SAVE_FILE, encoding="utf-8") as f:
                d = json.load(f)
        except FileNotFoundError:
            say(f"No save file found ({self.SAVE_FILE}).", (250, 205, 80))
            pause()
            return False
        except (OSError, ValueError) as e:
            say(f"Load failed: {e}", (240, 90, 80))
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
        header("SAVE LOADED", (110, 220, 120))
        say(f"Welcome back, {BOLD}{p.name}{RESET}.", (110, 220, 120))
        p.show_stats()
        pause()
        return True

    # ═════════════════════════════════════════════════════
    #  character creation
    # ═════════════════════════════════════════════════════
    def _create_character(self) -> Player:
        clear()
        header("CHARACTER CREATION", SKY)
        while True:
            name = ask_text("Enter your name »")
            if name:
                break
            say("Name cannot be empty.", (250, 205, 80))

        clear()
        header("CHOOSE YOUR HIDDEN VILLAGE", LEAF)
        vnames = list(VILLAGES.keys())
        entries = []
        for i, v in enumerate(vnames, 1):
            b = VILLAGES[v]["bonus"]
            entries.append((i, f"{CYAN}{v}{RESET}", VILLAGES[v]["desc"], f"{DIM}STR +{b[0]} SPD +{b[1]} END +{b[2]}{RESET}"))
        menu_panel("VILLAGES", entries, LEAF, SKY, back=None)
        village = vnames[get_valid_input(1, len(vnames)) - 1]
        say(f"Village chosen: {CYAN}{BOLD}{village}{RESET}")
        pause("ENTER to reveal your clan")

        clan = self._clan_roll_scene()
        self.player = Player(name, clan, village)
        self._choose_style()
        self._graduation_trial()

        clear()
        header("CHARACTER CREATED", (110, 220, 120))
        self.player.show_stats()
        pause()
        return self.player

    def _clan_roll_scene(self) -> str:
        clear()
        header("CLAN AWAKENING", VIOLET)
        names = list(CLAN_POOL.keys())
        pool = []
        for n, d in CLAN_POOL.items():
            pool.extend([n] * RARITY_WEIGHTS[d["rarity"]])
        chosen = random.choice(pool)
        info   = CLAN_POOL[chosen]
        rcol   = RARITY_RGB[info["rarity"]]
        clan_reveal(names, chosen, info["rarity"])
        kind = "double" if info["rarity"] in ("Legendary", "Mythic", "Secret") else "round"
        show(panel([f"{rgb(*rcol)}{BOLD}{chosen}{RESET}  {DIM}— {info['rarity']}{RESET}",
                    f"Bonus  STR +{info['stats'][0]}   SPD +{info['stats'][1]}   END +{info['stats'][2]}"],
                   "YOUR CLAN", rcol, mix(rcol, (255, 255, 255), .5), pw(), kind=kind))
        pause()
        return chosen

    def _graduation_trial(self) -> None:
        clear()
        header("ACADEMY GRADUATION TRIAL", ORANGE)
        story_panel("THE ACADEMY", [
            "Before you earn a forehead protector, three tests stand in your way.",
            "Pass them all, and you’ll be a Genin of your village.",
        ], ORANGE)
        pause("ENTER to begin the trial")
        for t in GRADUATION_TRIALS:
            while not self.start_battle(t["name"], t["hp"], t["atk"], is_story=True):
                self.player.full_heal()
                say("The proctor lets you retry.", (250, 205, 80))
                pause()
        clear()
        audio.sfx("level_up")
        banner("PASSED", [(110, 220, 120), (230, 255, 230)])
        say(f"{GREEN}{BOLD}You pass! The headband is yours.{RESET}")
        pause()

    def _intro_story(self) -> None:
        p = self.player
        clear()
        header("YOUR STORY BEGINS", GOLD)
        story_panel("PROLOGUE", [
            f"Your name is {p.name}, of the {p.clan} clan.",
            f"You wear the headband of {p.village}.",
            "The Akatsuki are on the move, and the five great nations are restless.",
            "Every country has its own trouble. Every village has its own scars.",
            "Take missions. Earn rank. Walk through every land.",
            "And when the world needs shinobi — be ready.",
        ], GOLD, ORANGE)
        pause()


# ── small local helpers ─────────────────────────────────
def columns_rows(left, right):
    n = max(len(left), len(right))
    return [(left[i] if i < len(left) else "") + (right[i] if i < len(right) else "") for i in range(n)]


def dimc_(c, k):
    return tuple(int(v * k) for v in c)
