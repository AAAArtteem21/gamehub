from rest_framework import serializers

from .models import Clan, ClanMembership
from .utils import clan_logo_url
from .profanity import contains_profanity

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
        return obj.user.username


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
            "id",
            "name",
            "owner",
            "logo",
            "logo_url",
            "description",
            "is_open",
            "game",
            "game_label",
            "max_members",
            "join_hours_start",
            "join_hours_end",
            "join_requirements",
            "invite_code",
            "is_member",
            "my_role",
            "members_count",
            "can_join_open",
            "created_at",
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
        """Код только лидер и офицер."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        ok = ClanMembership.objects.filter(
            clan=obj,
            user=request.user,
            role__in=["leader", "officer"],
        ).exists()
        return obj.invite_code if ok else None

    def get_game_label(self, obj):
        return dict(Clan.GAME_CHOICES).get(obj.game, obj.game)

    def get_can_join_open(self, obj):
        """Подсказка UI: открытый и ещё не участник."""
        request = self.context.get("request")
        if not obj.is_open:
            return False
        if not request or not request.user.is_authenticated:
            return True
        return not ClanMembership.objects.filter(clan=obj, user=request.user).exists()

    def validate_name(self, value):
        value = (value or "").strip()
        if len(value) < 3:
            raise serializers.ValidationError("Название не короче 3 символов")
        if len(value) > 50:
            raise serializers.ValidationError("Название слишком длинное")
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
        if len(value) > 500:
            raise serializers.ValidationError("Слишком длинные требования")
        return value

    def validate_max_members(self, value):
        if value is not None and value < 2:
            raise serializers.ValidationError("Минимум 2 участника или пусто (без лимита)")
        if value is not None and value > 500:
            raise serializers.ValidationError("Слишком большой лимит")
        return value

    def validate_join_hours_start(self, value):
        if value is not None and not (0 <= int(value) <= 23):
            raise serializers.ValidationError("Час от 0 до 23")
        return value

    def validate_join_hours_end(self, value):
        if value is not None and not (0 <= int(value) <= 23):
            raise serializers.ValidationError("Час от 0 до 23")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is None:
            owned = Clan.objects.filter(owner=request.user).count()
            if owned >= MAX_CLANS_OWNED:
                raise serializers.ValidationError(
                    {"detail": f"Нельзя создать больше {MAX_CLANS_OWNED} кланов"}
                )
        start = attrs.get("join_hours_start", getattr(self.instance, "join_hours_start", None))
        end = attrs.get("join_hours_end", getattr(self.instance, "join_hours_end", None))
        if (start is None) ^ (end is None):
            raise serializers.ValidationError(
                {"join_hours_start": "Укажи оба часа окна входа или ни одного"}
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