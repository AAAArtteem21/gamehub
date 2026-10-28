from rest_framework import serializers
from django.contrib.auth  import get_user_model
from apps.users.display import user_public_name
from .models import Friendship, FriendRequest, PlayStatus

User = get_user_model()

def _avatar(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "avatar_url", None) if profile else None

def _presence_payload(user):
    p = getattr(user, "presence", None)
    if not p:
        return {
            "status": PlayStatus.OFFLINE,
            "note": "",
            "game": "",
            "updated_at": None,
        }
    return {
        "status": p.status,
        "note": p.note or "",
        "game": p.game or "",
        "updated_at": p.updated_at,
    }


def user_card(user):
    return {
        "id": user.id,
        "username": user_public_name(user),
        "avatar_url": _avatar(user),
        "presence": _presence_payload(user),
    }

class PresenceSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PlayStatus.CHOICES)
    note = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )
    game = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )


class FriendRequestCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    message = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )

    def validate_user_id(self, value):
        request = self.context["request"]
        if value == request.user.id:
            raise serializers.ValidationError("Нельзя добавить себя")
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Пользователь не найден")
        if Friendship.are_friends(request.user.id, value):
            raise serializers.ValidationError("Уже друзья")

        if FriendRequest.objects.filter(
            from_user=request.user,
            to_user_id=value,
            status=FriendRequest.STATUS_PENDING,
        ).exists():
            raise serializers.ValidationError("Заявка уже отправлена")

        if FriendRequest.objects.filter(
            from_user_id=value,
            to_user=request.user,
            status=FriendRequest.STATUS_PENDING,
        ).exists():
            raise serializers.ValidationError("Уже есть входящая заявка — прими её")

        return value

class InviteSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    message = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )
    game = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
