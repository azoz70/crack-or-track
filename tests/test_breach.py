#!/usr/bin/env python3
"""Tests for the BREACH game engine (no I/O, no network)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import breach
from breach import Game, MISSIONS, Caught, Win, MAX_HEAT


def new_game(mission=0):
    return Game(MISSIONS[mission])


class TestRecon(unittest.TestCase):
    def test_scan_lists_all_hosts(self):
        g = new_game()
        out = g.execute("scan")
        for ip in MISSIONS[0]["hosts"]:
            self.assertIn(ip, out)

    def test_scan_raises_heat(self):
        g = new_game()
        g.execute("scan")
        self.assertEqual(g.heat, 5)

    def test_unknown_target(self):
        g = new_game()
        out = g.execute("connect 1.2.3.4")
        self.assertIn("Unknown target", out)


class TestAccess(unittest.TestCase):
    def test_open_host_connects(self):
        g = new_game()
        out = g.execute("connect 10.10.10.10")
        self.assertIn("Session opened", out)
        self.assertEqual(g.host, "10.10.10.10")

    def test_creds_host_refuses_direct_connect(self):
        g = new_game()
        out = g.execute("connect 10.10.10.20")
        self.assertIn("requires credentials", out)
        self.assertIsNone(g.host)

    def test_login_success(self):
        g = new_game()
        out = g.execute("login 10.10.10.20 admin Sunshine2024")
        self.assertIn("Authenticated", out)
        self.assertEqual(g.host, "10.10.10.20")

    def test_login_failure_adds_heat(self):
        g = new_game()
        before = g.heat
        out = g.execute("login 10.10.10.20 admin wrong")
        self.assertIn("failed", out)
        self.assertGreater(g.heat, before)

    def test_login_wrong_host(self):
        g = new_game()
        out = g.execute("login 9.9.9.9 admin x")
        self.assertIn("Unknown target", out)


class TestFiles(unittest.TestCase):
    def test_ls_requires_connection(self):
        g = new_game()
        self.assertIn("Not connected", g.execute("ls"))

    def test_cat_requires_connection(self):
        g = new_game()
        self.assertIn("Not connected", g.execute("cat index.html"))

    def test_cat_missing_file(self):
        g = new_game()
        g.execute("connect 10.10.10.10")
        self.assertIn("No such file", g.execute("cat nope.txt"))

    def test_cat_reads_file(self):
        g = new_game()
        g.execute("connect 10.10.10.10")
        self.assertIn("Acme Shop", g.execute("cat index.html"))


class TestObjective(unittest.TestCase):
    def test_flag_requires_host(self):
        g = new_game()
        self.assertIn("Not connected", g.execute("flag"))

    def test_flag_wrong_host(self):
        g = new_game()
        g.execute("connect 10.10.10.10")
        self.assertIn("Wrong host", g.execute("flag"))

    def test_flag_requires_reading_flag_first(self):
        g = new_game()
        g.execute("login 10.10.10.20 admin Sunshine2024")
        self.assertIn("must read flag.txt", g.execute("flag"))

    def test_full_win_path(self):
        g = new_game()
        g.execute("scan")
        g.execute("connect 10.10.10.10")
        g.execute("cat index.html")
        g.execute("login 10.10.10.20 admin Sunshine2024")
        g.execute("ls")
        g.execute("cat flag.txt")
        with self.assertRaises(Win):
            g.execute("flag")

    def test_mission3_exploit_path(self):
        g = new_game(2)
        g.execute("scan")
        out = g.execute("exploit 10.30.30.8")
        self.assertIn("Exploit succeeded", out)
        g.execute("login 10.30.30.25 vault V4ult!2021")
        g.execute("cat flag.txt")
        with self.assertRaises(Win):
            g.execute("flag")


class TestDetection(unittest.TestCase):
    def test_heat_caps_at_caught(self):
        g = new_game()
        with self.assertRaises(Caught):
            for _ in range(20):
                g.execute("login 10.10.10.20 admin wrong")
        self.assertGreaterEqual(g.heat, MAX_HEAT)

    def test_heat_command(self):
        g = new_game()
        self.assertIn("detection", g.execute("heat"))


class TestParsing(unittest.TestCase):
    def test_empty_line(self):
        g = new_game()
        self.assertEqual(g.execute("   "), "")

    def test_unknown_command(self):
        g = new_game()
        self.assertIn("Unknown command", g.execute("dance"))

    def test_bad_quoting(self):
        g = new_game()
        self.assertIn("Bad quoting", g.execute("cat 'unclosed"))


if __name__ == "__main__":
    unittest.main()
