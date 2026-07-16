
from django.contrib import admin
from .models import GameAccount, DailySnapshot


@admin.register(GameAccount)
class GameAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "external_id", "verified", "created_at")
    list_filter = ("platform", "verified")
    search_fields = ("external_id", "user__username")


@admin.register(DailySnapshot)
class DailySnapshotAdmin(admin.ModelAdmin):
    list_display = ("game_account", "game_name", "playtime_forever", "date")
    list_filter = ("date",)
    search_fields = ("game_name",)