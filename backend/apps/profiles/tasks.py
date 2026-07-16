from celery import shared_task
from django.core.cache import cache

from .models import GameAccount
from .serivces import ProfileSyncService,SyncError

@shared_task
def sync_all_game_accounts():
    for account in GameAccount.objects.all():
        try:
            ProfileSyncService(account).sync()
            cache.delete(f'game_accounts:{account.user_id}')
        except SyncError:
            continue
        except Exception:
            continue

@shared_task
def sync_single_account(account_id):
    try:
        account = GameAccount.objects.get(id=account_id)
        ProfileSyncService(account).sync()
        cache.delete(f'game_accounts:{account.user_id}')
    except GameAccount.DoesNotExist:
        pass 
    except SyncError:
        pass