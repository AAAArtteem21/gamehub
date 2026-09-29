from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings

from apps.profiles.integrations.faceit_client import FaceitClient, FaceitError


@override_settings(FACEIT_API_KEY="test-key-not-placeholder")
class FaceitClientTests(TestCase):
    def test_missing_key_raises(self):
        with override_settings(FACEIT_API_KEY=""):
            with self.assertRaises(FaceitError):
                FaceitClient()

    @patch("apps.profiles.integrations.faceit_client.requests.Session.get")
    def test_get_player_by_nickname(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "player_id": "abc-123",
            "nickname": "tester",
            "games": {"cs2": {"skill_level": 7, "faceit_elo": 1800}},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        c = FaceitClient()
        data = c.get_player_by_nickname("tester")
        self.assertEqual(data["player_id"], "abc-123")
        mock_get.assert_called()

    @patch("apps.profiles.integrations.faceit_client.requests.Session.get")
    def test_401(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp
        c = FaceitClient()
        with self.assertRaises(FaceitError):
            c.get_player_by_nickname("x")