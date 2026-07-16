from rest_framework import serializers
from .models import LFGPost,LFGResponse
from .validators import validate_no_profanity
from django.utils import timezone


class LFGResponseSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = LFGResponse
        fields = ['id','post','user','created_at']

    def validate_post(self,value):
        if value.status == 'closed':
            raise serializers.ValidationError('Заявку уже забрали')
        return value 
    
    def validate(self,attrs):
        request = self.context['request']
        post = attrs['post']
        if LFGResponse.objects.filter(post=post,user=request.user).exists():
            raise serializers.ValidationError('Ты уже откликнулся на эту заявку')
        if post.author_id == request.user.id:
            raise serializers.ValidationError('Ты не можешь откликнутся на свою заявку')
        return attrs
    
    def create(self,validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
class LFGPostSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    responses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LFGPost
        fields = [
            'id','author','game','datetime','description',
            'contact','status','created_at','responses_count',
        ]
        read_only_fields = ['author','status','created_at']

    def get_responses_count(self,obj):
        value = getattr(obj, 'responses_count_annotated', None)
        return value if value is not None else obj.responses.count()
    
    def validate_game(self,value):
        value = value.strip()
        if len(value) < 2 :
            raise serializers.ValidationError('Название игры слишком короткое')
        validate_no_profanity(value)
        return value 
    
    def validate_description(self,value):
        if len(value) > 300:
            raise serializers.ValidationError('Слишком большое описание')
        validate_no_profanity(value)
        return value 
    
    def validate_contact(self,value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError('Укажи свой юз в дс или тг или акк')
        return value 
    
    def validate_datetime(self,value):
        if value < timezone.now():
            raise serializers.ValidationError('Нельзя создать заявку в прошедшее время')
        return value 
    
    def create(self,validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)