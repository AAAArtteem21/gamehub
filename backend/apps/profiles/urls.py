from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    GameAccountViewSet,
    LeaderboardView,
    PublicProfileView,
    WorldLeaderboardView,
    GuestProfileView,
    MatchParticipantsView,
    RecentMatchesFeedView,
)
from .social_views import (
    ComparePlayersView,
    WeeklyReportView,
    TeammateRecommendationsView,
    FavoriteToggleView,
    FavoriteListView,
    FavoriteStatusView,
    ClanFeedView,
)

router = DefaultRouter()
router.register("game-accounts", GameAccountViewSet, basename="gameaccount")

urlpatterns = router.urls + [
    path("match-participants/<str:game>/<str:match_id>/", MatchParticipantsView.as_view()),
    path("leaderboard/", LeaderboardView.as_view()),
    path("players/<int:user_id>/", PublicProfileView.as_view()),
    path("players/compare/", ComparePlayersView.as_view()),
    path("world-leaderboard/", WorldLeaderboardView.as_view()),
    path('guest-profile/<str:game>/<str:external_id>/', GuestProfileView.as_view()),
    path("me/recent-matches/", RecentMatchesFeedView.as_view()),
    path("me/weekly-report/", WeeklyReportView.as_view()),
    path("recommendations/teammates/", TeammateRecommendationsView.as_view()),
    path("favorites/", FavoriteListView.as_view()),
    path("favorites/toggle/", FavoriteToggleView.as_view()),
    path("favorites/status/", FavoriteStatusView.as_view()),
    path("clans/<int:clan_id>/feed/", ClanFeedView.as_view()),
]