from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ClanViewSet, ClanLeaderboardView, MyClansPanelView, ClanMessagesView


router = DefaultRouter()
router.register("clans", ClanViewSet, basename="clan")

urlpatterns = [
    path("clans/leaderboard/", ClanLeaderboardView.as_view()),
    path("clans/my-panel/", MyClansPanelView.as_view()),
    path("clans/<int:clan_id>/messages/", ClanMessagesView.as_view()),
] + router.urls