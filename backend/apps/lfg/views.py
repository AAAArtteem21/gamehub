from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.display import user_public_name

from .models import LFGPost, LFGResponse, ContactReveal, LFGChatMessage
from .serializers import LFGPostSerializer, LFGResponseSerializer, LFGChatMessageSerializer
from .permissions import IsAuthorOrReadOnly, IsResponseOwnerOrReadOnly


class LFGPostViewSet(viewsets.ModelViewSet):
    serializer_class = LFGPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_queryset(self):
        qs = (
            LFGPost.objects.select_related("author", "author__profile")
            .annotate(
                accepted_count_annotated=Count(
                    "responses", filter=Q(responses__status="accepted")
                ),
                pending_count_annotated=Count(
                    "responses", filter=Q(responses__status="pending")
                ),
                responses_count_annotated=Count(
                    "responses", filter=Q(responses__status="accepted")
                ),
            )
            .order_by("-created_at")
        )
        game = self.request.query_params.get("game")
        status_param = self.request.query_params.get("status")
        search = self.request.query_params.get("search")

        if game:
            qs = qs.filter(game__iexact=game)
        if search:
            qs = qs.filter(Q(game__icontains=search) | Q(description__icontains=search))
        if status_param:
            qs = qs.filter(status=status_param)
        else:
            qs = qs.filter(status="open")
            cutoff = timezone.now() - timedelta(hours=1)
            qs = qs.exclude(datetime__lt=cutoff)

        return qs

    @method_decorator(ratelimit(key="user", rate="5/h", block=True))
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def close(self, request, pk=None):
        post = self.get_object()
        if post.author_id != request.user.id:
            return Response(
                {"detail": "Только автор может закрыть заявку"},
                status=status.HTTP_403_FORBIDDEN,
            )
        post.status = "closed"
        post.save(update_fields=["status"])
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def applications(self, request, pk=None):
        """Список заявок на пост — только автор."""
        post = self.get_object()
        if post.author_id != request.user.id:
            return Response({"detail": "Только автор"}, status=status.HTTP_403_FORBIDDEN)
        qs = (
            post.responses.select_related("user", "user__profile")
            .exclude(status="withdrawn")
            .order_by("status", "-created_at")
        )
        # pending сверху
        qs = sorted(
            qs,
            key=lambda r: (0 if r.status == "pending" else 1, -r.created_at.timestamp()),
        )
        return Response(LFGResponseSerializer(qs, many=True, context={"request": request}).data)


