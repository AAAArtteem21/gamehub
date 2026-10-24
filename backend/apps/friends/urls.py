from django.urls import path
from .views import (
    MyPresenceView,
    FriendsListView,
    FriendRequestsView,
    FriendRequestActionView,
    UnfriendView,
    SuggestionsView,
    InviteFriendView,
    FriendshipStatusView,
)

from .views import (
    MyPresenceView,
    FriendsListView,
    FriendRequestsView,
    FriendRequestActionView,
    UnfriendView,
    SuggestionsView,
    InviteFriendView,
    FriendshipStatusView,
)

urlpatterns = [
    path("friends/presence/", MyPresenceView.as_view()),
    path("friends/", FriendsListView.as_view()),
    path("friends/requests/", FriendRequestsView.as_view()),
    path("friends/requests/<int:pk>/<str:action>/", FriendRequestActionView.as_view()),
    path("friends/<int:user_id>/", UnfriendView.as_view()),
    path("friends/suggestions/", SuggestionsView.as_view()),
    path("friends/invite/", InviteFriendView.as_view()),
    path("friends/status/<int:user_id>/", FriendshipStatusView.as_view()),
]