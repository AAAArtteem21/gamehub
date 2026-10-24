from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class PlayStatus:
    OFFLINE = "offline"
    FREE = "free"
    RANKED = "ranked"
    LFG = "lfg"

    CHOICES = [
        (OFFLINE, "Не в сети"),
        (FREE, "Свободен"),
        (RANKED, "Играю рейтинг"),
        (LFG, "Ищу команду"),
    ]


class UserPresence(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="presence",
    )
    status = models.CharField(
        max_length=20,
        choices=PlayStatus.CHOICES,
        default=PlayStatus.OFFLINE,
    )
    note = models.CharField(max_length=80, blank=True, default="")
    game = models.CharField(max_length=50, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id}: {self.status}"


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
        unique_together = ("user_low", "user_high")
        indexes = [
            models.Index(fields=["user_low"]),
            models.Index(fields=["user_high"]),
        ]

    @staticmethod
    def pair(u1_id: int, u2_id: int):
        return (u1_id, u2_id) if u1_id < u2_id else (u2_id, u1_id)

    @classmethod
    def are_friends(cls, u1_id: int, u2_id: int) -> bool:
        if u1_id == u2_id:
            return False
        a, b = cls.pair(u1_id, u2_id)
        return cls.objects.filter(user_low_id=a, user_high_id=b).exists()

    @classmethod
    def friend_ids_of(cls, user_id: int):
        qs = cls.objects.filter(Q(user_low_id=user_id) | Q(user_high_id=user_id))
        ids = set()
        for f in qs.only("user_low_id", "user_high_id"):
            ids.add(f.user_high_id if f.user_low_id == user_id else f.user_low_id)
        return ids


class FriendRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELLED, "Cancelled"),
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
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    message = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["to_user", "status"]),
            models.Index(fields=["from_user", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                condition=Q(status="pending"),
                name="uniq_pending_friend_request",
            )
        ]

    def accept(self):
        if self.status != self.STATUS_PENDING:
            return False
        a, b = Friendship.pair(self.from_user_id, self.to_user_id)
        Friendship.objects.get_or_create(user_low_id=a, user_high_id=b)
        self.status = self.STATUS_ACCEPTED
        self.decided_at = timezone.now()
        self.save(update_fields=["status", "decided_at"])
        FriendRequest.objects.filter(
            from_user_id=self.to_user_id,
            to_user_id=self.from_user_id,
            status=self.STATUS_PENDING,
        ).update(status=self.STATUS_CANCELLED, decided_at=timezone.now())
        return True


class Acquaintance(models.Model):
    SOURCE_LFG = "lfg"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acquaintances",
    )
    other = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acquainted_by",
    )
    source = models.CharField(max_length=20, default=SOURCE_LFG)
    lfg_post_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "other")
        indexes = [models.Index(fields=["user", "-created_at"])]

    @classmethod
    def link_from_lfg(cls, user_a_id: int, user_b_id: int, post_id=None):
        if user_a_id == user_b_id:
            return
        for u, o in ((user_a_id, user_b_id), (user_b_id, user_a_id)):
            cls.objects.get_or_create(
                user_id=u,
                other_id=o,
                defaults={"source": cls.SOURCE_LFG, "lfg_post_id": post_id},
            )
