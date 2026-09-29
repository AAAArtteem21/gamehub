from django.contrib import admin
from .models import GameAccount, DailySnapshot

# FavoritePlayer / ClanActivity если в profiles — раскомментируй
try:
    from .models import FavoritePlayer
except ImportError:
    FavoritePlayer = None


@admin.register(GameAccount)
class GameAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "platform", "nickname", "external_id",
        "verified", "skill_rating", "last_synced_at", "created_at",
    )
    list_filter = ("platform", "verified")
    search_fields = ("user__username", "nickname", "external_id")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "last_synced_at")


@admin.register(DailySnapshot)
class DailySnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "game_account", "date", "appid", "game_name", "playtime_forever")
    list_filter = ("date",)
    search_fields = ("game_name", "game_account__user__username")
    raw_id_fields = ("game_account",)


if FavoritePlayer is not None:
    @admin.register(FavoritePlayer)
    class FavoritePlayerAdmin(admin.ModelAdmin):
        list_display = (
            "id",
            "owner",
            "target_user",
            "platform",
            "external_id",
            "display_name",
            "created_at",
        )
        list_filter = ("platform", "created_at")
        search_fields = (
            "display_name",
            "external_id",
            "owner__username",
            "target_user__username",
        )
        raw_id_fields = ("owner", "target_user")
        readonly_fields = ("created_at",)