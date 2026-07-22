from rest_framework.routers import DefaultRouter
from .views import LFGPostViewSet,LFGResponseViewSet,LFGChatMessageViewSet,MyNotificationsView, MyChatThreadsView
from django.urls import path 

router = DefaultRouter()
router.register('lfg-posts', LFGPostViewSet, basename='lfgpost')
router.register('lfg-responses', LFGResponseViewSet, basename='lfgresponses')
router.register('lfg-chat', LFGChatMessageViewSet, basename='lfgchat')

urlpatterns = router.urls + [
    path('lfg-notifications/', MyNotificationsView.as_view()),
    path('lfg-chat-threads/', MyChatThreadsView.as_view()),
]