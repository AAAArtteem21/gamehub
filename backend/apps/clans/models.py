import uuid
from django.conf import settings
from django.db import models


class Clan(models.Model):
    GAME_DOTA2 = "dota2"
    GAME_VALORANT = "valorant"
    GAME_CS2 = "cs2"
    GAME_DEADLOCK = "deadlock"
    GAME_LOL = "lol"
    GAME_MULTI = "multi"
    GAME_CHOICES = [
        (GAME_DOTA2, "Dota 2"),
        (GAME_VALORANT, "Valorant"),
        (GAME_CS2, "CS2"),
        (GAME_DEADLOCK, "Deadlock"),
        (GAME_LOL, "League of Legends"),
        (GAME_MULTI, "Мультигейминг"),
    ]

    name = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_clans",
    )
    logo = models.ImageField(upload_to="clan_logos/", blank=True, null=True)
    description = models.TextField(blank=True)
    is_open = models.BooleanField(default=True)
    game = models.CharField(max_length=32, choices=GAME_CHOICES, default=GAME_MULTI)
    max_members = models.PositiveIntegerField(null=True, blank=True)
    min_playtime_hours = models.PositiveIntegerField(null=True, blank=True)
    join_requirements = models.CharField(max_length=500, blank=True, default="")
    invite_code = models.CharField(max_length=8, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Клан"
        verbose_name_plural = "Кланы"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ClanMembership(models.Model):
    ROLE_LEADER = "leader"
    ROLE_OFFICER = "officer"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [
        (ROLE_LEADER, "Лидер"),
        (ROLE_OFFICER, "Офицер"),
        (ROLE_MEMBER, "Участник"),
    ]

    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clan_memberships",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("clan", "user")]
        ordering = ["role", "joined_at"]

    def __str__(self):
        return f"{self.user_id} @ {self.clan_id} ({self.role})"


class ClanMessage(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clan_messages",
    )
    text = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ClanBan(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="bans")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clan_bans",
    )
    banned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clan_bans_made",
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["clan", "user"], name="uniq_clan_ban_user"),
        ]
        ordering = ["-created_at"]


class ClanModerationLog(models.Model):
    ACTION_KICK = "kick"
    ACTION_BAN = "ban"
    ACTION_UNBAN = "unban"
    ACTION_CHOICES = [
        (ACTION_KICK, "Kick"),
        (ACTION_BAN, "Ban"),
        (ACTION_UNBAN, "Unban"),
    ]

    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="mod_logs")
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clan_mod_actions",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clan_mod_targets",
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]