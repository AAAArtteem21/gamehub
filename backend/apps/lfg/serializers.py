
from django.utils import timezone
from rest_framework import serializers
from .models import LFGPost, LFGResponse, LFGChatMessage,ContactReveal
from .validators import validate_no_profanity
from datetime import timedelta





class LFGResponseSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = LFGResponse
        fields = ['id', 'post', 'user', 'created_at']
        read_only_fields = ['user', 'created_at']

    def validate_post(self, value):
        if value.status == 'closed':
            raise serializers.ValidationError("Заявка уже закрыта — набор завершён")
        return value

    def validate(self, attrs):
        request = self.context['request']
        post = attrs['post']
        if LFGResponse.objects.filter(post=post, user=request.user).exists():
            raise serializers.ValidationError("Ты уже откликнулся на эту заявку")
        if post.author_id == request.user.id:
            raise serializers.ValidationError("Нельзя откликнуться на свою же заявку")
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        response = super().create(validated_data)

        post = response.post
        reveal, created = ContactReveal.objects.get_or_create(
            user=response.user,
            post=post,
            defaults={"contact": post.contact, "expires_at": timezone.now() + timedelta(hours=1)},
        )
        if not created:
            
            reveal.contact = post.contact
            reveal.expires_at = timezone.now() + timedelta(hours=1)
            reveal.save(update_fields=["contact", "expires_at"])

        if post.responses.count() >= post.slots_needed:
            post.status = 'closed'
            post.save(update_fields=['status'])

        return response

class LFGPostSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    author_avatar = serializers.SerializerMethodField()
    responses_count = serializers.SerializerMethodField()
    has_responded = serializers.SerializerMethodField()
    is_author = serializers.SerializerMethodField()

    class Meta:
        model = LFGPost
        fields = [
            'id', 'author', 'author_id', 'author_avatar', 'game', 'datetime', 'description', 'contact',
            'slots_needed', 'status', 'created_at', 'responses_count',
            'has_responded', 'is_author',
        ]
        read_only_fields = ['author', 'status', 'created_at']

    def get_author_avatar(self, obj):
        profile = getattr(obj.author, 'profile', None)
        return profile.avatar_url if profile else None

    def get_responses_count(self, obj):
        return getattr(obj, 'responses_count_annotated', None) or obj.responses.count()

    def get_has_responded(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.responses.filter(user=request.user).exists()

    def get_is_author(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author_id == request.user.id

    def validate_game(self, value):
        value = value.strip()
        validate_no_profanity(value)
        return value

    def validate_description(self, value):
        if len(value) > 500:
            raise serializers.ValidationError("Описание не должно превышать 500 символов")
        validate_no_profanity(value)
        return value

    def validate_contact(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Укажи корректный контакт (discord/telegram)")
        return value

    def validate_slots_needed(self, value):
        if value < 1 or value > 20:
            raise serializers.ValidationError("Количество игроков должно быть от 1 до 20")
        return value

    def validate_datetime(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Нельзя создать заявку на прошедшее время")
        return value

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        is_author = self.get_is_author(instance)
        has_responded = self.get_has_responded(instance)
        if not (is_author or has_responded):
            data['contact'] = None
        return data

class LFGChatMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = LFGChatMessage
        fields = ['id', 'post', 'sender_id', 'sender_username', 'sender_avatar', 'text', 'created_at']
        read_only_fields = ['created_at']

    def get_sender_avatar(self, obj):
        profile = getattr(obj.sender, 'profile', None)
        return profile.avatar_url if profile else None

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Сообщение не может быть пустым")
        if len(value) > 1000:
            raise serializers.ValidationError("Слишком длинное сообщение")
        return value

    def validate_post(self, value):
        request = self.context['request']
        is_participant = (
            value.author_id == request.user.id
            or value.responses.filter(user=request.user).exists()
        )
        if not is_participant:
            raise serializers.ValidationError("Чат доступен только автору и откликнувшимся")
        return value

    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)