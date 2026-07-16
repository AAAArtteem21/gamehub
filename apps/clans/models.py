from django.conf import settings

import uuid

from django.db import models

from django.contrib.auth.models import User

class Clan(models.Model):
    name = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_clan')
    logo = models.ImageField(upload_to='clan_logos/', blank=True, null=True)
    description = models.TextField(blank=True)
    invite_code = models.CharField(max_length=8, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Meta:
    verbose_name = 'Клан'
    verbose_name_plural = 'Кланы'
    ordering = ['-created_at']

def save(self, *args, **kwargs):
    if not self.invite.code:
        self.invite_code = uuid.uuid4(),hex[:10].upper()
    super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ClanMembership(models.Model):
    ROLE_LEADER = 'leader'
    ROLE_OFFICER = 'officer'
    ROLE_MEMBER = 'member'

    ROLE_CHOICES = [
        (ROLE_LEADER, 'Лидер'),
        (ROLE_OFFICER, 'Офицер'),
        (ROLE_MEMBER, 'Участник'),
    ]

    clan = models.ForeignKey(
        'Clan',
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clan_memberships'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_MEMBER
    )

    class Meta:
        verbose_name = 'Участник клана'
        verbose_name_plural = 'Участники клана'
        unique_together = ('clan', 'user')
        ordering = ['joined_at']

        def __str__(self):
            return f'{self.user} - {self.clan} ({self.get_role_display()})'
