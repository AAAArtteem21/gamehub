from django.db import models
from django.conf import settings
from django.utils import timezone as dj_timezone
from datetime import timedelta


class LFGPost(models.Model):
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lfg_posts")
    game = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    description = models.TextField(blank=True)
    contact = models.CharField(max_length=100)
    slots_needed = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.game} — {self.author}"


class LFGResponse(models.Model):
    post = models.ForeignKey(LFGPost, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")


class LFGChatMessage(models.Model):
    post = models.ForeignKey(LFGPost, on_delete=models.CASCADE, related_name="chat_messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

class ContactReveal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="revealed_contacts")
    post = models.ForeignKey(LFGPost, on_delete=models.CASCADE, related_name="reveals")
    contact = models.CharField(max_length=100)
    revealed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        unique_together = ("user", "post")

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = dj_timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return dj_timezone.now() > self.expires_at