from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import UserProfile, ProfileView, Notification
from .xp import add_xp

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = "user"
    extra = 0
    readonly_fields = ("referral_code", "created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": (
                "display_name",
                "avatar_url",
                "steam_id",
                "bio",
            )
        }),
        ("GameHub прогресс", {
            "fields": (
                "xp",
                "level",
                "boost_credits",
                "tags",
                "referral_code",
                "referred_by",
            )
        }),
        ("Служебное", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [UserProfileInline]
    list_display = ("id", "username", "email", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("username", "email")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "display_name",
        "level",
        "xp",
        "boost_credits",
        "referral_code",
        "referred_by",
        "steam_id",
        "updated_at",
    )
    list_filter = ("level",)
    search_fields = (
        "user__username",
        "display_name",
        "steam_id",
        "referral_code",
    )
    raw_id_fields = ("user", "referred_by")
    readonly_fields = ("referral_code", "created_at", "updated_at")
    actions = ("give_100_xp", "give_1_boost", "regenerate_referral_code")

    @admin.action(description="Выдать +100 XP")
    def give_100_xp(self, request, queryset):
        for p in queryset.select_related("user"):
            add_xp(p.user, 100, reason="admin")
        self.message_user(request, f"XP начислен: {queryset.count()} профилей")

    @admin.action(description="Выдать +1 boost")
    def give_1_boost(self, request, queryset):
        for p in queryset:
            p.boost_credits = (p.boost_credits or 0) + 1
            p.save(update_fields=["boost_credits"])
        self.message_user(request, f"Бусты выданы: {queryset.count()}")

    @admin.action(description="Сгенерировать referral_code заново")
    def regenerate_referral_code(self, request, queryset):
        for p in queryset:
            p.referral_code = None
            p.save()
        self.message_user(request, f"Коды обновлены: {queryset.count()}")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "kind", "title", "read", "created_at")
    list_filter = ("kind", "read", "created_at")
    search_fields = ("user__username", "title", "body")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at",)
    actions = ("mark_read", "mark_unread")

    @admin.action(description="Пометить прочитанными")
    def mark_read(self, request, queryset):
        n = queryset.update(read=True)
        self.message_user(request, f"Прочитано: {n}")

    @admin.action(description="Пометить непрочитанными")
    def mark_unread(self, request, queryset):
        n = queryset.update(read=False)
        self.message_user(request, f"Непрочитано: {n}")


@admin.register(ProfileView)
class ProfileViewAdmin(admin.ModelAdmin):
    list_display = ("id", "viewer", "viewed_user", "viewed_at")
    list_filter = ("viewed_at",)
    search_fields = ("viewer__username", "viewed_user__username")
    raw_id_fields = ("viewer", "viewed_user")
    readonly_fields = ("viewed_at",)