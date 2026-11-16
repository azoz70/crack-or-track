#!/usr/bin/env python3
"""Tests for the advanced learning & assessment engine features."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import engine
from content import BY_ID, MISSIONS, localize_mission


class FakeForm(dict):
    def getlist(self, key):
        v = self.get(key, [])
        return v if isinstance(v, list) else [v]


class TestNewQuestionTypes(unittest.TestCase):
    def test_true_false(self):
        ok = engine.evaluate({"type": "true_false", "correct": "true"}, FakeForm(answer="true"))[1]
        self.assertTrue(ok)

    def test_true_false_wrong(self):
        ok = engine.evaluate({"type": "true_false", "correct": "true"}, FakeForm(answer="false"))[1]
        self.assertFalse(ok)

    def test_log_analysis(self):
        ok = engine.evaluate({"type": "log_analysis", "correct": 1}, FakeForm(answer="1"))[1]
        self.assertTrue(ok)

    def test_command_output(self):
        ok = engine.evaluate({"type": "command_output", "correct": 0}, FakeForm(answer="0"))[1]
        self.assertTrue(ok)

    def test_event_investigation(self):
        ok = engine.evaluate({"type": "event_investigation", "correct": 2}, FakeForm(answer="2"))[1]
        self.assertTrue(ok)

    def test_scenario(self):
        ok = engine.evaluate({"type": "scenario", "correct": 1}, FakeForm(answer="1"))[1]
        self.assertTrue(ok)

    def test_incident_response(self):
        ok = engine.evaluate({"type": "incident_response", "correct": [0, 2]}, FakeForm(answer=["0", "2"]))[1]
        self.assertTrue(ok)

    def test_evidence_id(self):
        ok = engine.evaluate({"type": "evidence_id", "correct": [1]}, FakeForm(answer=["1"]))[1]
        self.assertTrue(ok)


class TestXp(unittest.TestCase):
    def test_xp_for(self):
        self.assertEqual(engine.xp_for(100, 1), 135)

    def test_xp_scales_with_difficulty(self):
        self.assertGreater(engine.xp_for(100, 3), engine.xp_for(100, 1))


class TestSkills(unittest.TestCase):
    def test_skill_taxonomy(self):
        self.assertIn("Reconnaissance", engine.SKILLS["red"])
        self.assertIn("Incident Response", engine.SKILLS["blue"])
        self.assertIn("Mitigation Planning", engine.SKILLS["purple"])

    def test_skill_for_explicit(self):
        self.assertEqual(engine.skill_for({}, {"skill": "API Security"}), "API Security")

    def test_every_stage_has_skill(self):
        for m in MISSIONS:
            for s in m["stages"]:
                self.assertTrue(s.get("skill"), m["id"])


class TestLocalization(unittest.TestCase):
    def test_localize_mission_ar(self):
        m = BY_ID["r1"]
        ar = localize_mission(m, "ar")
        self.assertNotEqual(ar["story"], m["story"])
        self.assertIn("الاستطلاع", ar["category"])

    def test_localize_options(self):
        ar = localize_mission(BY_ID["r2"], "ar")
        self.assertEqual(ar["stages"][0]["options"][0], "تسجيل دخول طبيعي")

    def test_localize_keeps_english(self):
        m = BY_ID["r1"]
        self.assertEqual(localize_mission(m, "en")["story"], m["story"])

    def test_severity_not_translated(self):
        m = BY_ID["r1"]
        ar = localize_mission(m, "ar")
        self.assertEqual(ar["stages"][2]["severity_options"], m["stages"][2]["severity_options"])


class TestContentQuality(unittest.TestCase):
    def test_all_stages_have_skill_concept_example(self):
        for m in MISSIONS:
            for s in m["stages"]:
                self.assertTrue(s.get("skill"), m["id"])
                self.assertTrue(s.get("concept"), m["id"])
                self.assertTrue(s.get("example"), m["id"])

    def test_option_stages_have_explanations(self):
        for m in MISSIONS:
            for s in m["stages"]:
                if "options" in s:
                    self.assertTrue(s.get("option_explanations"), m["id"])

    def test_all_stages_have_three_hint_levels(self):
        for m in MISSIONS:
            for s in m["stages"]:
                self.assertEqual(len(s.get("hint_levels", [])), 3, m["id"])

    def test_all_missions_have_arabic(self):
        for m in MISSIONS:
            self.assertIn("title_ar", m)
            self.assertIn("story_ar", m)

    def test_new_formats_are_used(self):
        types = {s["type"] for m in MISSIONS for s in m["stages"]}
        for t in ("true_false", "log_analysis", "command_output", "event_investigation",
                  "scenario", "incident_response", "evidence_id"):
            self.assertIn(t, types)


if __name__ == "__main__":
    unittest.main()
