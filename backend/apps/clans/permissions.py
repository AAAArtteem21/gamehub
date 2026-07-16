from rest_framework import permissions
from .models import ClanMembership


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner_id == request.user.id


class IsClanLeaderOrOfficer(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        clan_id = view.kwargs.get('clan_pk')
        if not clan_id:
            return True
        return ClanMembership.objects.filter(
            clan_id=clan_id,user=request.user,role__in=['leader', 'officer']).exists()