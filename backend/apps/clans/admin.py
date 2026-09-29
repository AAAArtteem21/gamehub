from django.contrib import admin
from .models import Clan, ClanMembership

# если модели есть в profiles — поправь импорты
try:
    from apps.profiles.models import ClanActivity, ClanMessage
except ImportError:
    ClanActivity = None
    ClanMessage = None


@admin.register(Clan)
class ClanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "invite_code", "created_at")
    search_fields = ("name", "invite_code", "owner__username")
    raw_id_fields = ("owner",)
    readonly_fields = ("invite_code", "created_at")


@admin.register(ClanMembership)
class ClanMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "clan", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("clan__name", "user__username")
    raw_id_fields = ("clan", "user")


if ClanActivity is not None:
    @admin.register(ClanActivity)
    class ClanActivityAdmin(admin.ModelAdmin):
        list_display = ("id", "clan", "user", "kind", "text", "created_at")
        list_filter = ("kind",)
        search_fields = ("clan__name", "user__username", "text")
        raw_id_fields = ("clan", "user")


if ClanMessage is not None:
    @admin.register(ClanMessage)
    class ClanMessageAdmin(admin.ModelAdmin):
        list_display = ("id", "clan", "sender", "text", "created_at")
        search_fields = ("clan__name", "sender__username", "text")
        raw_id_fields = ("clan", "sender")