from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import UserProfile


API_PREFIX = "/api"  # если urls подключены через /api/users/, поставь "/api/users"


def api_url(path):
    return f"{API_PREFIX}{path}"


class UserProfileTests(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

    def auth(self):
        self.client.force_authenticate(user=self.user)

    def test_me_requires_authentication(self):
        response = self.client.get(api_url("/me/"))

        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_me_get_creates_profile(self):
        self.auth()

        response = self.client.get(api_url("/me/"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())
        self.assertEqual(response.data["username"], self.user.username)

    def test_me_patch_updates_profile(self):
        self.auth()

        response = self.client.patch(
            api_url("/me/"),
            {
                "display_name": "New Name",
                "bio": "Hello world",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.display_name, "New Name")
        self.assertEqual(profile.bio, "Hello world")

    def test_me_patch_rejects_short_display_name(self):
        self.auth()

        response = self.client.patch(
            api_url("/me/"),
            {"display_name": "a"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("display_name", response.data)

    def test_me_patch_rejects_long_bio(self):
        self.auth()

        response = self.client.patch(
            api_url("/me/"),
            {"bio": "x" * 301},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bio", response.data)

    def test_read_only_fields_are_not_updated(self):
        self.auth()

        profile = UserProfile.objects.create(
            user=self.user,
            steam_id="12345",
            avatar_url="https://example.com/avatar.png",
        )

        response = self.client.patch(
            api_url("/me/"),
            {
                "steam_id": "99999",
                "avatar_url": "https://example.com/new.png",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profile.refresh_from_db()
        self.assertEqual(profile.steam_id, "12345")
        self.assertEqual(profile.avatar_url, "https://example.com/avatar.png")

    def test_logout_deletes_token(self):
        self.auth()
        Token.objects.create(user=self.user)

        response = self.client.post(api_url("/logout/"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertEqual(response.data["detail"], "Вы успешно вышли из аккаунта")

    def test_steam_auth_complete_creates_token_and_redirects(self):
        self.auth()

        response = self.client.get(api_url("/auth/steam/complete"))

        token = Token.objects.get(user=self.user)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn(
            f"http://localhost:5173/auth/callback?token={token.key}",
            response["Location"],
        )

    def test_steam_auth_error_returns_400(self):
        response = self.client.get(api_url("/auth/steam/error"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Не удалось найти аккаунт стим попробуйте позже",
        )