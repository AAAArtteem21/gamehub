
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/',include('apps.lfg.urls')),
    path('api/',include('apps.profiles.urls')),
    # path('api/',include('apps.clans.urls')),
]
