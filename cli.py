#!/usr/bin/env python3
"""
CRACK OR TRACK — a terminal hacking simulator.

You are a red-team operator with an authorized scope and a detection meter.
Complete the objective before detection reaches 100.

Commands: help, scan, connect, login, exploit, ls, cat, flag, heat, exit
"""

import json
import shlex
import sys
import time
from pathlib import Path

SCORES = Path.home() / ".crack_or_track_scores.json"
MAX_HEAT = 100

MISSIONS = [
    {
        "name": "Mission 1 — The Exposed Web Server",
        "brief": "A shop left its staging server online. Get the customer DB flag.",
        "hosts": {
            "10.10.10.10": {
                "name": "web-01", "ports": [80], "access": "open", "creds": None,
                "files": {"index.html": "<h1>Acme Shop</h1>\n"
                                       "<!-- TODO remove backup creds admin:Sunshine2024 -->"},
                "flag": False,
            },
            "10.10.10.20": {
                "name": "db-01", "ports": [5432], "access": "creds",
                "creds": ("admin", "Sunshine2024"),
                "files": {"customers.sql": "INSERT INTO customers ...",
                          "flag.txt": "FLAG{w3b_l34k_t0_db_pwn}"},
                "flag": True,
            },
        },
    },
    {
        "name": "Mission 2 — Lateral Movement",
        "brief": "One host holds the keys to the next. Pivot carefully.",
        "hosts": {
            "10.20.20.5": {
                "name": "jump-01", "ports": [22], "access": "open", "creds": None,
                "files": {"notes.txt": "ops rotates creds monthly.\nbackup:backup!2023"},
                "flag": False,
            },
            "10.20.20.15": {
                "name": "files-01", "ports": [445], "access": "creds",
                "creds": ("backup", "backup!2023"),
                "files": {"share.txt": "finance export pending",
                          "creds.txt": "svc_sql:Sql!Server2022"},
                "flag": False,
            },
            "10.20.20.30": {
                "name": "sql-01", "ports": [1433], "access": "creds",
                "creds": ("svc_sql", "Sql!Server2022"),
                "files": {"flag.txt": "FLAG{l4t3r4l_m0v3m3nt}"},
                "flag": True,
            },
        },
    },
    {
        "name": "Mission 3 — Weak Service",
        "brief": "A legacy service gives a shell. Escalate to the crown jewel.",
        "hosts": {
            "10.30.30.8": {
                "name": "legacy-01", "ports": [8080], "access": "exploit",
                "creds": ("tomcat", "tomcat"),
                "files": {"tomcat-users.xml": "role1=manager-gui"},
                "flag": False,
            },
            "10.30.30.25": {
                "name": "vault-01", "ports": [3306], "access": "creds",
                "creds": ("vault", "V4ult!2021"),
                "files": {"keys.txt": "kms:master:rotated-2021",
                          "flag.txt": "FLAG{expl01t_ch41n_c0mpl3t3}"},
                "flag": True,
            },
        },
    },
]

GREEN = "\033[38;2;16;185;129m"
GOLD = "\033[38;2;212;175;55m"
RED = "\033[38;2;229;72;77m"
BLUE = "\033[38;2;59;130;246m"
DIM = "\033[2m"
RESET = "\033[0m"


def _color_enabled():
    import os
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def paint(text, code):
    return f"{code}{text}{RESET}" if _color_enabled() else text


def print_banner():
    for name in ("cli_wordmark.txt", "cli_art.txt"):
        f = Path(__file__).with_name(name)
        if f.exists():
            for line in f.read_text().splitlines():
                print(paint(line, GREEN))
            print()
    print(paint("  BY ABO SARA", GOLD))
    print(paint("  Crack the System. Track the Threat.", DIM))
    print()


HELP = """
scan                 enumerate hosts in scope          (+5 heat)
connect <ip>         open a session on a host         (+2)
login <ip> <u> <p>   authenticate                       (+2, +10 on failure)
exploit <ip>         use a known weakness              (+20)
ls                   list files on current host       (+1)
cat <file>           read a file                       (+2)
flag                 submit the objective              (+15)
heat                 show detection level
exit                 quit
"""


class Win(Exception):
    pass


class Caught(Exception):
    pass


class Quit(Exception):
    pass


