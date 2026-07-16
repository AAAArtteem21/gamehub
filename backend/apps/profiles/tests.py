from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from .models import GameAccount, DailySnapshot
from .serivces import get_daily_playtime

User = get_user_model()

class ProfilesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="pass")

    def test_daily_playtime(self):
        acc = GameAccount.objects.create(user=self.user, platform="steam", external_id="76561198000000001")
        DailySnapshot.objects.create(game_account=acc, appid=730, game_name="CS2", playtime_forever=100, date=date.today()-timedelta(days=1))
        DailySnapshot.objects.create(game_account=acc, appid=730, game_name="CS2", playtime_forever=160, date=date.today())
        self.assertEqual(get_daily_playtime(acc, 730, date.today()), 60)