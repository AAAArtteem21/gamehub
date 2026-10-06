
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from apps.users.views import health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/',include('social_django.urls',namespace='social')),
    path('api/',include('apps.users.urls')),
    path('api/',include('apps.lfg.urls')),
    path('api/',include('apps.profiles.urls')),
    path('api/',include('apps.clans.urls')),
    path("health/", health),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)    