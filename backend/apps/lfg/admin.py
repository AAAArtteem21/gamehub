from django.contrib import admin
from .models import LFGPost, LFGResponse, LFGChatMessage, ContactReveal


@admin.register(LFGPost)
class LFGPostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "game", "status", "slots_needed", "datetime", "created_at")
    list_filter = ("status", "game")
    search_fields = ("author__username", "game", "description")
    raw_id_fields = ("author",)


@admin.register(LFGResponse)
class LFGResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    search_fields = ("user__username", "post__game")
    raw_id_fields = ("post", "user")


@admin.register(LFGChatMessage)
class LFGChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "sender", "text", "created_at")
    search_fields = ("sender__username", "text")
    raw_id_fields = ("post", "sender")


@admin.register(ContactReveal)
class ContactRevealAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "post", "expires_at", "revealed_at")
    raw_id_fields = ("user", "post")