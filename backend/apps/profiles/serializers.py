from datetime import date 
from rest_framework import serializers
from .models import GameAccount,DailySnapshot
from .serivces import get_daily_playtime,build_display_stats
from .validators import validate_external_id


ESTIMATED_PLATFORMS = {'opendota','faceit'}

class DailySnapshotSerializer(serializers.ModelSerializer):
    today_playtime_minutes = serializers.SerializerMethodField()
    is_estimated = serializers.SerializerMethodField()

    class Meta:
        model = DailySnapshot
        fields = ['id','appid','game_name','playtime_forever','date','today_playtime_minutes','is_estimated']

    def get_today_playtime_minutes(self,obj):
        return get_daily_playtime(obj.game_account,obj.appid,obj.date)
    
    def get_is_estimated(self,obj):
        return obj.game_account.platform in ESTIMATED_PLATFORMS
    

class GameAccountSerializer(serializers.ModelSerializer):
    snapshots = serializers.SerializerMethodField()
    display_stats = serializers.SerializerMethodField()

    class Meta:
        model = GameAccount
        fields = [
            'id', 'user', 'platform', 'external_id', 'nickname', 'avatar',
            'verified', 'created_at', 'snapshots', 'extra_stats',
            'skill_rating', 'game_label', 'display_stats',
        ]
        read_only_fields = ['user', 'verified', 'created_at', 'extra_stats', 'skill_rating', 'game_label']

    def get_display_stats(self, obj):
        return build_display_stats(obj.platform, obj.extra_stats)


    def get_snapshots(self, obj):
        from django.db.models import Max

        latest_dates = (
            obj.snapshots.values("appid")
            .annotate(max_date=Max("date"))
        )
        date_map = {r["appid"]: r["max_date"] for r in latest_dates}
        rows = []
        for appid, max_date in date_map.items():
            s = obj.snapshots.filter(appid=appid, date=max_date).first()
            if s:
                rows.append(s)
        rows.sort(key=lambda s: s.playtime_forever or 0, reverse=True)
        return DailySnapshotSerializer(rows, many=True).data
    
    def validate(self,attrs):
        platform = attrs.get('platform')
        external_id = attrs.get('external_id','').strip()
        validate_external_id(platform,external_id)

        if GameAccount.objects.filter(platform=platform,external_id=external_id).exists():
            raise serializers.ValidationError('Этот аккаунт уже подключен')
        
        attrs['external_id'] = external_id
        return attrs 
    
    def create(self,validated_data):
        validated_data['user'] = self.context['request'].user 
        return super().create(validated_data)
