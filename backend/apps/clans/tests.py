from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Clan, ClanMembership
from .services import join_clan_by_invite_code

User = get_user_model()


class ClanTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.member = User.objects.create_user(username="member", password="pass")
        self.clan = Clan.objects.create(name="Test Clan", owner=self.owner)
        ClanMembership.objects.create(clan=self.clan, user=self.owner, role="leader")

    def test_invite_code_generated(self):
        self.assertTrue(self.clan.invite_code)
        self.assertEqual(len(self.clan.invite_code), 8)

    def test_join_by_invite_code(self):
        membership = join_clan_by_invite_code(self.member, self.clan.invite_code)
        self.assertEqual(membership.role, "member")

    def test_cannot_join_twice(self):
        join_clan_by_invite_code(self.member, self.clan.invite_code)
        with self.assertRaises(ValueError):
            join_clan_by_invite_code(self.member, self.clan.invite_code)

    def test_invalid_invite_code(self):
        with self.assertRaises(ValueError):
            join_clan_by_invite_code(self.member, "wrongcode")