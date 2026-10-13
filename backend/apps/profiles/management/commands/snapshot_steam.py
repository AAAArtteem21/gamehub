from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.profiles.models import GameAccount
from apps.profiles.snapshots import snapshot_steam_account


class Command(BaseCommand):
    help = "Daily Steam snapshots for all verified accounts"

    def handle(self, *args, **options):
        for acc in GameAccount.objects.filter(platform="steam", verified=True):
            try:
                n = snapshot_steam_account(acc)
                cache.delete(f"game_accounts:{acc.user_id}")
                self.stdout.write(f"account={acc.id} games={n}")
            except Exception as e:
                self.stderr.write(f"account={acc.id} failed: {e}")
        self.stdout.write(self.style.SUCCESS("done"))