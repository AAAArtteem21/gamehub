from django.urls import path
from .views import (
    MeView, LogoutView, SteamAuthCompleteView, SteamAuthErrorView,
    get_csrf_token, PlayerSearchView, NotificationListView, NotificationReadView,
    ProgressView, ReferralClaimView, steam_start
)

urlpatterns = [
    path("me/", MeView.as_view()),
    path("me/progress/", ProgressView.as_view()),
    path("referrals/claim/", ReferralClaimView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("auth/steam/complete/", SteamAuthCompleteView.as_view()),
    path("auth/steam/error", SteamAuthErrorView.as_view()),
    path("csrf/", get_csrf_token),
    path("players/search/", PlayerSearchView.as_view()),
    path("notifications/", NotificationListView.as_view()),
    path("notifications/read/", NotificationReadView.as_view()),
    path("auth/steam/start/", steam_start),
]