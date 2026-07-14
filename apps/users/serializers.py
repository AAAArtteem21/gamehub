from rest_framework import serializers
from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username',read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id','username','avatar_url','steam_id','display_name',
            'bio','created_at','updated_at',
        ]
        read_only_fields = ['steam_id','avatar_url','created_at','updated_at']

    def validate_display_name(self,value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('Имя слишком короткое')
        return value
    
    def validate_bio(self,value):
        if len(value) > 300:
            raise serializers.ValidationError('Описание слишком длинное')
        return value 
