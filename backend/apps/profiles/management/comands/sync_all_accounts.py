
from django.core.management.base import BaseCommand
from apps.profiles.models import GameAccount
from apps.profiles.serivces import ProfileSyncService


class Command(BaseCommand):
    help = "Синхронизирует все подключённые игровые аккаунты — запускать раз в день через Windows Task Scheduler"

    def handle(self, *args, **options):
        accounts = GameAccount.objects.all()
        success, failed = 0, 0
        for acc in accounts:
            try:
                ProfileSyncService(acc).sync()
                success += 1
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.WARNING(f"Не удалось синхронизировать {acc}: {e}"))
        self.stdout.write(self.style.SUCCESS(f"Готово: {success} успешно, {failed} с ошибками"))