from rest_framework.routers import DefaultRouter
from .views import GameAccountViewSet,LeaderboardView,PublicProfileView,WorldLeaderboardView,GuestProfileView,MatchParticipantsView
from django.urls import path

router = DefaultRouter()
router.register('game-accounts',GameAccountViewSet,basename='gameaccount')

urlpatterns = router.urls + [
    path('match-participants/<str:game>/<str:match_id>/', MatchParticipantsView.as_view()),
    path('leaderboard/', LeaderboardView.as_view()),
    path('players/<int:user_id>/', PublicProfileView.as_view()),
    path('world-leaderboard/', WorldLeaderboardView.as_view()),
    path('guest-profile/<str:game>/<str:external_id>/', GuestProfileView.as_view())
]