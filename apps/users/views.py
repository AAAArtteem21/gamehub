from django.shortcuts import redirect
from rest_framework import generics,permissions,status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response 
from rest_framework.views import APIView

from .models import UserProfile
from .serializers import UserProfileSerializer

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes =[permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile 
    
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request):
        Token.objects.filter(user=request.user).delete()
        return Response({'detail':'Вы успешно вышли из аккаунта'},status=status.HTTP_200_OK)
    
class SteamAuthCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self,request):
        token, _ =Token.objects.get_or_create(user=request.user)
        frontend_url = f'http://localhost:5173/auth/callback?token={token.key}'
        return redirect(frontend_url)
    
class SteamAuthErrorView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self,request):
        return Response(
            {'detail':'Не удалось найти аккаунт стим попробуйте позже'},
            status=status.HTTP_400_BAD_REQUEST
        )