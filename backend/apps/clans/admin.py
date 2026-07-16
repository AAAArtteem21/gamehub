from django.contrib import admin
from .models import Clan, ClanMembership


class ClanMembershipInline(admin.TabularInline):
    model = ClanMembership
    extra = 0


@admin.register(Clan)
class ClanAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "invite_code", "created_at")
    search_fields = ("name", "owner__username")
    inlines = [ClanMembershipInline]


@admin.register(ClanMembership)
class ClanMembershipAdmin(admin.ModelAdmin):
    list_display = ("clan", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("clan__name", "user__username")