class LFGResponseViewSet(viewsets.ModelViewSet):
    serializer_class = LFGResponseSerializer
    permission_classes = [permissions.IsAuthenticated, IsResponseOwnerOrReadOnly]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = LFGResponse.objects.select_related(
            "user", "user__profile", "post", "post__author", "post__author__profile"
        )
        post_id = self.request.query_params.get("post")
        if post_id:
            qs = qs.filter(post_id=post_id)
        # обычный list: свои заявки или заявки на свои посты
        if not post_id:
            user = self.request.user
            qs = qs.filter(
                Q(user=user) | Q(post__author=user)
            ).exclude(status="withdrawn")
        return qs

    def destroy(self, request, *args, **kwargs):
        """Отозвать свою pending-заявку или кик accepted автором."""
        obj = self.get_object()
        user = request.user
        if obj.user_id == user.id:
            if obj.status not in ("pending", "accepted"):
                return Response({"detail": "Нельзя отозвать"}, status=400)
            obj.status = "withdrawn"
            obj.decided_at = timezone.now()
            obj.save(update_fields=["status", "decided_at"])
            return Response(status=status.HTTP_204_NO_CONTENT)
        if obj.post.author_id == user.id:
            # автор убирает игрока
            obj.status = "rejected"
            obj.decided_at = timezone.now()
            obj.save(update_fields=["status", "decided_at"])
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Нет прав"}, status=403)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def accept(self, request, pk=None):
        resp = self.get_object()
        post = resp.post
        if post.author_id != request.user.id:
            return Response({"detail": "Только автор"}, status=403)
        if resp.status != "pending":
            return Response({"detail": "Заявка уже обработана"}, status=400)
        if post.status == "closed":
            return Response({"detail": "Пост закрыт"}, status=400)

        resp.status = "accepted"
        resp.decided_at = timezone.now()
        resp.save(update_fields=["status", "decided_at"])

        # открыть контакт принятому
        ContactReveal.objects.update_or_create(
            user=resp.user,
            post=post,
            defaults={
                "contact": post.contact,
                "expires_at": timezone.now() + timedelta(hours=24),
            },
        )

        post.refresh_slots_status()

        try:
            from apps.users.services import notify
            notify(
                resp.user,
                kind="lfg_accepted",
                title="Заявка принята",
                body=f"Тебя взяли в «{post.game}» · {post.datetime:%d.%m %H:%M}",
                link=f"/lfg/{post.id}",
            )
        except Exception:
            pass

        return Response(
            LFGResponseSerializer(resp, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        resp = self.get_object()
        post = resp.post
        if post.author_id != request.user.id:
            return Response({"detail": "Только автор"}, status=403)
        if resp.status != "pending":
            return Response({"detail": "Заявка уже обработана"}, status=400)

        resp.status = "rejected"
        resp.decided_at = timezone.now()
        resp.save(update_fields=["status", "decided_at"])

        try:
            from apps.users.services import notify
            notify(
                resp.user,
                kind="lfg_rejected",
                title="Заявка отклонена",
                body=f"По «{post.game}» заявка отклонена",
                link=f"/lfg/{post.id}",
            )
        except Exception:
            pass

        return Response(
            LFGResponseSerializer(resp, context={"request": request}).data
        )


class LFGChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = LFGChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        qs = LFGChatMessage.objects.select_related("sender", "sender__profile", "post")
        post_id = self.request.query_params.get("post")
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs


class MyApplicationsView(APIView):
    """
    Ближайшие матчи, на которые подал заявку (pending + accepted).
    Сортировка по datetime поста.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now() - timedelta(hours=2)
        qs = (
            LFGResponse.objects.filter(
                user=request.user,
                status__in=["pending", "accepted"],
                post__datetime__gte=now,
            )
            .select_related("post", "post__author", "post__author__profile", "user", "user__profile")
            .order_by("post__datetime")
        )
        return Response(
            LFGResponseSerializer(qs, many=True, context={"request": request}).data
        )


class MyNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        reveals = (
            ContactReveal.objects.filter(user=request.user, expires_at__gt=now)
            .select_related("post")
            .order_by("-revealed_at")
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
        # чат только у author + accepted
        post_ids = set(LFGPost.objects.filter(author=user).values_list("id", flat=True))
        post_ids |= set(
            LFGResponse.objects.filter(user=user, status="accepted").values_list(
                "post_id", flat=True
            )
        )

        threads = []
        for post in LFGPost.objects.filter(id__in=post_ids).select_related(
            "author", "author__profile"
        ):
            last_msg = post.chat_messages.order_by("-created_at").first()
            threads.append({
                "post_id": post.id,
                "game": post.game,
                "author": user_public_name(post.author),
                "last_message": last_msg.text if last_msg else None,
                "last_message_at": last_msg.created_at if last_msg else post.created_at,
            })
        threads.sort(key=lambda t: t["last_message_at"], reverse=True)
        return Response(threads)


class QuickStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.clans.models import ClanMembership

        user = request.user
        return Response({
            "open_lfg": LFGPost.objects.filter(author=user, status="open").count(),
            "pending_applications": LFGResponse.objects.filter(
                post__author=user, status="pending"
            ).count(),
            "my_pending": LFGResponse.objects.filter(
                user=user, status="pending"
            ).count(),
            "unread_chats": 0,
            "clans_count": ClanMembership.objects.filter(user=user).count(),
        })