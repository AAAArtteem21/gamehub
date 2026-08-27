from django import views
from django.shortcuts import render
from rest_framework import viewsets,permissions,status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from rest_framework.views import APIView

from .models import Clan,ClanMembership
from .serializers import (
    ClanSerializer,ClanDashboardEntrySerializer,
    JoinClanSerializer,ClanMembershipSerializer
)
from .permissions import IsOwnerOrReadOnly
from .services import get_clan_dashboard,join_clan_by_invite_code


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
    """GET /api/clans/leaderboard/ — топ кланов по суммарной активности участников за месяц"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .services import _period_activity
        from django.utils import timezone as dj_timezone
        from datetime import timedelta

        today = dj_timezone.now().date()
        month_ago = today - timedelta(days=30)

        clans = Clan.objects.annotate(members_count_annotated=Count("memberships"))
        result = []
        for clan in clans:
            user_ids = list(ClanMembership.objects.filter(clan=clan).values_list("user_id", flat=True))
            if not user_ids:
                continue
            activity = _period_activity(user_ids, month_ago, today)
            total_minutes = sum(activity.values())
            result.append({
                "id": clan.id,
                "name": clan.name,
                "logo": clan.logo,
                "members_count": clan.members_count_annotated,
                "total_month_minutes": total_minutes,
            })

        result.sort(key=lambda c: c["total_month_minutes"], reverse=True)
        return Response(result[:10])