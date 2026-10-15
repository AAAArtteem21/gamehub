import uuid

from django.conf import settings
from django.db import models


class Clan(models.Model):
    GAME_DOTA = "dota2"
    GAME_VAL = "valorant"
    GAME_CS = "cs2"
    GAME_LOL = "lol"
    GAME_DEADLOCK = "deadlock"
    GAME_MULTI = "multigaming"
    GAME_OTHER = "other"

    GAME_CHOICES = [
        (GAME_DOTA, "Dota 2"),
        (GAME_VAL, "Valorant"),
        (GAME_CS, "CS2 / Faceit"),
        (GAME_LOL, "League of Legends"),
        (GAME_DEADLOCK, "Deadlock"),
        (GAME_MULTI, "Мультигейминг"),
        (GAME_OTHER, "Другое"),
    ]

    name = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_clans",
    )
    logo = models.ImageField(upload_to="clan_logos/", blank=True, null=True)
    description = models.TextField(blank=True)

    is_open = models.BooleanField(
        default=True,
        help_text="Открытый — вступить можно без кода (если проходят лимит/часы). Закрытый — только по коду.",
    )
    game = models.CharField(
        max_length=32,
        choices=GAME_CHOICES,
        default=GAME_MULTI,
    )
    max_members = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="None = без лимита",
    )
    # Часы входа 0–23, UTC или локаль сервера; оба None = круглосуточно
    join_hours_start = models.PositiveSmallIntegerField(null=True, blank=True)
    join_hours_end = models.PositiveSmallIntegerField(null=True, blank=True)
    join_requirements = models.TextField(
        blank=True,
        max_length=500,
        help_text="Текст требований для входа (видят все)",
    )

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

    @property
    def members_count(self):
        return self.memberships.count()


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
        verbose_name = "Участник клана"
        verbose_name_plural = "Участники клана"
        unique_together = ("clan", "user")
        indexes = [models.Index(fields=["clan", "role"])]
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user} - {self.clan} ({self.role})"


class ClanMessage(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clan_messages",
    )
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.clan_id}:{self.sender_id}:{self.text[:30]}"