from django.db import models
from django.conf import settings
import secrets


def _gen_ref_code():
    return secrets.token_hex(4).upper()


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    avatar_url = models.URLField(blank=True, null=True)
    steam_id = models.CharField(max_length=32, blank=True, null=True, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True, max_length=300)

    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    boost_credits = models.PositiveIntegerField(default=0)
    tags = models.JSONField(default=list, blank=True)

    referral_code = models.CharField(
        max_length=16,
        unique=True,
        null=True,
        blank=True,
        default=None,
    )
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals_made",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            for _ in range(20):
                code = _gen_ref_code()
                qs = UserProfile.objects.filter(referral_code=code)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                if not qs.exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile of {self.user}"


class ProfileView(models.Model):
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="views_made",
    )
    viewed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="views_received",
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["viewed_user", "viewed_at"])]

    def __str__(self):
        return f"{self.viewer_id} → {self.viewed_user_id}"


class Notification(models.Model):
    class Kind(models.TextChoices):
        LFG_RESPONSE = "lfg_response", "LFG response"
        CLAN_JOIN = "clan_join", "Clan join"
        CLAN_MESSAGE = "clan_message", "Clan message"
        FAVORITE_LFG = "favorite_lfg", "Favorite LFG"
        WEEKLY = "weekly", "Weekly report"
        SYSTEM = "system", "System"
        REFERRAL = "referral", "Referral"
        LEVEL_UP = "level_up", "Level up"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices, default=Kind.SYSTEM)
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=280, blank=True)
    link = models.CharField(max_length=255, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id}: {self.title}"