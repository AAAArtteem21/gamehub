from collections import defaultdict

from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.profiles.models import GameAccount, DailySnapshot


class Command(BaseCommand):
    help = "Склеивает дубли Steam GameAccount и переносит DailySnapshot на primary"

    def handle(self, *args, **options):
        by_user = defaultdict(list)
        for a in GameAccount.objects.filter(platform="steam").order_by("id"):
            by_user[a.user_id].append(a)

        for uid, steam_accs in by_user.items():
            if len(steam_accs) == 1:
                a = steam_accs[0]
                n = DailySnapshot.objects.filter(game_account=a).count()
                self.stdout.write(f"user={uid} steam={a.id} snaps={n} (ok)")
                continue

            primary = max(
                steam_accs,
                key=lambda a: DailySnapshot.objects.filter(game_account=a).count(),
            )
            self.stdout.write(f"user={uid} primary={primary.id} of {len(steam_accs)}")

            for a in steam_accs:
                if a.id == primary.id:
                    continue
                for s in list(DailySnapshot.objects.filter(game_account=a)):
                    exists = DailySnapshot.objects.filter(
                        game_account=primary, appid=s.appid, date=s.date
                    ).exists()
                    if exists:
                        s.delete()
                    else:
                        DailySnapshot.objects.filter(pk=s.pk).update(
                            game_account_id=primary.id
                        )
                self.stdout.write(f"  deleted steam {a.id}")
                a.delete()

            cache.delete(f"game_accounts:{uid}")
            n = DailySnapshot.objects.filter(game_account=primary).count()
            dates = list(
                DailySnapshot.objects.filter(game_account=primary)
                .values_list("date", flat=True)
                .distinct()
                .order_by("date")
            )
            self.stdout.write(f"  result snaps={n} dates={dates}")

        self.stdout.write(self.style.SUCCESS("done"))
