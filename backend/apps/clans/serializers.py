from rest_framework import serializers
from .models import Clan, ClanMembership
from .utils import clan_logo_url

MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


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
    # logo в ответе = полный URL (строка). Запись файла — только через upload_logo.
    logo = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Clan
        fields = [
            "id",
            "name",
            "owner",
            "logo",
            "logo_url",
            "description",
            "invite_code",
            "is_member",
            "my_role",
            "members_count",
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
        membership = ClanMembership.objects.filter(clan=obj, user=request.user).first()
        return membership.role if membership else None

    def get_invite_code(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        is_leader = ClanMembership.objects.filter(
            clan=obj, user=request.user, role="leader"
        ).exists()
        return obj.invite_code if is_leader else None

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Название клана должно быть не короче 3 символов")
        if len(value) > 100:
            raise serializers.ValidationError("Название клана слишком длинное")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is None:
            owned_count = Clan.objects.filter(owner=request.user).count()
            if owned_count >= 3:
                raise serializers.ValidationError("Нельзя создать больше 3 кланов")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["owner"] = request.user
        clan = super().create(validated_data)
        ClanMembership.objects.create(clan=clan, user=request.user, role="leader")
        return clan


class JoinClanSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=12)


class ClanDashboardEntrySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()
    joined_at = serializers.DateTimeField()
    today_playtime = serializers.IntegerField()
    week_playtime = serializers.IntegerField()
    month_playtime = serializers.IntegerField()
    last_active_date = serializers.DateField(allow_null=True)
    is_inactive = serializers.BooleanField()