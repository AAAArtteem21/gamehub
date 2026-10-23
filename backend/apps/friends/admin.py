from django.contrib import admin

from .models import Acquaintance, FriendRequest, Friendship, UserPresence


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "game", "note", "updated_at")
    list_filter = ("status",)
    search_fields = ("userusername", "game", "note")
    raw_id_fields = ("user",)


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("id", "user_low", "user_high", "created_at")
    search_fields = ("user_lowusername", "user_highusername")
    raw_id_fields = ("user_low", "user_high")


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "from_user", "to_user", "status", "created_at", "decided_at")
    list_filter = ("status",)
    search_fields = ("from_userusername", "to_userusername", "message")
    raw_id_fields = ("from_user", "to_user")


@admin.register(Acquaintance)
class AcquaintanceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "other", "source", "lfg_post", "created_at")
    list_filter = ("source",)
    search_fields = ("userusername", "other__username")
    raw_id_fields = ("user", "other", "lfg_post")