from rest_framework.routers import DefaultRouter
from .views import ClanViewSet

router = DefaultRouter()
router.register("clans", ClanViewSet, basename="clan")

urlpatterns = router.urls