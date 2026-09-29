from django.test import TestCase

from apps.profiles.serivces import build_display_stats
# если файл services.py:
# from apps.profiles.services import build_display_stats


class BuildDisplayStatsFaceitTests(TestCase):
    def test_faceit_metrics(self):
        extra = {
            "skill_level": 8,
            "faceit_elo": 2100,
            "matches": 100,
            "wins": 55,
            "winrate": 55.0,
            "kd": 1.15,
            "hs_percent": 48,
            "game_id": "cs2",
            "top_maps": [
                {"name": "mirage", "matches": 20, "winrate": 60, "kd": 1.2},
            ],
            "match_history": [
                {
                    "won": True,
                    "title": "mirage",
                    "subtitle": "20/15/5",
                    "match_id": "m1",
                }
            ],
            "recent_form": ["W", "L", "W"],
        }
        data = build_display_stats("faceit", extra)
        self.assertTrue(data["metrics"])
        self.assertEqual(len(data["match_history"]), 1)
        self.assertIn("Level", data["badge"] or "")