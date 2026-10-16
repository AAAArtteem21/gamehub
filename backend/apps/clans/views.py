from django.db.models import Count
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from apps.users.display import user_public_name

from .models import Clan, ClanMembership, ClanMessage, ClanBan, ClanModerationLog
from .serializers import (
    ClanSerializer,
    ClanDashboardEntrySerializer,
    JoinClanSerializer,
    ClanMembershipSerializer,
    MAX_LOGO_SIZE,
    ALLOWED_LOGO_TYPES,
)
from .utils import clan_logo_url
from .permissions import IsOwnerOrReadOnly
from .services import get_clan_dashboard, join_clan_by_invite_code, join_open_clan


class ClanViewSet(viewsets.ModelViewSet):
    serializer_class = ClanSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        return (
            Clan.objects.select_related("owner")
            .annotate(members_count_annotated=Count("memberships"))
            .order_by("-created_at")
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_logo(self, request, pk=None):
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
        if clan.logo:
            try:
                clan.logo.delete(save=False)
            except Exception:
                pass
        clan.logo = f
        clan.save(update_fields=["logo"])
        url = clan_logo_url(clan, request)
        return Response({"logo": url, "logo_url": url})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def join(self, request):
        serializer = JoinClanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            if data.get("clan_id") and not (data.get("invite_code") or "").strip():
                membership = join_open_clan(request.user, data["clan_id"])
            else:
                membership = join_clan_by_invite_code(
                    request.user, data.get("invite_code") or ""
                )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ClanMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def dashboard(self, request, pk=None):
        clan = self.get_object()
        if not ClanMembership.objects.filter(clan=clan, user=request.user).exists():
            return Response(
                {"detail": "Дашборд доступен только участникам клана"},
                status=status.HTTP_403_FORBIDDEN,
            )
        data = get_clan_dashboard(clan)
        return Response(ClanDashboardEntrySerializer(data, many=True).data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def members(self, request, pk=None):
        clan = self.get_object()
        memberships = (
            clan.memberships.select_related("user", "user__profile")
            .order_by("role", "joined_at")
        )
        return Response(ClanMembershipSerializer(memberships, many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def kick(self, request, pk=None):
        clan = self.get_object()
        target_user_id = request.data.get("user_id")
        requester = ClanMembership.objects.filter(clan=clan, user=request.user).first()
        if not requester or requester.role not in ("leader", "officer"):
            return Response({"detail": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)
        target = ClanMembership.objects.filter(clan=clan, user_id=target_user_id).first()
        if not target:
            return Response({"detail": "Участник не найден"}, status=404)
        if target.role == "leader":
            return Response({"detail": "Нельзя исключить лидера"}, status=400)
        if requester.role == "officer" and target.role == "officer":
            return Response({"detail": "Офицер не может кикать офицера"}, status=403)
        target_user = target.user
        target.delete()
        ClanModerationLog.objects.create(
            clan=clan,
            action=ClanModerationLog.ACTION_KICK,
            actor=request.user,
            target=target_user,
            reason=(request.data.get("reason") or "")[:255],
        )
        return Response({"detail": "Участник исключён"})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def leave(self, request, pk=None):
        clan = self.get_object()
        membership = ClanMembership.objects.filter(clan=clan, user=request.user).first()
        if not membership:
            return Response({"detail": "Ты не состоишь в этом клане"}, status=400)
        if membership.role == "leader":
            return Response(
                {"detail": "Лидер не может выйти — передай лидерство или удали клан"},
                status=400,
            )
        membership.delete()
        return Response({"detail": "Ты покинул клан"})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def change_role(self, request, pk=None):
        clan = self.get_object()
        target_user_id = request.data.get("user_id")
        new_role = request.data.get("role")
        if new_role not in ("member", "officer", "leader"):
            return Response({"detail": "Недопустимая роль"}, status=400)
        requester = ClanMembership.objects.filter(clan=clan, user=request.user).first()
        if not requester or requester.role != "leader":
            return Response({"detail": "Только лидер"}, status=403)
        target = ClanMembership.objects.filter(clan=clan, user_id=target_user_id).first()
        if not target:
            return Response({"detail": "Участник не найден"}, status=404)
        if new_role == "leader":
            requester.role = "officer"
            requester.save(update_fields=["role"])
        target.role = new_role
        target.save(update_fields=["role"])
        return Response({"detail": "Роль обновлена"})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def ban(self, request, pk=None):
        clan = self.get_object()
        requester = ClanMembership.objects.filter(clan=clan, user=request.user).first()
        if not requester or requester.role not in ("leader", "officer"):
            return Response({"detail": "Нет прав"}, status=403)
        uid = request.data.get("user_id")
        reason = (request.data.get("reason") or "")[:255]
        target_m = ClanMembership.objects.filter(clan=clan, user_id=uid).first()
        if target_m and target_m.role == "leader":
            return Response({"detail": "Нельзя банить лидера"}, status=400)
        if requester.role == "officer" and target_m and target_m.role == "officer":
            return Response({"detail": "Офицер не может банить офицера"}, status=403)
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.filter(id=uid).first()
        if not user:
            return Response({"detail": "Юзер не найден"}, status=404)
        if target_m:
            target_m.delete()
        ban, _ = ClanBan.objects.update_or_create(
            clan=clan,
            user=user,
            defaults={"banned_by": request.user, "reason": reason},
        )
        ClanModerationLog.objects.create(
            clan=clan,
            action=ClanModerationLog.ACTION_BAN,
            actor=request.user,
            target=user,
            reason=reason,
        )
        return Response({"detail": "Забанен", "ban_id": ban.id})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def unban(self, request, pk=None):
        clan = self.get_object()
        requester = ClanMembership.objects.filter(clan=clan, user=request.user).first()
        if not requester or requester.role not in ("leader", "officer"):
            return Response({"detail": "Нет прав"}, status=403)
        uid = request.data.get("user_id")
        deleted, _ = ClanBan.objects.filter(clan=clan, user_id=uid).delete()
        if deleted:
            from django.contrib.auth import get_user_model
            t = get_user_model().objects.filter(id=uid).first()
            ClanModerationLog.objects.create(
                clan=clan,
                action=ClanModerationLog.ACTION_UNBAN,
                actor=request.user,
                target=t,
                reason=(request.data.get("reason") or "")[:255],
            )
        return Response({"detail": "Разбанен" if deleted else "Не был в бане"})

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def mod_log(self, request, pk=None):
        clan = self.get_object()
        if not ClanMembership.objects.filter(clan=clan, user=request.user).exists():
            return Response({"detail": "Только участники"}, status=403)
        logs = (
            ClanModerationLog.objects.filter(clan=clan)
            .select_related("actor", "actor__profile", "target", "target__profile")[:50]
        )
        return Response([{
            "id": x.id,
            "action": x.action,
            "actor": user_public_name(x.actor),
            "target": user_public_name(x.target),
            "reason": x.reason,
            "created_at": x.created_at,
        } for x in logs])

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def bans(self, request, pk=None):
        clan = self.get_object()
        mem = ClanMembership.objects.filter(clan=clan, user=request.user).first()
        if not mem or mem.role not in ("leader", "officer"):
            return Response({"detail": "Только лидер/офицер"}, status=403)
        rows = ClanBan.objects.filter(clan=clan).select_related("user", "user__profile")
        return Response([{
            "user_id": b.user_id,
            "username": user_public_name(b.user),
            "reason": b.reason,
            "created_at": b.created_at,
        } for b in rows])


class ClanLeaderboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from collections import defaultdict
        from .services import get_users_playtime

        pairs = list(ClanMembership.objects.values_list("clan_id", "user_id"))
        users_by_clan = defaultdict(list)
        for clan_id, user_id in pairs:
            users_by_clan[clan_id].append(user_id)
        stats = get_users_playtime({uid for _, uid in pairs})
        clans = Clan.objects.filter(id__in=users_by_clan.keys()).annotate(
            members_count_annotated=Count("memberships")
        )
        result = []
        for clan in clans:
            two_weeks = sum(
                stats.get(u, {}).get("two_weeks", 0) for u in users_by_clan[clan.id]
            )
            total = sum(stats.get(u, {}).get("total", 0) for u in users_by_clan[clan.id])
            result.append({
                "id": clan.id,
                "name": clan.name,
                "logo": clan_logo_url(clan, request),
                "members_count": clan.members_count_annotated,
                "game": getattr(clan, "game", None),
                "is_open": getattr(clan, "is_open", True),
                "total_two_weeks_minutes": two_weeks,
                "total_minutes": total,
            })
        result.sort(
            key=lambda c: (c["total_two_weeks_minutes"], c["total_minutes"]),
            reverse=True,
        )
        return Response(result[:15])


class MyClansPanelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        memberships = (
            ClanMembership.objects.filter(user=request.user)
            .select_related("clan")
            .order_by("-joined_at")[:3]
        )
        result = []
        for m in memberships:
            clan = m.clan
            feed = []
            try:
                from apps.profiles.models import ClanActivity
                acts = (
                    ClanActivity.objects.filter(clan=clan)
                    .select_related("user", "user__profile")
                    .order_by("-created_at")[:15]
                )
                for a in acts:
                    feed.append({
                        "id": a.id,
                        "username": user_public_name(a.user) if a.user_id else "?",
                        "text": a.text,
                        "kind": a.kind,
                        "created_at": a.created_at,
                    })
            except Exception:
                pass
            msgs = (
                ClanMessage.objects.filter(clan=clan)
                .select_related("sender", "sender__profile")
                .order_by("-created_at")[:40]
            )
            msgs = list(reversed(list(msgs)))
            role_map = dict(
                ClanMembership.objects.filter(
                    clan=clan, user_id__in=[x.sender_id for x in msgs]
                ).values_list("user_id", "role")
            )
            messages = [{
                "id": msg.id,
                "text": msg.text,
                "created_at": msg.created_at,
                "sender_id": msg.sender_id,
                "sender_username": user_public_name(msg.sender),
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
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, clan_id):
        if not ClanMembership.objects.filter(clan_id=clan_id, user=request.user).exists():
            return Response({"detail": "Только участники"}, status=403)
        msgs = (
            ClanMessage.objects.filter(clan_id=clan_id)
            .select_related("sender", "sender__profile")
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
            "sender_username": user_public_name(m.sender),
            "role": role_map.get(m.sender_id, "member"),
        } for m in msgs])

    def post(self, request, clan_id):
        mem = ClanMembership.objects.filter(clan_id=clan_id, user=request.user).first()
        if not mem:
            return Response({"detail": "Только участники"}, status=403)
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "Пустое сообщение"}, status=400)
        if len(text) > 1000:
            return Response({"detail": "Слишком длинное"}, status=400)
        m = ClanMessage.objects.create(clan_id=clan_id, sender=request.user, text=text)
        return Response({
            "id": m.id,
            "text": m.text,
            "created_at": m.created_at,
            "sender_id": request.user.id,
            "sender_username": user_public_name(request.user),
            "role": mem.role,
        }, status=201)