class Game:
    def __init__(self, mission):
        self.m = mission
        self.heat = 0
        self.host = None
        self.read = set()
        self.commands = 0
        self.t0 = time.time()

    # ---------- helpers ----------
    def bump(self, n):
        self.heat = min(MAX_HEAT, self.heat + n)
        if self.heat >= MAX_HEAT:
            raise Caught()

    def bar(self):
        filled = int(self.heat / 5)
        return "[" + "#" * filled + "." * (20 - filled) + f"] {self.heat}%"

    def resolve(self, target):
        for ip, h in self.m["hosts"].items():
            if ip == target or h["name"] == target:
                return ip
        return None

    # ---------- handlers (return output text) ----------
    def cmd_scan(self):
        self.bump(5)
        lines = [f"[*] Scope: {len(self.m['hosts'])} hosts"]
        for ip, h in self.m["hosts"].items():
            lines.append(f"    {ip:<14} {h['name']:<10} ports={h['ports']}  access={h['access']}")
        return "\n".join(lines)

    def cmd_connect(self, target):
        ip = self.resolve(target)
        if not ip:
            return "[-] Unknown target. Run scan first."
        h = self.m["hosts"][ip]
        if h["access"] == "creds":
            self.bump(2)
            return f"[-] {h['name']} requires credentials. Use: login {ip} <user> <pass>"
        if h["access"] == "exploit":
            self.bump(2)
            return f"[-] {h['name']} needs a vulnerability. Use: exploit {ip}"
        self.host = ip
        self.bump(2)
        return f"[+] Session opened on {h['name']} ({ip})"

    def cmd_login(self, target, user, password):
        ip = self.resolve(target)
        if not ip:
            return "[-] Unknown target."
        h = self.m["hosts"][ip]
        self.bump(2)
        if h["creds"] and (user, password) == h["creds"] and h["access"] == "creds":
            self.host = ip
            return f"[+] Authenticated to {h['name']}"
        self.bump(10)
        return "[-] Authentication failed. The SOC noticed."

    def cmd_exploit(self, target):
        ip = self.resolve(target)
        if not ip:
            return "[-] Unknown target."
        h = self.m["hosts"][ip]
        if h["access"] != "exploit":
            self.bump(5)
            return "[-] No known exploitable weakness there."
        self.bump(20)
        self.host = ip
        return (f"[+] Exploit succeeded on {h['name']}. Shell obtained.\n"
                f"    Credentials recovered: {h['creds'][0]}:{h['creds'][1]}")

    def cmd_ls(self):
        if not self.host:
            return "[-] Not connected to a host."
        self.bump(1)
        return "\n".join("    " + f for f in self.m["hosts"][self.host]["files"])

    def cmd_cat(self, fname):
        if not self.host:
            return "[-] Not connected to a host."
        files = self.m["hosts"][self.host]["files"]
        if fname not in files:
            self.bump(2)
            return "[-] No such file."
        self.bump(2)
        self.read.add((self.host, fname))
        return f"\n--- {fname} ---\n{files[fname]}\n"

    def cmd_flag(self):
        if not self.host:
            return "[-] Not connected to a host."
        h = self.m["hosts"][self.host]
        if not h["flag"]:
            self.bump(10)
            return "[-] No objective here. Wrong host."
        if (self.host, "flag.txt") not in self.read:
            return "[-] You must read flag.txt first."
        self.bump(15)
        raise Win(h["files"]["flag.txt"])

    # ---------- dispatch ----------
    def execute(self, line):
        """Run one command line; return its output text."""
        line = line.strip()
        if not line:
            return ""
        self.commands += 1
        try:
            parts = shlex.split(line)
        except ValueError:
            return "[-] Bad quoting."
        cmd, args = parts[0].lower(), parts[1:]

        if cmd == "help":
            return HELP
        if cmd == "scan":
            return self.cmd_scan()
        if cmd == "connect" and args:
            return self.cmd_connect(args[0])
        if cmd == "login" and len(args) == 3:
            return self.cmd_login(*args)
        if cmd == "exploit" and args:
            return self.cmd_exploit(args[0])
        if cmd == "ls":
            return self.cmd_ls()
        if cmd == "cat" and args:
            return self.cmd_cat(args[0])
        if cmd == "flag":
            return self.cmd_flag()
        if cmd == "heat":
            return f"    detection: {self.bar()}"
        if cmd == "exit":
            raise Quit()
        return "[-] Unknown command. Type 'help'."

    # ---------- main loop ----------
    def run(self):
        print(paint("== CRACK MISSION ==", RED) + f" {self.m['name']}")
        print(self.m["brief"])
        print("Type 'help' for commands.\n")

        while True:
            try:
                line = input(paint(f"crack [{self.heat}%] > ", GREEN))
            except (EOFError, KeyboardInterrupt):
                print("\n[!] Session aborted.")
                return
            try:
                out = self.execute(line)
                if out:
                    print(out)
            except Quit:
                print("[!] Disconnected.")
                return
            except Win as flag:
                print("\n" + "=" * 44)
                print(f" OBJECTIVE COMPLETE — {flag}")
                print("=" * 44)
                return
            except Caught:
                print("\n" + "!" * 44)
                print(" SOC DETECTED YOU. Engagement burned.")
                print("!" * 44)
                return


