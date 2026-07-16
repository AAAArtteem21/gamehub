import os 
from celery import Celery
from celery.schedules import crontab 

os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')

app = Celery('gamehub')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'sync-game-accounts-daily': {
        'task': 'apps.profiles.tasks.sync_all_game_accounts',
        'schedule': crontab(hour=0, minute=0),
    },
}