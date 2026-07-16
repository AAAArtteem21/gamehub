from rest_framework.routers import DefaultRouter
from .views import GameAccountViewSet

router = DefaultRouter()
router.register('game-accounts',GameAccountViewSet,basename='gameaccount')

urlpatterns = router.urls