def save_score(mission, seconds, heat, commands):
    data = []
    if SCORES.exists():
        try:
            data = json.loads(SCORES.read_text())
        except Exception:
            data = []
    data.append({"mission": mission, "seconds": round(seconds, 1),
                 "heat": heat, "commands": commands})
    SCORES.write_text(json.dumps(data, indent=2))


WELCOME = """\
CRACK OR TRACK is a cybersecurity training game.

  CRACK (Red Team) — find weaknesses: recon, web apps, APIs.
  TRACK (SOC)      — detect and respond: phishing, SIEM, malware.

You learn by doing: play missions or test yourself with quizzes.
Every host, log, and flag is fictional. Nothing touches a real network."""


def welcome():
    print(paint(WELCOME, DIM))
    print(paint("  Commands: 1 CRACK · 2 TRACK · 3 Quiz · 4 How to play · 5 Exit", GOLD))


def run_quiz(topic):
    import quiz as quizmod
    questions = quizmod.QUIZZES[topic]
    print(paint(f"\n== QUIZ: {topic} ==\n", GREEN + "\033[1m"))
    score = 0
    for i, q in enumerate(questions, 1):
        print(paint(f"Q{i}. {q['q']}", GREEN))
        for j, opt in enumerate(q["o"]):
            print(f"   {j + 1}) {opt}")
        while True:
            ans = input(paint("   Answer (1-4, q to quit): ", GOLD)).strip()
            if ans.lower() == "q":
                return
            if ans in ("1", "2", "3", "4"):
                break
            print("   Enter 1-4.")
        if int(ans) - 1 == q["a"]:
            print(paint("   Correct", GREEN))
            score += 1
        else:
            print(paint(f"   The answer was {q['a'] + 1}", RED))
        print(paint(f"   {q['why']}", DIM))
        print()
    pct = round(score / len(questions) * 100)
    print(paint(f"  Score: {score}/{len(questions)} ({pct}%)", GOLD + "\033[1m"))


def menu():
    print(paint("  ────────────────────────────────", DIM))
    print(paint("  [1] CRACK — play a Red Team mission", RED))
    print(paint("  [2] TRACK — SOC quiz (phishing, SIEM, malware)", BLUE))
    print(paint("  [3] Quiz — 10 questions per topic", GOLD))
    print(paint("  [4] How to play", DIM))
    print(paint("  [5] Exit", DIM))


def play_mission(idx):
    mission = MISSIONS[idx]
    game = Game(mission)
    try:
        game.run()
    finally:
        elapsed = time.time() - game.t0
        save_score(mission["name"], elapsed, game.heat, game.commands)
        print(f"\n time: {elapsed:.1f}s | heat: {game.heat}% | commands: {game.commands}")


def play_mission_menu():
    print()
    for i, m in enumerate(MISSIONS, 1):
        print(paint(f"  [{i}] {m['name']}", RED))
    print(paint("  [b] back", DIM))
    c = input(paint("  > ", GREEN)).strip()
    if c.lower() == "b":
        return
    if c.isdigit() and 1 <= int(c) <= len(MISSIONS):
        play_mission(int(c) - 1)


def quiz_topic_menu(scope="all"):
    import quiz as quizmod
    topics = list(quizmod.QUIZZES.keys())
    if scope == "blue":
        topics = ["Phishing Analysis", "SIEM Investigation", "Malware Analysis"]
    print()
    for i, t in enumerate(topics, 1):
        color = BLUE if t in ("Phishing Analysis", "SIEM Investigation", "Malware Analysis") else RED
        print(paint(f"  [{i}] {t}", color))
    print(paint("  [b] back", DIM))
    c = input(paint("  > ", GREEN)).strip()
    if c.lower() == "b":
        return
    if c.isdigit() and 1 <= int(c) <= len(topics):
        run_quiz(topics[int(c) - 1])


def choose():
    while True:
        menu()
        c = input(paint("  > ", GREEN)).strip()
        if c == "1":
            play_mission_menu()
        elif c == "2":
            quiz_topic_menu("blue")
        elif c == "3":
            quiz_topic_menu("all")
        elif c == "4":
            print()
            welcome()
            print()
        elif c == "5" or c.lower() in ("q", "exit"):
            print(paint("  Goodbye.", DIM))
            return
        else:
            print(paint("  Choose 1-5.", DIM))


def main():
    print_banner()
    print()
    if len(sys.argv) > 1:
        try:
            idx = int(sys.argv[1]) - 1
            if 0 <= idx < len(MISSIONS):
                play_mission(idx)
                return
        except ValueError:
            pass
    welcome()
    print()
    choose()


if __name__ == "__main__":
    main()
