import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import LFGPost, LFGChatMessage


class LFGChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.post_id = self.scope['url_route']['kwargs']['post_id']
        self.room_group_name = f'lfg_chat_{self.post_id}'
        user = self.scope['user']

        if not user.is_authenticated:
            await self.close()
            return

        if not await self.check_participant(user):
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        text = (data.get('text') or '').strip()
        if not text or len(text) > 1000:
            return

        user = self.scope['user']
        message = await self.save_message(user, text)

        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'chat_message', 'message': message},
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def check_participant(self, user):
        try:
            post = LFGPost.objects.get(id=self.post_id)
        except LFGPost.DoesNotExist:
            return False
        return post.author_id == user.id or post.responses.filter(user=user).exists()

    @database_sync_to_async
    def save_message(self, user, text):
        msg = LFGChatMessage.objects.create(post_id=self.post_id, sender=user, text=text)
        profile = getattr(user, 'profile', None)
        return {
            'id': msg.id,
            'sender_id': user.id,
            'sender_username': user.username,
            'sender_avatar': profile.avatar_url if profile else None,
            'text': msg.text,
            'created_at': msg.created_at.isoformat(),
        }