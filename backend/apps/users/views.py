from django.shortcuts import redirect
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import get_user, get_user_model
from django.db.models import Q
from django.middleware.csrf import get_token
from django.conf import settings
from django.db import connection

from .xp import (
    get_or_create_profile,
    progress_payload,
    add_xp,
    XP_REFERRAL_INVITER,
    XP_REFERRAL_INVITEE,
)
from .services import notify
from .models import UserProfile, Notification
from .serializers import UserProfileSerializer
from .auth_cookies import set_auth_cookie, clear_auth_cookie


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"detail": "CSRF cookie set"})


@ensure_csrf_cookie
def steam_start(request):
    token = get_token(request)
    html = f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"/><title>Steam</title></head>
<body>
<form id="f" method="post" action="/auth/login/steam/">
  <input type="hidden" name="csrfmiddlewaretoken" value="{token}">
</form>
<script>document.getElementById('f').submit()</script>
</body>
</html>"""
    return HttpResponse(html)
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        response = Response(
            {"detail": "Вы успешно вышли из аккаунта"},
            status=status.HTTP_200_OK,
        )
        clear_auth_cookie(response)
        return response


class SteamAuthCompleteView(APIView):
    """
    После Steam: токен только в HttpOnly cookie.
    В URL и JSON токен больше НЕ отдаём.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = get_user(request)

        if not user.is_authenticated:
            return Response(
                {"detail": "Пользователь не найден"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token, _ = Token.objects.get_or_create(user=user)

        response = redirect(f"{settings.FRONTEND_URL}/auth/callback")
        set_auth_cookie(response, token.key)
        return response


class SteamAuthErrorView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {"detail": "Не удалось войти через Steam, попробуйте позже"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class PlayerSearchView(APIView):
    """GET /api/players/search/?q=be"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        User = get_user_model()
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 1:
            return Response([])

        qs = (
            User.objects.filter(
                Q(username__icontains=q)
                | Q(profile__display_name__icontains=q)
            )
            .select_related("profile")
            .distinct()[:8]
        )

        data = []
        for u in qs:
            profile = getattr(u, "profile", None)
            data.append({
                "id": u.id,
                "username": u.username,
                "display_name": (
                    profile.display_name
                    if profile and getattr(profile, "display_name", None)
                    else u.username
                ),
                "avatar_url": getattr(profile, "avatar_url", None) if profile else None,
            })
        return Response(data)


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)[:40]
        return Response([
            {
                "id": n.id,
                "kind": n.kind,
                "title": n.title,
                "body": n.body,
                "link": n.link,
                "read": n.read,
                "created_at": n.created_at,
            }
            for n in qs
        ])


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ids = request.data.get("ids")
        qs = Notification.objects.filter(user=request.user, read=False)
        if ids:
            qs = qs.filter(id__in=ids)
        updated = qs.update(read=True)
        return Response({"ok": True, "updated": updated})


class ProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        return Response(progress_payload(profile))


class ReferralClaimView(APIView):
    """POST { "code": "A1B2C3D4" } — один раз на аккаунт"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = (request.data.get("code") or "").strip().upper()
        if not code:
            return Response({"detail": "Укажи код"}, status=status.HTTP_400_BAD_REQUEST)

        me = get_or_create_profile(request.user)
        if me.referred_by_id:
            return Response(
                {"detail": "Реферал уже активирован"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if me.referral_code and me.referral_code.upper() == code:
            return Response(
                {"detail": "Нельзя ввести свой код"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inviter_profile = (
            UserProfile.objects.filter(referral_code__iexact=code)
            .select_related("user")
            .first()
        )
        if not inviter_profile:
            return Response({"detail": "Код не найден"}, status=status.HTTP_404_NOT_FOUND)

        me.referred_by = inviter_profile.user
        me.boost_credits = (me.boost_credits or 0) + 1
        me.save(update_fields=["referred_by", "boost_credits", "updated_at"])

        add_xp(request.user, XP_REFERRAL_INVITEE, reason="реферал")
        add_xp(inviter_profile.user, XP_REFERRAL_INVITER, reason="друг по рефке")

        inviter_profile.boost_credits = (inviter_profile.boost_credits or 0) + 1
        inviter_profile.save(update_fields=["boost_credits"])

        try:
            notify(
                inviter_profile.user,
                kind="referral",
                title="Реферал сработал",
                body=(
                    f"{request.user.username} пришёл по твоему коду "
                    f"· +{XP_REFERRAL_INVITER} XP"
                ),
                link="/profile",
            )
        except Exception:
            pass

        me.refresh_from_db()
        return Response({
            "detail": "Реферал активирован",
            "progress": progress_payload(me),
        })


def health(request):
    try:
        connection.ensure_connection()
        db = "ok"
    except Exception:
        return JsonResponse({"status": "error", "db": "error"}, status=503)
    return JsonResponse({"status": "ok", "db": db})