from rest_framework.routers import DefaultRouter
from .views import GameAccountViewSet,LeaderboardView,PublicProfileView
from django.urls import path

router = DefaultRouter()
router.register('game-accounts',GameAccountViewSet,basename='gameaccount')

urlpatterns = router.urls + [
    path('leaderboard/', LeaderboardView.as_view()),
    path('players/<int:user_id>/', PublicProfileView.as_view()),
]