from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from .models import User, Team


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'code', 'name', 'leader', 'receive_price', 'pay_price', 'default_overtime_cost', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    team_detail = TeamSerializer(source='team', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'team', 'team_detail', 'phone', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},
        }


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'team', 'phone'
        ]

    def validate(self, data):
        """비밀번호 일치 확인"""
        password = data.get('password')
        password_confirm = data.pop('password_confirm', None)

        if password != password_confirm:
            raise serializers.ValidationError({'password': '비밀번호가 일치하지 않습니다.'})

        return data

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'role', 'team', 'phone', 'is_active'
        ]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT 토큰 생성 시 사용자 정보 추가"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # 사용자 정보 추가
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        token['team_code'] = user.team.code if user.team else None

        return token

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            'password': attrs['password'],
        }
        try:
            authenticate_user = authenticate(**authenticate_kwargs)
        except TypeError as exc:
            msg = _("Unable to log in with provided credentials.")
            raise serializers.ValidationError(msg, code='authentication') from exc

        if authenticate_user is None or not authenticate_user.is_active:
            raise serializers.ValidationError({
                'detail': '사용자 인증에 실패했습니다. 사용자명 또는 비밀번호를 확인하세요.'
            }, code='authentication')

        refresh = self.get_token(authenticate_user)

        data = {'refresh': str(refresh), 'access': str(refresh.access_token)}

        return data


class UserMeSerializer(serializers.ModelSerializer):
    team_detail = TeamSerializer(source='team', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'team', 'team_detail', 'phone', 'is_active'
        ]
