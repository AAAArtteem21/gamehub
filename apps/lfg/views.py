from django.shortcuts import render
from rest_framework import viewsets,permissions,status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.db.models import Count

from .models import LFGPost,LFGResponse
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

        if game:
            qs = qs.filter(game__iexact=game)
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