from rest_framework.routers import DefaultRouter
from .views import ClanViewSet,ClanLeaderboardView
from django.urls import path

router = DefaultRouter()
router.register("clans", ClanViewSet, basename="clan")

urlpatterns = router.urls + [path('clans/leaderboard/', ClanLeaderboardView.as_view())]