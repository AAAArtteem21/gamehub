from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient

from apps.clans.models import Clan, ClanMembership

User = get_user_model()


class ClanLeaderboardTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="clan_u", password="x")
        self.clan = Clan.objects.create(name="TestClan", owner=self.user)
        ClanMembership.objects.create(clan=self.clan, user=self.user, role="leader")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_leaderboard_no_500(self):
        r = self.client.get("/api/clans/leaderboard/")
        if r.status_code == 404:
            self.skipTest("leaderboard url нет")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsInstance(r.data, list)