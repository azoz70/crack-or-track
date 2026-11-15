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
        print_banner()
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


def main():
    mission = MISSIONS[0]
    if len(sys.argv) > 1:
        try:
            mission = MISSIONS[int(sys.argv[1]) - 1]
        except (ValueError, IndexError):
            raise SystemExit(f"Usage: {sys.argv[0]} [1-{len(MISSIONS)}]")

    game = Game(mission)
    try:
        game.run()
    finally:
        elapsed = time.time() - game.t0
        save_score(mission["name"], elapsed, game.heat, game.commands)
        print(f"\n time: {elapsed:.1f}s | heat: {game.heat}% | commands: {game.commands}")


if __name__ == "__main__":
    main()
