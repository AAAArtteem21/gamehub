from django.shortcuts import render
from django.core.cache import cache
from rest_framework import viewsets,permissions,status 
from rest_framework.decorators import action 
from rest_framework.response import Response 
from rest_framework.views import APIView

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
    
    def list(self, request, *args, **kwargs):
        cache_key = _list_cache_key(request.user.id)

        cached = cache.get(cache_key)

        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)

        cache.set(
            cache_key,
            response.data,
            timeout=LIST_CACHE_TIMEOUT
        )

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
    
    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        account = self.get_object()
        cooldown_key = f"profile_sync_cooldown:{account.id}"

        if cache.get(cooldown_key):
            return Response(
                {"detail": "Синхронизация уже запускалась недавно, попробуй через несколько минут"},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        try:
            ProfileSyncService(account).sync()
        except SyncError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        cache.set(cooldown_key, True, timeout=SYNC_COOLDOWN_SECONDS)
        cache.delete(_list_cache_key(request.user.id))

        return Response(self.get_serializer(account).data)
    
    @action(detail=True,methods=['get'])
    def summary(self,request,pk=None):
        account = self.get_object()
        return Response(get_account_summary(account))
    
class LeaderboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        game = request.query_params.get("game")
        qs = GameAccount.objects.filter(verified=True).exclude(extra_stats__isnull=True).select_related("user")
        if game:
            qs = qs.filter(game_label__iexact=game)

       
        accounts = list(qs)
        accounts.sort(key=lambda a: (a.skill_rating or 0, (a.extra_stats or {}).get('total_matches', 0) or (a.extra_stats or {}).get('matches', 0)), reverse=True)
        accounts = accounts[:10]

        data = [{
            "user_id": acc.user.id,
            "username": acc.user.username,
            "platform": acc.platform,
            "skill_rating": acc.skill_rating,
        } for acc in accounts]
        return Response(data)
class PublicProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Игрок не найден"}, status=404)

        accounts = GameAccount.objects.filter(user=user).prefetch_related("snapshots")
        profile = getattr(user, "profile", None)

        return Response({
            "username": user.username,
            "display_name": profile.display_name if profile else user.username,
            "avatar_url": profile.avatar_url if profile else None,
            "accounts": GameAccountSerializer(accounts, many=True, context={"request": request}).data,
        })