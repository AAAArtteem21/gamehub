from django.shortcuts import render
from django.core.cache import cache
from rest_framework import viewsets,permissions,status 
from rest_framework.decorators import action 
from rest_framework.response import Response 

from .models import GameAccount
from .serializers import GameAccountSerializer
from .serivces import ProfileSyncService,SyncError,get_account_summary
from .tasks import sync_single_account

SYNC_COOLDOWN_SECONDS =300
LIST_CACHE_TIMEOUT = 120
MAX_ACCOUNTS_PER_PLATFORM = 1

def _list_cache_key(user_id):
    return f'game_accounts:{user_id}'

class GameAccountViewSet(viewsets.ModelViewSet):
    serializer_class = GameAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (GameAccount.objects.filter(user=self.request.user).prefetch_related('snapshots').order_by('-created_at'))
    
    def list(self,request,*args,**kwargs):
        cache_key = _list_cache_key(request.user.id)
        cached = cache.get(cache_key)
        if cached is None:
            return Response(cached)
        
        response = super().list(request,*args,**kwargs)
        cache.set(cache_key,response.data,timeout=LIST_CACHE_TIMEOUT)
        return response 
    
    def create(self,request,*args,**kwargs):
        platform = request.data.get('platform')
        existing_count = GameAccount.objects.filter(
            user=request.user,platform=platform
        ).count()
        if existing_count >= MAX_ACCOUNTS_PER_PLATFORM:
            return Response (
                {'detail': f'Уже подключен аккаунт для платформы{platform}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response = super().create(request,*args,**kwargs)
        cache.delete(_list_cache_key(request.user.id))
        return response
    
    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request,*args,**kwargs)
        cache.delete(_list_cache_key(request.user.id))
        return response 
    
    @action(detail=True,methods=['post'])
    def sync(self,request,pk=None):
        account = self.get_object()
        cooldown_key = f'profile_sync_cooldown:{account.id}'

        if cache.get(cooldown_key):
            return Response(
                {'detail':'Синхронизация уже запускалась недавно, попробуй через несколько секунд'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        sync_single_account.delay(account.id)
        cache.set(cooldown_key,True,timeout=SYNC_COOLDOWN_SECONDS)

        return Response({'detail':'Синхронизация запущена, обнови страничку если не появилась'})
    
    @action(detail=True,methods=['get'])
    def summary(self,request,pk=None):
        account = self.get_object()
        return Response(get_account_summary(account))