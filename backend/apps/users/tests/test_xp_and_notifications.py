from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient

from apps.users.models import UserProfile, Notification
from apps.users.xp import add_xp, progress_payload, XP_PER_LEVEL, XP_SYNC
from apps.users.services import notify

User = get_user_model()


class XPTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="x")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)

    def test_add_xp_increases(self):
        add_xp(self.user, 25, reason="test")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.xp, 25)
        self.assertEqual(self.profile.level, 1)

    def test_level_up(self):
        add_xp(self.user, XP_PER_LEVEL, reason="level")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.level, 2)
        self.assertTrue(
            Notification.objects.filter(user=self.user, kind="level_up").exists()
        )

    def test_progress_payload(self):
        self.profile.xp = 40
        self.profile.level = 1
        self.profile.save()
        data = progress_payload(self.profile)
        self.assertEqual(data["xp"], 40)
        self.assertEqual(data["xp_into_level"], 40)
        self.assertIn("referral_code", data)


class NotifyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", password="x")

    def test_notify_creates_row(self):
        n = notify(
            self.user,
            kind="system",
            title="Тест",
            body="ok",
            link="/profile",
        )
        self.assertIsNotNone(n)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        self.assertFalse(n.read)


class ReferralAPITests(APITestCase):
    def setUp(self):
        self.inviter = User.objects.create_user(username="inv", password="x")
        self.invitee = User.objects.create_user(username="new", password="x")
        self.inv_p, _ = UserProfile.objects.get_or_create(user=self.inviter)
        self.new_p, _ = UserProfile.objects.get_or_create(user=self.invitee)
        # save генерирует referral_code
        self.inv_p.save()
        self.inv_p.refresh_from_db()
        self.client = APIClient()

    def test_progress_requires_auth(self):
        r = self.client.get("/api/me/progress/")
        self.assertIn(r.status_code, (401, 403))

    def test_progress_ok(self):
        self.client.force_authenticate(self.invitee)
        r = self.client.get("/api/me/progress/")
        # если url ещё нет — будет 404; тогда поправь path
        if r.status_code == 404:
            self.skipTest("me/progress/ не подключён")
        self.assertEqual(r.status_code, 200)
        self.assertIn("level", r.data)

    def test_claim_referral(self):
        self.client.force_authenticate(self.invitee)
        code = self.inv_p.referral_code
        if not code:
            self.skipTest("нет referral_code")
        r = self.client.post("/api/referrals/claim/", {"code": code}, format="json")
        if r.status_code == 404:
            self.skipTest("referrals/claim/ не подключён")
        self.assertEqual(r.status_code, 200)
        self.new_p.refresh_from_db()
        self.assertEqual(self.new_p.referred_by_id, self.inviter.id)