from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    LFGPostViewSet,
    LFGResponseViewSet,
    LFGChatMessageViewSet,
    MyNotificationsView,
    MyChatThreadsView,
    QuickStatsView,
    MyApplicationsView,
)

router = DefaultRouter()
router.register("lfg-posts", LFGPostViewSet, basename="lfgpost")
router.register("lfg-responses", LFGResponseViewSet, basename="lfgresponses")
router.register("lfg-chat", LFGChatMessageViewSet, basename="lfgchat")

urlpatterns = router.urls + [
    path("lfg-notifications/", MyNotificationsView.as_view()),
    path("lfg-chat-threads/", MyChatThreadsView.as_view()),
    path("lfg-my-applications/", MyApplicationsView.as_view()),
    path("me/quick-stats/", QuickStatsView.as_view()),
]