from django.db import models

from django.db import models
from django.conf import settings


class GameAccount(models.Model):
    PLATFORM_CHOICES = [
        ("steam", "Steam"),
        ("faceit", "Faceit"),
        ("opendota", "OpenDota"),
        ("manual", "Manual"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="game_accounts"
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    external_id = models.CharField(max_length=100)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} — {self.platform}"


class DailySnapshot(models.Model):
    game_account = models.ForeignKey(
        GameAccount,
        on_delete=models.CASCADE,
        related_name="snapshots"
    )
    playtime_forever = models.IntegerField(help_text="в минутах")
    date = models.DateField()

    class Meta:
        unique_together = ("game_account", "date")

    def __str__(self):
        return f"{self.game_account} — {self.date}"