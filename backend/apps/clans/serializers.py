from rest_framework import serializers
from .models import Clan, ClanMembership
from .utils import clan_logo_url
from .profanity import contains_profanity
from apps.users.display import user_public_name

MAX_LOGO_SIZE = 2 * 1024 * 1024
ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_CLANS_OWNED = 3


class ClanMembershipSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = ClanMembership
        fields = ["id", "clan", "user", "username", "role", "joined_at"]
        read_only_fields = ["user", "joined_at"]

    def get_username(self, obj):
        return user_public_name(obj.user)


class ClanSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()
    invite_code = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    game_label = serializers.SerializerMethodField()
    can_join_open = serializers.SerializerMethodField()

    class Meta:
        model = Clan
        fields = [
            "id", "name", "owner", "logo", "logo_url", "description",
            "is_open", "game", "game_label", "max_members", "min_playtime_hours",
            "join_requirements", "invite_code", "is_member", "my_role",
            "members_count", "can_join_open", "created_at",
        ]
        read_only_fields = ["owner", "created_at", "logo", "logo_url"]

    def get_logo(self, obj):
        return clan_logo_url(obj, self.context.get("request"))

    def get_logo_url(self, obj):
        return clan_logo_url(obj, self.context.get("request"))

    def get_members_count(self, obj):
        return getattr(obj, "members_count_annotated", None) or obj.memberships.count()

    def get_is_member(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return ClanMembership.objects.filter(clan=obj, user=request.user).exists()

    def get_my_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        m = ClanMembership.objects.filter(clan=obj, user=request.user).first()
        return m.role if m else None

    def get_invite_code(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        ok = ClanMembership.objects.filter(
            clan=obj, user=request.user, role__in=["leader", "officer"]
        ).exists()
        return obj.invite_code if ok else None

    def get_game_label(self, obj):
        return dict(Clan.GAME_CHOICES).get(obj.game, obj.game)

    def get_can_join_open(self, obj):
        if not obj.is_open:
            return False
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return True
        return not ClanMembership.objects.filter(clan=obj, user=request.user).exists()

    def validate_name(self, value):
        value = (value or "").strip()
        if len(value) < 3:
            raise serializers.ValidationError("Название не короче 3 символов")
        if contains_profanity(value):
            raise serializers.ValidationError("В названии недопустимые слова")
        return value

    def validate_description(self, value):
        value = value or ""
        if contains_profanity(value):
            raise serializers.ValidationError("В описании недопустимые слова")
        return value

    def validate_join_requirements(self, value):
        value = value or ""
        if contains_profanity(value):
            raise serializers.ValidationError("В требованиях недопустимые слова")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is None:
            if Clan.objects.filter(owner=request.user).count() >= MAX_CLANS_OWNED:
                raise serializers.ValidationError(
                    {"detail": f"Нельзя создать больше {MAX_CLANS_OWNED} кланов"}
                )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["owner"] = request.user
        validated_data.pop("logo", None)
        clan = super().create(validated_data)
        ClanMembership.objects.create(clan=clan, user=request.user, role="leader")
        return clan


class JoinClanSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=12, required=False, allow_blank=True)
    clan_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if not attrs.get("invite_code") and not attrs.get("clan_id"):
            raise serializers.ValidationError("Нужен invite_code или clan_id")
        return attrs


class ClanDashboardEntrySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()
    joined_at = serializers.DateTimeField()
    two_weeks_playtime = serializers.IntegerField()
    total_playtime = serializers.IntegerField()
    is_inactive = serializers.BooleanField()