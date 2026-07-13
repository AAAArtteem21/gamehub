from django.contrib import admin

from .models import GameAccount,DailySnapshot

admin.site.register(GameAccount)
admin.site.register(DailySnapshot)
