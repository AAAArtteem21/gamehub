from rest_framework.routers import DefaultRouter
from .views import LFGPostViewSet,LFGResponseViewSet

router = DefaultRouter()
router.register('lfg-posts', LFGPostViewSet, basename='lfgpost')
router.register('lfg-response', LFGResponseViewSet, basename='lfgresponse')

urlpatterns = router.urls