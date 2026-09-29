from django import views
from django.shortcuts import render
from rest_framework import viewsets,permissions,status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Clan,ClanMembership
from .serializers import (
    ClanSerializer,ClanDashboardEntrySerializer,
    JoinClanSerializer,ClanMembershipSerializer
)
from .utils import clan_logo_url
from .permissions import IsOwnerOrReadOnly
from .services import get_clan_dashboard,join_clan_by_invite_code
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .models import Clan, ClanMembership, ClanMessage

class ClanViewSet(viewsets.ModelViewSet):
    serializer_class = ClanSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsOwnerOrReadOnly]
    
    def get_queryset(self):
        return (
            Clan.objects.
            select_related('owner')
            .annotate(members_count_annotated=Count('memberships'))
            .order_by('-created_at')
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_logo(self, request, pk=None):
        from .utils import clan_logo_url
        from .serializers import MAX_LOGO_SIZE, ALLOWED_LOGO_TYPES

        clan = self.get_object()
        membership = ClanMembership.objects.filter(clan=clan, user=request.user).first()
        if not membership or membership.role != "leader":
            return Response({"detail": "Только лидер может менять аватар"}, status=403)

        f = request.FILES.get("logo")
        if not f:
            return Response({"detail": "Нет файла logo"}, status=400)
        if f.size > MAX_LOGO_SIZE:
            return Response({"detail": "Максимум 2 МБ"}, status=400)
        ct = getattr(f, "content_type", None)
        if ct and ct not in ALLOWED_LOGO_TYPES:
            return Response({"detail": "Только JPEG, PNG, WebP, GIF"}, status=400)

        # удалить старый файл при замене (опционально)
        if clan.logo:
            try:
                clan.logo.delete(save=False)
            except Exception:
                pass

        clan.logo = f
        clan.save(update_fields=["logo"])

        url = clan_logo_url(clan, request)
        return Response({"logo": url, "logo_url": url})
    
    @action(detail=False,methods=['post'],permission_classes=[permissions.IsAuthenticated])
    def join(self,request):
        serializer = JoinClanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            membership = join_clan_by_invite_code(
                request.user,serializer.validated_data['invite_code']
            )
        except ValueError as e:
            return Response({'detail':str(e)},status=status.HTTP_400_BAD_REQUEST)

        return Response(ClanMembershipSerializer(membership).data,status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def dashboard(self, request, pk=None):
        clan = self.get_object()

        is_member = ClanMembership.objects.filter(clan=clan, user=request.user).exists()
        if not is_member:
            return Response(
                {"detail": "Дашборд доступен только участникам клана"},
                status=status.HTTP_403_FORBIDDEN
            )

        data = get_clan_dashboard(clan)
        serializer = ClanDashboardEntrySerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def members(self, request, pk=None):
        clan = self.get_object()
        memberships = clan.memberships.select_related("user").order_by("role", "joined_at")
        serializer = ClanMembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def kick(self, request, pk=None):
        clan = self.get_object()
        target_user_id = request.data.get("user_id")

        requester_membership = ClanMembership.objects.filter(clan=clan, user=request.user).first()
        if not requester_membership or requester_membership.role not in ("leader", "officer"):
            return Response({"detail": "Только лидер или офицер могут исключать участников"}, status=status.HTTP_403_FORBIDDEN)

        target_membership = ClanMembership.objects.filter(clan=clan, user_id=target_user_id).first()
        if not target_membership:
            return Response({"detail": "Участник не найден"}, status=status.HTTP_404_NOT_FOUND)

        if target_membership.role == "leader":
            return Response({"detail": "Нельзя исключить лидера клана"}, status=status.HTTP_400_BAD_REQUEST)

        target_membership.delete()
        return Response({"detail": "Участник исключён"})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def leave(self, request, pk=None):
        clan = self.get_object()
        membership = ClanMembership.objects.filter(clan=clan, user=request.user).first()

        if not membership:
            return Response({"detail": "Ты не состоишь в этом клане"}, status=status.HTTP_400_BAD_REQUEST)
        if membership.role == "leader":
            return Response(
                {"detail": "Лидер не может покинуть клан — сначала передай лидерство или удали клан"},
                status=status.HTTP_400_BAD_REQUEST
            )

        membership.delete()
        return Response({"detail": "Ты покинул клан"}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def change_role(self, request, pk=None):
        clan = self.get_object()
        target_user_id = request.data.get("user_id")
        new_role = request.data.get("role")

        if new_role not in ("member", "officer", "leader"):
            return Response({"detail": "Недопустимая роль"}, status=status.HTTP_400_BAD_REQUEST)

        requester_membership = ClanMembership.objects.filter(clan=clan, user=request.user).first()
        if not requester_membership or requester_membership.role != "leader":
            return Response({"detail": "Только лидер может менять роли"}, status=status.HTTP_403_FORBIDDEN)

        target_membership = ClanMembership.objects.filter(clan=clan, user_id=target_user_id).first()
        if not target_membership:
            return Response({"detail": "Участник не найден"}, status=status.HTTP_404_NOT_FOUND)

        if new_role == "leader":
            requester_membership.role = "officer"
            requester_membership.save(update_fields=["role"])

        target_membership.role = new_role
        target_membership.save(update_fields=["role"])
        return Response({"detail": "Роль обновлена"})


class ClanLeaderboardView(APIView):
    """GET /api/clans/leaderboard/ — топ кланов по активности за 30 дней"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .services import _period_activity
        from django.utils import timezone as dj_timezone
        from datetime import timedelta
        from django.db.models import Count

        today = dj_timezone.now().date()
        month_ago = today - timedelta(days=30)

        clans = Clan.objects.annotate(members_count_annotated=Count("memberships"))
        result = []

        for clan in clans:
            user_ids = list(
                ClanMembership.objects.filter(clan=clan).values_list("user_id", flat=True)
            )
            if not user_ids:
                continue

            activity = _period_activity(user_ids, month_ago, today)
            total_minutes = int(sum(activity.values()))

            logo_url = None
            if clan.logo:
                try:
                    logo_url = clan.logo.url
                except ValueError:
                    logo_url = None

            result.append({
                "id": clan.id,
                "name": clan.name,
                "logo": clan_logo_url(clan, request),
                "members_count": clan.members_count_annotated,
                "total_month_minutes": total_minutes,
            })

        result.sort(key=lambda c: c["total_month_minutes"], reverse=True)
        return Response(result[:15])

class MyClansPanelView(APIView):
    """GET /api/clans/my-panel/ — до 3 кланов: лента + чат"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        memberships = (
            ClanMembership.objects
            .filter(user=request.user)
            .select_related("clan")
            .order_by("-joined_at")[:3]
        )
        result = []
        for m in memberships:
            clan = m.clan
            logo = None
            try:
                if clan.logo:
                    logo = clan.logo.url
            except Exception:
                logo = None

            feed = []
            try:
                from apps.profiles.models import ClanActivity
                acts = (
                    ClanActivity.objects
                    .filter(clan=clan)
                    .select_related("user")
                    .order_by("-created_at")[:15]
                )
                for a in acts:
                    feed.append({
                        "id": a.id,
                        "username": a.user.username if a.user_id else "?",
                        "text": a.text,
                        "kind": a.kind,
                        "created_at": a.created_at,
                    })
            except Exception:
                pass

            msgs = (
                ClanMessage.objects
                .filter(clan=clan)
                .select_related("sender")
                .order_by("-created_at")[:40]
            )
            msgs = list(reversed(list(msgs)))
            user_ids = [x.sender_id for x in msgs]
            role_map = dict(
                ClanMembership.objects.filter(clan=clan, user_id__in=user_ids)
                .values_list("user_id", "role")
            )
            messages = [{
                "id": msg.id,
                "text": msg.text,
                "created_at": msg.created_at,
                "sender_id": msg.sender_id,
                "sender_username": msg.sender.username,
                "role": role_map.get(msg.sender_id, "member"),
            } for msg in msgs]

            result.append({
                "clan_id": clan.id,
                "clan_name": clan.name,
                "my_role": m.role,
                "logo": clan_logo_url(clan, request),
                "feed": feed,
                "messages": messages,
            })
        return Response(result)


class ClanMessagesView(APIView):
    """GET/POST /api/clans/<id>/messages/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, clan_id):
        if not ClanMembership.objects.filter(clan_id=clan_id, user=request.user).exists():
            return Response({"detail": "Только участники"}, status=status.HTTP_403_FORBIDDEN)
        msgs = (
            ClanMessage.objects
            .filter(clan_id=clan_id)
            .select_related("sender")
            .order_by("-created_at")[:50]
        )
        msgs = list(reversed(list(msgs)))
        role_map = dict(
            ClanMembership.objects.filter(clan_id=clan_id).values_list("user_id", "role")
        )
        return Response([{
            "id": m.id,
            "text": m.text,
            "created_at": m.created_at,
            "sender_id": m.sender_id,
            "sender_username": m.sender.username,
            "role": role_map.get(m.sender_id, "member"),
        } for m in msgs])

    def post(self, request, clan_id):
        mem = ClanMembership.objects.filter(clan_id=clan_id, user=request.user).first()
        if not mem:
            return Response({"detail": "Только участники"}, status=status.HTTP_403_FORBIDDEN)
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "Пустое сообщение"}, status=status.HTTP_400_BAD_REQUEST)
        if len(text) > 1000:
            return Response({"detail": "Слишком длинное"}, status=status.HTTP_400_BAD_REQUEST)
        m = ClanMessage.objects.create(clan_id=clan_id, sender=request.user, text=text)
        return Response({
            "id": m.id,
            "text": m.text,
            "created_at": m.created_at,
            "sender_id": request.user.id,
            "sender_username": request.user.username,
            "role": mem.role,
        }, status=status.HTTP_201_CREATED)
