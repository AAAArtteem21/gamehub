from django.conf import settings
from django.db import models
from django.db.models import Q


class UserPresence(models.Model):
    STATUS_CHOICES = [
        ("offline", "Offline"),
        ("free", "Free"),
        ("ranked", "Ranked"),
        ("lfg", "LFG"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="presence"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="offline")
    note = models.CharField(max_length=100, blank=True, default="")
    game = models.CharField(max_length=50, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} — {self.status}"


class Friendship(models.Model):
    user_low = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_low",
    )
    user_high = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_high",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_low", "user_high"], name="unique_friendship_pair"
            )
        ]

    def save(self, *args, **kwargs):
        if self.user_low_id and self.user_high_id and self.user_low_id > self.user_high_id:
            self.user_low_id, self.user_high_id = self.user_high_id, self.user_low_id
        super().save(*args, **kwargs)

    @classmethod
    def between(cls, a, b):
        low, high = (a, b) if a.id < b.id else (b, a)
        return cls.objects.filter(user_low=low, user_high=high).first()

    @classmethod
    def for_user(cls, user):
        return cls.objects.filter(Q(user_low=user) | Q(user_high=user))

    def __str__(self):
        return f"{self.user_low} ↔ {self.user_high}"


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friend_requests_sent",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friend_requests_received",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    message = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                condition=Q(status="pending"),
                name="unique_pending_friend_request",
            )
        ]

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"


class Acquaintance(models.Model):

    SOURCE_CHOICES = [("lfg", "LFG")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acquaintances",
    )
    other = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acquaintance_of",
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="lfg")
    lfg_post = models.ForeignKey(
        "lfg.LFGPost",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "other")

    def __str__(self):
        return f"{self.user} ~ {self.other} ({self.source})"