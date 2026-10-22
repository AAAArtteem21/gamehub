from django.urls import path
from .views import MyDotaAnalysesView,CreateDotaAnalysisView,MatchAnalysisDetailView

urlpatterns = [
    path("analysis/dota/", CreateDotaAnalysisView.as_view()),
    path("analysis/dota/list/", MyDotaAnalysesView.as_view()),
    path("analysis/<int:pk>/", MatchAnalysisDetailView.as_view()),
]