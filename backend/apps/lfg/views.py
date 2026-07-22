from django.shortcuts import render
from rest_framework import viewsets,permissions,status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.db.models import Count,Q
from .models import LFGChatMessage
from .serializers import LFGChatMessageSerializer
from django.utils import timezone

from .models import LFGPost,LFGResponse,ContactReveal,LFGChatMessage
from .serializers import LFGPostSerializer,LFGResponseSerializer
from .permissions import IsAuthorOrReadOnly,IsResponseOwnerOrReadOnly

class LFGPostViewSet(viewsets.ModelViewSet):
    serializer_class = LFGPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsAuthorOrReadOnly]

    def get_queryset(self):
        qs = (
            LFGPost.objects
            .select_related('author')
            .annotate(responses_count_annotated=Count('responses'))
            .order_by('-created_at')
        )
        game = self.request.query_params.get('game')
        status_param = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        if game:
            qs = qs.filter(game__iexact=game)
        if search:
            qs = qs.filter(Q(game__icontains=search) | Q(description__icontains=search))
        if status_param:
            qs = qs.filter(status=status_param)
        else:
            qs = qs.filter(status='open')

        return qs

    
    @method_decorator(ratelimit(key='user',rate='5/h',block=True))
    def create(self,request,*args,**kwargs):
        return super().create(request,*args,**kwargs)
    
    @action(detail=True,methods=['post'],permission_classes=[permissions.IsAuthenticated])
    def close(self,request,pk=None):
        post = self.get_object()
        if post.author_id != request.user.id:
            return Response(
                {'detail':'Только автор может закрыть заявку'},
                status=status.HTTP_403_FORBIDDEN
            )
        post.status='closed'
        post.save(update_fields=['status'])
        return Response(self.get_serializer(post).data)
    
class LFGResponseViewSet(viewsets.ModelViewSet):
    serializer_class = LFGResponseSerializer
    permission_classes = [permissions.IsAuthenticated,IsResponseOwnerOrReadOnly]

    def get_queryset(self):
        qs = LFGResponse.objects.select_related('user','post')
        post_id = self.request.query_params.get('post')
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs
    
class LFGChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = LFGChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post'] 

    def get_queryset(self):
        qs = LFGChatMessage.objects.select_related('sender', 'post')
        post_id = self.request.query_params.get('post')
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs
    
class MyNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        reveals = (
            ContactReveal.objects
            .filter(user=request.user, expires_at__gt=now)
            .select_related('post')
            .order_by('-revealed_at')
        )
        data = [{
            "post_id": r.post_id,
            "game": r.post.game,
            "contact": r.contact,
            "expires_at": r.expires_at,
        } for r in reveals]
        return Response(data)


class MyChatThreadsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        post_ids = set(LFGPost.objects.filter(author=user).values_list('id', flat=True))
        post_ids |= set(LFGResponse.objects.filter(user=user).values_list('post_id', flat=True))

        threads = []
        for post in LFGPost.objects.filter(id__in=post_ids).select_related('author'):
            last_msg = post.chat_messages.order_by('-created_at').first()
            threads.append({
                "post_id": post.id,
                "game": post.game,
                "author": str(post.author),
                "last_message": last_msg.text if last_msg else None,
                "last_message_at": last_msg.created_at if last_msg else post.created_at,
            })
        threads.sort(key=lambda t: t["last_message_at"], reverse=True)
        return Response(threads)