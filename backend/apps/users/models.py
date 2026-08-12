from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    user= models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='profile')
    avatar_url = models.URLField(blank=True,null=True)
    steam_id = models.CharField(max_length=32,blank=True,null=True,unique=True)
    display_name = models.CharField(max_length=100,blank=True)
    bio = models.TextField(blank=True,max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user}"
    
class ProfileView(models.Model):
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="views_made")
    viewed_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="views_received")
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["viewed_user", "viewed_at"])]