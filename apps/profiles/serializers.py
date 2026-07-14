from datetime import date 
from rest_framework import serializers
from .models import GameAccount,DailySnapshot
from .serivces import get_daily_playtime
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
        return obj.game_account.plaform in ESTIMATED_PLATFORMS
    

class GameAccountSerializer(serializers.ModelSerializer):
    snapshots = serializers.SerializerMethodField()

    class Meta:
        model = GameAccount
        fields = ['id','user','platform','external_id','verified','created_at','snapshots']
        read_only_fields = ['user','verified','created_at']


    def get_snapshots(self,obj):
        recent = obj.snapshots.filter(date__gte=date.today().replace(day=1))
        return DailySnapshotSerializer(recent,many=True).data 
    
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
