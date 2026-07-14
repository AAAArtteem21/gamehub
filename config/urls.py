
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/',include('social_django.urls',namespace='social')),
    path('api/',include('apps.users.urls')),
    path('api/',include('apps.lfg.urls')),
    path('api/',include('apps.profiles.urls')),
    # path('api/',include('apps.clans.urls')),
]
