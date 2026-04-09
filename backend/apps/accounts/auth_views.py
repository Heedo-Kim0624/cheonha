from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class LoginView(APIView):
    """프론트엔드 로그인 API - {token, user} 형태로 응답"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'detail': '이메일과 비밀번호를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # email로 유저를 찾아서 username으로 인증
        user = None
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            # username으로 직접 시도
            user = authenticate(request, username=email, password=password)

        if user is None or not user.is_active:
            return Response(
                {'detail': '사용자 인증에 실패했습니다. 이메일 또는 비밀번호를 확인하세요.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        user_data = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'role': getattr(user, 'role', None),
            'team': user.team_id if hasattr(user, 'team_id') else None,
            'team_code': user.team.code if hasattr(user, 'team') and user.team else None,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }

        return Response({
            'token': access_token,
            'refresh': str(refresh),
            'user': user_data,
        })


class RefreshTokenView(APIView):
    """토큰 갱신"""
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'refresh 토큰이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            refresh = RefreshToken(refresh_token)
            return Response({
                'token': str(refresh.access_token),
                'refresh': str(refresh),
            })
        except Exception:
            return Response(
                {'detail': '유효하지 않은 토큰입니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class ProfileView(APIView):
    """현재 로그인한 사용자 프로필"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_data = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'role': getattr(user, 'role', None),
            'team': user.team_id if hasattr(user, 'team_id') else None,
            'team_code': user.team.code if hasattr(user, 'team') and user.team else None,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': getattr(user, 'phone', None),
        }
        return Response(user_data)


class LogoutView(APIView):
    """로그아웃 (클라이언트에서 토큰 삭제)"""
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({'detail': '로그아웃 되었습니다.'})


class SignupView(APIView):
    """팀장 회원가입 - 관리자 승인 필요"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        first_name = request.data.get('first_name', '')
        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')
        team_code = request.data.get('team_code')

        if not all([username, password, password_confirm]):
            return Response({'detail': '아이디와 비밀번호를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        if password != password_confirm:
            return Response({'detail': '비밀번호가 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'detail': '이미 사용 중인 아이디입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        from .models import Team
        team = None
        if team_code:
            try:
                team = Team.objects.get(code=team_code)
            except Team.DoesNotExist:
                return Response({'detail': '존재하지 않는 팀입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            email=f'{username}@cheonha.local',
            password=password,
            first_name=first_name,
            role='TEAM_LEADER',
            team=team,
            is_active=False,  # 관리자 승인 전까지 비활성
        )

        return Response({'detail': '회원가입이 완료되었습니다. 관리자 승인 후 로그인할 수 있습니다.'}, status=status.HTTP_201_CREATED)
