#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import engine
from content import BY_ID, MISSIONS


class FakeForm(dict):
    def getlist(self, key):
        value = self.get(key, [])
        return value if isinstance(value, list) else [value]


class TestRanks(unittest.TestCase):
    def test_rookie(self):
        self.assertEqual(engine.rank_for(0), "Cyber Rookie")

    def test_elite(self):
        self.assertEqual(engine.rank_for(9999), "Elite Cyber Operator")

    def test_next_rank(self):
        threshold, name = engine.next_rank(0)
        self.assertEqual(name, "Junior Analyst")
        self.assertEqual(threshold, 250)

    def test_no_next_rank(self):
        self.assertEqual(engine.next_rank(9999), (None, None))


class TestEvaluate(unittest.TestCase):
    def test_analyze_correct(self):
        stage = {"type": "analyze", "correct": 1, "explain": "x"}
        points, ok, _ = engine.evaluate(stage, FakeForm(answer="1"))
        self.assertEqual(points, 1.0)
        self.assertTrue(ok)

    def test_analyze_wrong(self):
        stage = {"type": "analyze", "correct": 1, "explain": "x"}
        points, ok, _ = engine.evaluate(stage, FakeForm(answer="0"))
        self.assertEqual(points, 0.0)
        self.assertFalse(ok)

    def test_decision_exact_set(self):
        stage = {"type": "decision", "correct": [0, 2], "explain": "x"}
        points, ok, _ = engine.evaluate(stage, FakeForm(answer=["2", "0"]))
        self.assertTrue(ok)

    def test_decision_missing_option(self):
        stage = {"type": "decision", "correct": [0, 2], "explain": "x"}
        points, ok, _ = engine.evaluate(stage, FakeForm(answer=["0"]))
        self.assertFalse(ok)

    def test_terminal_accepts_phrase(self):
        stage = {"type": "terminal", "explain": "x",
                 "accept": ["nmap -sv 10.10.10.10"]}
        points, ok, _ = engine.evaluate(
            stage, FakeForm(answer="NMAP -sV 10.10.10.10"))
        self.assertTrue(ok)

    def test_terminal_rejects_other(self):
        stage = {"type": "terminal", "explain": "x",
                 "accept": ["nmap -sv 10.10.10.10"]}
        points, ok, _ = engine.evaluate(stage, FakeForm(answer="ping 8.8.8.8"))
        self.assertFalse(ok)

    def test_report_full_credit(self):
        stage = {"type": "report", "explain": "x", "severity": "high",
                 "remediation": 1}
        points, ok, _ = engine.evaluate(
            stage, FakeForm(severity="high", remediation="1"))
        self.assertEqual(points, 1.0)
        self.assertTrue(ok)

    def test_report_partial_credit(self):
        stage = {"type": "report", "explain": "x", "severity": "high",
                 "remediation": 1}
        points, ok, _ = engine.evaluate(
            stage, FakeForm(severity="low", remediation="1"))
        self.assertEqual(points, 0.5)
        self.assertFalse(ok)


class TestScoring(unittest.TestCase):
    def test_perfect_score(self):
        result = engine.mission_score([1, 2, 3], 3.0, 0, 0, 2, 10, 60)
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["time_bonus"], 10)

    def test_penalties(self):
        result = engine.mission_score([1, 2, 3], 3.0, 2, 2, 2, 10, 9999)
        self.assertLess(result["score"], 100)
        self.assertEqual(result["time_bonus"], 0)

    def test_score_never_negative(self):
        result = engine.mission_score([1], 0.0, 20, 4, 3, 10, 9999)
        self.assertEqual(result["score"], 0)

    def test_xp_scales_with_difficulty(self):
        easy = engine.mission_score([1], 1.0, 0, 0, 1, 10, 10)
        hard = engine.mission_score([1], 1.0, 0, 0, 3, 10, 10)
        self.assertGreater(hard["xp"], easy["xp"])


class TestContent(unittest.TestCase):
    def test_all_missions_have_stages(self):
        for m in MISSIONS:
            self.assertTrue(m["stages"], m["id"])
            self.assertEqual(len(m["hints"]), 4, m["id"])

    def test_tracks_are_valid(self):
        for m in MISSIONS:
            self.assertIn(m["track"], ("red", "blue", "both"))

    def test_ids_unique(self):
        self.assertEqual(len(BY_ID), len(MISSIONS))

    def test_explanations_present(self):
        for m in MISSIONS:
            self.assertTrue(m["explanation"])
            self.assertTrue(m["real_world"])


if __name__ == "__main__":
    unittest.main()
