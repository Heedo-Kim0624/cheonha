from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.crew.models import CrewMember
from apps.common.company_scope import get_company_app_from_request

from .models import PointItem, PointRedemption, PointTransaction
from .serializers import (
    MobileRedeemPointSerializer,
    PointItemSerializer,
    PointItemWriteSerializer,
    PointRedemptionSerializer,
    PointTransactionSerializer,
    SetPointBalanceSerializer,
    serialize_crew_point_summary,
)
from .services import (
    cancel_point_redemption,
    confirm_point_redemption,
    get_available_points,
    get_pending_redemption_points,
    get_point_balance,
    get_serialized_point_items,
    request_point_redemption,
    set_point_balance,
)


def _is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or getattr(user, "is_admin", lambda: False)())
    )


def _admin_required(request):
    if not _is_admin_user(request.user):
        return Response(
            {"detail": "관리자 권한이 필요합니다."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def point_items(request):
    if request.method == "GET":
        return Response(get_serialized_point_items(active_only=False))

    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    serializer = PointItemWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    item = serializer.save(
        created_by=request.user if getattr(request.user, "is_authenticated", False) else None,
        updated_by=request.user if getattr(request.user, "is_authenticated", False) else None,
    )
    return Response(PointItemSerializer(item).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "PUT", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def point_item_detail(request, item_id):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    item = get_object_or_404(PointItem, pk=item_id)
    if request.method == "DELETE":
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    partial = request.method == "PATCH"
    serializer = PointItemWriteSerializer(item, data=request.data, partial=partial)
    serializer.is_valid(raise_exception=True)
    item = serializer.save(
        updated_by=request.user if getattr(request.user, "is_authenticated", False) else None,
    )
    return Response(PointItemSerializer(item).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def crew_point_summaries(request):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    team = request.query_params.get("team")
    qs = CrewMember.objects.filter(
        is_active=True,
        is_yongcha=False,
        team__company_app=get_company_app_from_request(request),
    ).select_related("team")
    if team:
        qs = qs.filter(team_id=team)

    rows = [serialize_crew_point_summary(crew) for crew in qs.order_by("team__code", "name", "code")]
    rows.sort(key=lambda row: (not bool(row["pending_redemptions"]), row["team_code"], row["name"]))
    return Response(rows)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def crew_point_detail(request, crew_id):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    crew = get_object_or_404(
        CrewMember.objects.select_related("team"),
        pk=crew_id,
        is_active=True,
        team__company_app=get_company_app_from_request(request),
    )
    transactions = PointTransaction.objects.filter(crew_member=crew).order_by("-created_at", "-id")[:50]
    redemptions = PointRedemption.objects.filter(crew_member=crew).order_by("status", "-requested_at", "-id")[:50]
    data = serialize_crew_point_summary(crew)
    data["transactions"] = PointTransactionSerializer(transactions, many=True).data
    data["redemptions"] = PointRedemptionSerializer(redemptions, many=True).data
    return Response(data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def set_crew_point_balance(request, crew_id):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    serializer = SetPointBalanceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    crew = get_object_or_404(
        CrewMember.objects.select_related("team"),
        pk=crew_id,
        is_active=True,
        team__company_app=get_company_app_from_request(request),
    )
    try:
        set_point_balance(
            crew,
            serializer.validated_data["balance"],
            user=request.user,
            memo=serializer.validated_data.get("memo", ""),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serialize_crew_point_summary(crew))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def confirm_redemption(request, redemption_id):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    try:
        redemption = PointRedemption.objects.get(pk=redemption_id)
        confirm_point_redemption(redemption, user=request.user)
    except PointRedemption.DoesNotExist:
        return Response({"detail": "교환 요청을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    redemption.refresh_from_db()
    return Response(PointRedemptionSerializer(redemption).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def cancel_redemption(request, redemption_id):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    try:
        redemption = PointRedemption.objects.get(pk=redemption_id)
        cancel_point_redemption(redemption, user=request.user, note=request.data.get("note", ""))
    except PointRedemption.DoesNotExist:
        return Response({"detail": "교환 요청을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(PointRedemptionSerializer(redemption).data)


def mobile_point_summary(crew):
    pending_redemptions = PointRedemption.objects.filter(
        crew_member=crew,
        status=PointRedemption.Status.PENDING,
    ).order_by("-requested_at", "-id")
    recent_redemptions = PointRedemption.objects.filter(crew_member=crew).order_by("-requested_at", "-id")[:10]
    recent_transactions = PointTransaction.objects.filter(crew_member=crew).order_by("-created_at", "-id")[:10]
    return {
        "balance": get_point_balance(crew),
        "pending_points": get_pending_redemption_points(crew),
        "available_points": get_available_points(crew),
        "items": get_serialized_point_items(active_only=True),
        "pending_redemptions": PointRedemptionSerializer(pending_redemptions, many=True).data,
        "recent_redemptions": PointRedemptionSerializer(recent_redemptions, many=True).data,
        "recent_transactions": PointTransactionSerializer(recent_transactions, many=True).data,
    }


@api_view(["GET"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def mobile_points(request):
    crew = getattr(request, "crew_member", None)
    if not crew:
        from apps.mobile.views import _get_crew_from_token

        crew = _get_crew_from_token(request)
    if not crew:
        return Response({"detail": "세션이 만료되었습니다. 다시 로그인해 주세요."}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(mobile_point_summary(crew))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def mobile_redeem_points(request):
    from apps.mobile.views import _get_crew_from_token

    crew = _get_crew_from_token(request)
    if not crew:
        return Response({"detail": "세션이 만료되었습니다. 다시 로그인해 주세요."}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = MobileRedeemPointSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        redemption = request_point_redemption(crew, serializer.validated_data["item_key"])
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    data = mobile_point_summary(crew)
    data["requested_redemption"] = PointRedemptionSerializer(redemption).data
    return Response(data, status=status.HTTP_201_CREATED)
