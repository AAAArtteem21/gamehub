from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.display import user_public_name
from .models import UserPresence, Friendship, FriendRequest, Acquaintance, PlayStatus
from .serializers import (
    PresenceSerializer,
    FriendRequestCreateSerializer,
    InviteSerializer,
    user_card,
    _presence_payload,
)

User = get_user_model()


def _ensure_presence(user):
    p, _ = UserPresence.objects.get_or_create(user=user)
    return p


class MyPresenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        _ensure_presence(request.user)
        return Response(_presence_payload(request.user))

    def post(self, request):
        ser = PresenceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        p = _ensure_presence(request.user)
        p.status = ser.validated_data["status"]
        p.note = ser.validated_data.get("note") or ""
        p.game = ser.validated_data.get("game") or ""
        p.save()
        return Response(_presence_payload(request.user))


class FriendsListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ids = Friendship.friend_ids_of(request.user.id)
        users = User.objects.filter(id__in=ids).select_related("profile", "presence")
        order = {
            PlayStatus.FREE: 0,
            PlayStatus.LFG: 1,
            PlayStatus.RANKED: 2,
            PlayStatus.OFFLINE: 3,
        }
        cards = [user_card(u) for u in users]
        cards.sort(
            key=lambda c: (order.get(c["presence"]["status"], 9), c["username"].lower())
        )
        return Response(cards)


class FriendRequestsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        incoming = (
            FriendRequest.objects.filter(
                to_user=request.user, status=FriendRequest.STATUS_PENDING
            )
            .select_related("from_user", "from_user__profile", "from_user__presence")
            .order_by("-created_at")
        )
        outgoing = (
            FriendRequest.objects.filter(
                from_user=request.user, status=FriendRequest.STATUS_PENDING
            )
            .select_related("to_user", "to_user__profile", "to_user__presence")
            .order_by("-created_at")
        )
        return Response(
            {
                "incoming": [
                    {
                        "id": r.id,
                        "user": user_card(r.from_user),
                        "message": r.message,
                        "created_at": r.created_at,
                    }
                    for r in incoming
                ],
                "outgoing": [
                    {
                        "id": r.id,
                        "user": user_card(r.to_user),
                        "message": r.message,
                        "created_at": r.created_at,
                    }
                    for r in outgoing
                ],
            }
        )

    def post(self, request):
        ser = FriendRequestCreateSerializer(
            data=request.data, context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        to_id = ser.validated_data["user_id"]
        msg = (ser.validated_data.get("message") or "").strip()
        fr = FriendRequest.objects.create(
            from_user=request.user,
            to_user_id=to_id,
            message=msg,
        )
        try:
            from apps.users.services import notify

            notify(
                User.objects.get(id=to_id),
                kind="friend_request",
                title="Заявка в друзья",
                body=f"{user_public_name(request.user)} хочет добавить тебя в друзья",
                link="/",
            )
        except Exception:
            pass
        return Response({"id": fr.id, "status": fr.status}, status=status.HTTP_201_CREATED)


class FriendRequestActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, action):
        try:
            fr = FriendRequest.objects.select_related("from_user", "to_user").get(pk=pk)
        except FriendRequest.DoesNotExist:
            return Response({"detail": "Не найдено"}, status=404)

        if action == "accept":
            if fr.to_user_id != request.user.id:
                return Response({"detail": "Нет прав"}, status=403)
            if not fr.accept():
                return Response({"detail": "Уже обработано"}, status=400)
            try:
                from apps.users.services import notify

                notify(
                    fr.from_user,
                    kind="friend_accepted",
                    title="Заявка принята",
                    body=f"{user_public_name(request.user)} принял(а) заявку в друзья",
                    link="/",
                )
            except Exception:
                pass
            return Response({"status": "accepted"})

        if action == "reject":
            if fr.to_user_id != request.user.id:
                return Response({"detail": "Нет прав"}, status=403)
            if fr.status != FriendRequest.STATUS_PENDING:
                return Response({"detail": "Уже обработано"}, status=400)
            fr.status = FriendRequest.STATUS_REJECTED
            fr.decided_at = timezone.now()
            fr.save(update_fields=["status", "decided_at"])
            return Response({"status": "rejected"})

        if action == "cancel":
            if fr.from_user_id != request.user.id:
                return Response({"detail": "Нет прав"}, status=403)
            if fr.status != FriendRequest.STATUS_PENDING:
                return Response({"detail": "Уже обработано"}, status=400)
            fr.status = FriendRequest.STATUS_CANCELLED
            fr.decided_at = timezone.now()
            fr.save(update_fields=["status", "decided_at"])
            return Response({"status": "cancelled"})

        return Response({"detail": "Unknown action"}, status=400)


class UnfriendView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, user_id):
        a, b = Friendship.pair(request.user.id, int(user_id))
        deleted, _ = Friendship.objects.filter(user_low_id=a, user_high_id=b).delete()
        if not deleted:
            return Response({"detail": "Не друзья"}, status=404)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SuggestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        friend_ids = Friendship.friend_ids_of(request.user.id)
        pending_to = set(
            FriendRequest.objects.filter(
                from_user=request.user, status=FriendRequest.STATUS_PENDING
            ).values_list("to_user_id", flat=True)
        )
        qs = (
            Acquaintance.objects.filter(user=request.user)
            .exclude(other_id__in=friend_ids)
            .exclude(other_id=request.user.id)
            .select_related("other", "other__profile", "other__presence")
            .order_by("-created_at")[:30]
        )
        data = []
        for ac in qs:
            card = user_card(ac.other)
            card["source"] = ac.source
            card["request_sent"] = ac.other_id in pending_to
            data.append(card)
        return Response(data)


class InviteFriendView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = InviteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        uid = ser.validated_data["user_id"]
        if not Friendship.are_friends(request.user.id, uid):
            return Response({"detail": "Только друзьям"}, status=400)
        msg = (ser.validated_data.get("message") or "").strip() or "Пойдём поиграем?"
        game = (ser.validated_data.get("game") or "").strip()
        body = msg if not game else f"{msg} · {game}"
        try:
            from apps.users.services import notify

            notify(
                User.objects.get(id=uid),
                kind="play_invite",
                title=f"Приглашение от {user_public_name(request.user)}",
                body=body,
                link="/lfg/",
            )
        except Exception:
            pass
        return Response({"ok": True})


class FriendshipStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        uid = int(user_id)
        if uid == request.user.id:
            return Response({"relation": "self"})
        if Friendship.are_friends(request.user.id, uid):
            return Response({"relation": "friends"})
        if FriendRequest.objects.filter(
            from_user=request.user,
            to_user_id=uid,
            status=FriendRequest.STATUS_PENDING,
        ).exists():
            return Response({"relation": "outgoing"})
        inc = FriendRequest.objects.filter(
            from_user_id=uid,
            to_user=request.user,
            status=FriendRequest.STATUS_PENDING,
        ).first()
        if inc:
            return Response({"relation": "incoming", "request_id": inc.id})
        return Response({"relation": "none"})
