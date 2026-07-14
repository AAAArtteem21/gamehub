from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user','steam_id','display_name','created_at']
    search_fields = ['user__username','steam_id','display_name']

