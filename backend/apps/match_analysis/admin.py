from django.contrib import admin
from .models import MatchAnalysis, PlayerPerformanceSnapshot


@admin.register(MatchAnalysis)
class MatchAnalystAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "platform",
        "game",
        "external_match_id",
        "status",
        "model_name",
        "created_at",
        "finished_at",
    )
    list_filter = ("platform", "status", "game")
    search_fields = ("user__username", "external_match_id")
    readonly_fields = ("created_at", "finished_at", "input_snapshot", "report_json")


@admin.register(PlayerPerformanceSnapshot)
class PlayerPerfomanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "platform", "game", "window_size", "created_at")
    list_filter = ("platform", "game")
    search_fields = ("user__username",)
