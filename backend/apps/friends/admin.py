from django.contrib import admin
from .models import UserPresence, Friendship, FriendRequest, Acquaintance


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "game", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__username",)


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("user_low", "user_high", "created_at")
    search_fields = ("user_low__username", "user_high__username")


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at", "decided_at")
    list_filter = ("status",)
    search_fields = ("from_user__username", "to_user__username")


@admin.register(Acquaintance)
class AcquaintanceAdmin(admin.ModelAdmin):
    list_display = ("user", "other", "source", "lfg_post_id", "created_at")
    list_filter = ("source",)
    search_fields = ("user__username", "other__username")
