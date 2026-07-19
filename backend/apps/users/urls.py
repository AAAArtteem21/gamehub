from django.urls import path 
from .views  import MeView,LogoutView,SteamAuthCompleteView,SteamAuthErrorView,get_csrf_token


urlpatterns = [
    path('me/',MeView.as_view()),
    path('logout/',LogoutView.as_view()),
    path('auth/steam/complete/',SteamAuthCompleteView.as_view()),
    path('auth/steam/error',SteamAuthErrorView.as_view()),
    path('csrf/', get_csrf_token),
    
]