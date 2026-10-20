from django.utils import timezone
from rest_framework import serializers
from datetime import timedelta

from .models import LFGPost, LFGResponse, LFGChatMessage, ContactReveal
from .validators import validate_no_profanity
from apps.users.display import user_public_name


def user_has_synced_account(user):
    from apps.profiles.models import GameAccount
    return GameAccount.objects.filter(user=user, verified=True).exists()


def _profile_snapshot(user):
    """Краткий снимок профиля для карточки заявки у автора."""
    profile = getattr(user, "profile", None)
    avatar = profile.avatar_url if profile else None
    games = []
    try:
        from apps.profiles.models import GameAccount
        for ga in GameAccount.objects.filter(user=user, verified=True).order_by("platform")[:6]:
            games.append({
                "platform": ga.platform,
                "nickname": ga.nickname or ga.external_id,
                "skill_rating": ga.skill_rating,
                "game_label": ga.game_label or ga.platform,
            })
    except Exception:
        pass
    return {
        "id": user.id,
        "username": user_public_name(user),
        "avatar_url": avatar,
        "games": games,
    }


class LFGResponseSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    profile = serializers.SerializerMethodField()
    post_game = serializers.CharField(source="post.game", read_only=True)
    post_datetime = serializers.DateTimeField(source="post.datetime", read_only=True)
    post_status = serializers.CharField(source="post.status", read_only=True)
    post_author = serializers.SerializerMethodField()
    post_author_id = serializers.IntegerField(source="post.author_id", read_only=True)

    class Meta:
        model = LFGResponse
        fields = [
            "id", "post", "user", "user_id", "profile",
            "message", "preferred_role", "status",
            "created_at", "decided_at",
            "post_game", "post_datetime", "post_status",
            "post_author", "post_author_id",
        ]
        read_only_fields = [
            "user", "user_id", "profile", "status",
            "created_at", "decided_at",
            "post_game", "post_datetime", "post_status",
            "post_author", "post_author_id",
        ]

    def get_user(self, obj):
        return user_public_name(obj.user)

    def get_profile(self, obj):
        return _profile_snapshot(obj.user)

    def get_post_author(self, obj):
        return user_public_name(obj.post.author)

    def validate_post(self, value):
        if value.status == "closed":
            raise serializers.ValidationError("Заявка уже закрыта")
        return value

    def validate_message(self, value):
        value = (value or "").strip()
        if len(value) > 300:
            raise serializers.ValidationError("Макс 300 символов")
        if value:
            validate_no_profanity(value)
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if not user_has_synced_account(request.user):
            raise serializers.ValidationError(
                "Сначала подключи и синхронизируй игровой аккаунт"
            )
        post = attrs["post"]
        if LFGResponse.objects.filter(post=post, user=request.user).exists():
            raise serializers.ValidationError("Уже подал заявку")
        if post.author_id == request.user.id:
            raise serializers.ValidationError("Нельзя на свою заявку")
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        validated_data["status"] = "pending"
        response = super().create(validated_data)
        try:
            from apps.users.services import notify
            from apps.users.xp import add_xp, XP_LFG_RESPONSE
            ru = self.context["request"].user
            if response.post.author_id != ru.id:
                notify(
                    response.post.author,
                    kind="lfg_response",
                    title="Новая заявка в LFG",
                    body=f"{user_public_name(ru)} хочет в «{response.post.game}»",
                    link=f"/lfg/{response.post_id}",
                )
            add_xp(ru, XP_LFG_RESPONSE, reason="заявка LFG")
        except Exception:
            pass
        return response


class LFGPostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    author_id = serializers.IntegerField(source="author.id", read_only=True)
    author_avatar = serializers.SerializerMethodField()
    responses_count = serializers.SerializerMethodField()
    accepted_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    has_responded = serializers.SerializerMethodField()
    my_response_status = serializers.SerializerMethodField()
    is_author = serializers.SerializerMethodField()

    class Meta:
        model = LFGPost
        fields = [
            "id", "author", "author_id", "author_avatar", "game", "datetime",
            "description", "contact", "slots_needed", "status", "created_at",
            "responses_count", "accepted_count", "pending_count",
            "has_responded", "my_response_status", "is_author",
        ]
        read_only_fields = ["author", "status", "created_at"]

    def get_author(self, obj):
        return user_public_name(obj.author)

    def get_author_avatar(self, obj):
        profile = getattr(obj.author, "profile", None)
        return profile.avatar_url if profile else None

    def get_responses_count(self, obj):
        return getattr(obj, "accepted_count_annotated", None) or obj.accepted_count

    def get_accepted_count(self, obj):
        return getattr(obj, "accepted_count_annotated", None) or obj.accepted_count

    def get_pending_count(self, obj):
        return getattr(obj, "pending_count_annotated", None) or obj.responses.filter(
            status="pending"
        ).count()

    def get_has_responded(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.responses.filter(user=request.user).exclude(
            status="withdrawn"
        ).exists()

    def get_my_response_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        r = obj.responses.filter(user=request.user).first()
        return r.status if r else None

    def get_is_author(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.author_id == request.user.id

    def validate_game(self, value):
        value = value.strip()
        validate_no_profanity(value)
        return value

    def validate_description(self, value):
        if len(value) > 500:
            raise serializers.ValidationError("Макс 500 символов")
        validate_no_profanity(value)
        return value

    def validate_contact(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Укажи контакт")
        return value

    def validate_slots_needed(self, value):
        if value < 1 or value > 20:
            raise serializers.ValidationError("Слоты 1–20")
        return value

    def validate_datetime(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Нельзя в прошлом")
        return value

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        post = super().create(validated_data)
        try:
            from apps.users.xp import add_xp, XP_LFG_POST
            add_xp(self.context["request"].user, XP_LFG_POST, reason="заявка LFG")
        except Exception:
            pass
        try:
            from django.contrib.auth import get_user_model
            from apps.profiles.models import FavoritePlayer
            from apps.users.services import notify
            author = post.author
            owner_ids = list(
                FavoritePlayer.objects.filter(target_user=author)
                .values_list("owner_id", flat=True)
                .distinct()
            )
            name = user_public_name(author)
            User = get_user_model()
            for u in User.objects.filter(id__in=owner_ids).exclude(id=author.id):
                notify(
                    u,
                    kind="favorite_lfg",
                    title="Избранный в LFG",
                    body=f"{name} ищет тиммейтов: {post.game}",
                    link=f"/lfg/{post.id}",
                )
        except Exception:
            pass
        return post

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        can_see = False
        if request and request.user.is_authenticated:
            if instance.author_id == request.user.id:
                can_see = True
            elif instance.responses.filter(
                user=request.user, status="accepted"
            ).exists():
                can_see = True
            else:
                from django.utils import timezone as tz
                can_see = ContactReveal.objects.filter(
                    user=request.user, post=instance, expires_at__gt=tz.now()
                ).exists()
        if not can_see:
            data["contact"] = None
        return data


class LFGChatMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)
    sender_username = serializers.SerializerMethodField()
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = LFGChatMessage
        fields = [
            "id", "post", "sender_id", "sender_username",
            "sender_avatar", "text", "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_sender_username(self, obj):
        return user_public_name(obj.sender)

    def get_sender_avatar(self, obj):
        profile = getattr(obj.sender, "profile", None)
        return profile.avatar_url if profile else None

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Пусто")
        if len(value) > 1000:
            raise serializers.ValidationError("Слишком длинное")
        return value

    def validate_post(self, value):
        request = self.context["request"]
        ok = (
            value.author_id == request.user.id
            or value.responses.filter(user=request.user, status="accepted").exists()
        )
        if not ok:
            raise serializers.ValidationError("Чат только после принятия заявки")
        return value

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)