from django.conf import settings
from django.db import models

class MatchAnalysis(models.Model):
    class Platform(models.TextChoices):
        FACEIT = "faceit", "Faceit"
        OPENDOTA = "opendota", "OpenDota"
        DEADLOCK = "deadlock", "Deadlock"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="match_analyses",
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    game = models.CharField(max_length=40, blank=True, default="")
    external_match_id = models.CharField(max_length=128)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    input_snapshot = models.JSONField(default=dict, blank=True)
    report_json = models.JSONField(default=dict, blank=True)

    model_name = models.CharField(max_length=80, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["platform", "external_match_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "platform", "external_match_id"],
                name="uniq_user_platform_match_analysis",
            )
        ]

    def __str__(self):
        return f"{self.platform}:{self.external_match_id} [{self.status}]"


class PlayerPerformanceSnapshot(models.Model):
    """Опционально: снимок формы за последние N матчей (без AI)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="performance_snapshots",
    )
    platform = models.CharField(max_length=20, choices=MatchAnalysis.Platform.choices)
    game = models.CharField(max_length=40, blank=True, default="")
    window_size = models.PositiveSmallIntegerField(default=20)
    stats = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "platform", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} {self.platform} n={self.window_size}"