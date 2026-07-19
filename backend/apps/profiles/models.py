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
    last_synced_at = models.DateTimeField(null=True,blank=True)
    nickname = models.CharField(max_length=100, blank=True)
    avatar = models.URLField(blank=True)
    skill_rating = models.IntegerField(null=True, blank=True, help_text="ELO/MMR — если платформа его даёт")
    game_label = models.CharField(max_length=50, blank=True, help_text="Человекочитаемое название игры для лидерборда")
    extra_stats = models.JSONField(null=True, blank=True, help_text="Доп. статистика: winrate, топ герои и т.д.")

    class Meta:
        unique_together = ("platform", "external_id")

    def __str__(self):
        return f"{self.user} — {self.platform}"


class DailySnapshot(models.Model):
    game_account = models.ForeignKey(
        GameAccount,
        on_delete=models.CASCADE,
        related_name="snapshots"
    )
    appid = models.IntegerField()
    game_name = models.CharField(max_length=100)
    playtime_forever = models.IntegerField(help_text="в минутах, общее время на момент снимка")
    date = models.DateField()

    class Meta:
        unique_together = ("game_account", "appid", "date")
        indexes = [
            models.Index(fields=["game_account", "date"]),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.game_account} — {self.game_name} ({self.date})"