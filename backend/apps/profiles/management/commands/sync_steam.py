from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.profiles.models import GameAccount
from apps.profiles.services import ProfileSyncService


class Command(BaseCommand):
    help = "Sync all Steam accounts (updates playtime_forever / playtime_2weeks)"

    def handle(self, *args, **options):
        for acc in GameAccount.objects.filter(platform="steam"):
            try:
                ProfileSyncService(acc).sync()
                cache.delete(f"game_accounts:{acc.user_id}")
                self.stdout.write(f"account={acc.id} ok")
            except Exception as e:
                self.stderr.write(f"account={acc.id} failed: {e}")
        self.stdout.write(self.style.SUCCESS("done"))