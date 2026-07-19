from rest_framework import serializers
from .models import Clan,ClanMembership
from .validators import validate_clan_name, MAX_CLAN_PER_USER

class ClanMembershipSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    class Meta:
        model = ClanMembership
        fields = ['id','clan','user','username','role','joined_at']
        read_only_fields = ['user','joined_at']

class ClanSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()
    invite_code = serializers.SerializerMethodField()

    class Meta:
        model = Clan
        fields = ["id", "name", "owner", "logo", "description", "invite_code", "members_count", "created_at"]
        read_only_fields = ["owner", "created_at"]

    def get_members_count(self, obj):
        return getattr(obj, "members_count_annotated", None) or obj.memberships.count()

    def get_invite_code(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        is_leader = ClanMembership.objects.filter(
            clan=obj, user=request.user, role="leader"
        ).exists()
        return obj.invite_code if is_leader else None
    
    def validate_name(self, value):
        validate_clan_name(value)
        return value.strip()
    
    def validate(self, attrs):
        request = self.context['request']
        if self.instance is None:
            owned_count = Clan.objects.filter(owner=request.user).count()
            if owned_count >= MAX_CLAN_PER_USER:
                raise serializers.ValidationError(
                    f'Нельзя создать больше {MAX_CLAN_PER_USER} кланнов'
                )
        return attrs 

    def create(self,validated_data):
        request = self.context['request']
        validated_data['owner'] = request.user
        clan = super().create(validated_data)
        ClanMembership.objects.create(clan=clan,user=request.user,role='leader')
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
    

    