from datetime import date

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .catalog import (
    DEFAULT_POINT_REDEMPTION_ITEMS,
    POINT_REWARD_AMOUNT,
    POINT_REWARD_MIN_CAMERA_END_COUNT,
)
from .models import PointItem, PointRedemption, PointTransaction


DOUBLE_POINT_EVENT_END_DATE = date(2026, 5, 31)
DOUBLE_POINT_EVENT_REWARD_AMOUNT = 10


def get_tracking_point_reward_amount(target_date=None) -> int:
    current_date = target_date or timezone.localdate()
    if current_date <= DOUBLE_POINT_EVENT_END_DATE:
        return DOUBLE_POINT_EVENT_REWARD_AMOUNT
    return POINT_REWARD_AMOUNT


def ensure_default_point_items():
    if PointItem.objects.exists():
        return

    PointItem.objects.bulk_create(
        [
            PointItem(
                key=item["key"],
                name=item["name"],
                cost_points=int(item["cost_points"]),
                sort_order=index,
                is_active=True,
            )
            for index, item in enumerate(DEFAULT_POINT_REDEMPTION_ITEMS, start=1)
        ]
    )


def get_point_items(*, active_only=True):
    ensure_default_point_items()
    queryset = PointItem.objects.all().order_by("sort_order", "id")
    if active_only:
        queryset = queryset.filter(is_active=True)
    return queryset


def serialize_point_item(item):
    return {
        "id": item.id,
        "key": item.key,
        "name": item.name,
        "cost_points": int(item.cost_points or 0),
        "sort_order": int(item.sort_order or 0),
        "is_active": bool(item.is_active),
    }


def get_serialized_point_items(*, active_only=True):
    return [serialize_point_item(item) for item in get_point_items(active_only=active_only)]


def get_point_item_by_key(item_key, *, active_only=True):
    ensure_default_point_items()
    queryset = PointItem.objects.filter(key=str(item_key or "").strip())
    if active_only:
        queryset = queryset.filter(is_active=True)
    return queryset.first()


def get_point_balance(crew_member) -> int:
    if not crew_member:
        return 0
    return int(
        PointTransaction.objects.filter(crew_member=crew_member).aggregate(
            total=Coalesce(Sum("points"), 0)
        )["total"]
        or 0
    )


def get_pending_redemption_points(crew_member) -> int:
    if not crew_member:
        return 0
    return int(
        PointRedemption.objects.filter(
            crew_member=crew_member,
            status=PointRedemption.Status.PENDING,
        ).aggregate(total=Coalesce(Sum("cost_points"), 0))["total"]
        or 0
    )


def get_available_points(crew_member) -> int:
    return max(0, get_point_balance(crew_member) - get_pending_redemption_points(crew_member))


def evaluate_tracking_point_award(session):
    """
    Award one daily work-session point transaction when the uploaded session has
    at least one RSSI sample and enough camera-end events.
    """
    if not session or not session.crew_member_id:
        return {
            "awarded": False,
            "points": 0,
            "reason": "missing_session",
            "balance": 0,
        }

    crew = session.crew_member
    has_rssi = session.ble_logs.filter(rssi__isnull=False).exists()
    camera_end_count = sum(1 for capture in session.captures.all() if capture.captured_at)

    if not has_rssi:
        return {
            "awarded": False,
            "points": 0,
            "reason": "missing_rssi",
            "balance": get_point_balance(crew),
            "camera_end_count": camera_end_count,
        }
    if camera_end_count < POINT_REWARD_MIN_CAMERA_END_COUNT:
        return {
            "awarded": False,
            "points": 0,
            "reason": "not_enough_camera_end_events",
            "balance": get_point_balance(crew),
            "camera_end_count": camera_end_count,
        }

    reward_amount = get_tracking_point_reward_amount(session.session_date)

    with transaction.atomic():
        existing = PointTransaction.objects.select_for_update().filter(
            tracking_session=session,
            kind=PointTransaction.Kind.WORK_REWARD,
        ).first()
        if existing:
            return {
                "awarded": False,
                "points": 0,
                "reason": "already_awarded_for_session",
                "balance": get_point_balance(crew),
                "camera_end_count": camera_end_count,
            }

        PointTransaction.objects.create(
            crew_member=crew,
            points=reward_amount,
            kind=PointTransaction.Kind.WORK_REWARD,
            work_date=session.session_date,
            tracking_session=session,
            memo=f"근무기록 적립: RSSI 있음, camera_end {camera_end_count}회",
        )

    return {
        "awarded": True,
        "points": reward_amount,
        "reason": "awarded",
        "balance": get_point_balance(crew),
        "camera_end_count": camera_end_count,
    }


def evaluate_tracking_point_award_from_metrics(
    *,
    session,
    has_rssi: bool,
    camera_end_count: int,
):
    if not session or not session.crew_member_id:
        return {
            "awarded": False,
            "points": 0,
            "reason": "missing_session",
            "balance": 0,
        }

    crew = session.crew_member

    if not has_rssi:
        return {
            "awarded": False,
            "points": 0,
            "reason": "missing_rssi",
            "balance": get_point_balance(crew),
            "camera_end_count": camera_end_count,
        }
    if camera_end_count < POINT_REWARD_MIN_CAMERA_END_COUNT:
        return {
            "awarded": False,
            "points": 0,
            "reason": "not_enough_camera_end_events",
            "balance": get_point_balance(crew),
            "camera_end_count": camera_end_count,
        }

    reward_amount = get_tracking_point_reward_amount(session.session_date)

    with transaction.atomic():
        existing = PointTransaction.objects.select_for_update().filter(
            tracking_session=session,
            kind=PointTransaction.Kind.WORK_REWARD,
        ).first()
        if existing:
            return {
                "awarded": False,
                "points": 0,
                "reason": "already_awarded_for_session",
                "balance": get_point_balance(crew),
                "camera_end_count": camera_end_count,
            }

        PointTransaction.objects.create(
            crew_member=crew,
            points=reward_amount,
            kind=PointTransaction.Kind.WORK_REWARD,
            work_date=session.session_date,
            tracking_session=session,
            memo=f"근무기록 적립: RSSI 있음, camera_end {camera_end_count}회",
        )

    return {
        "awarded": True,
        "points": reward_amount,
        "reason": "awarded",
        "balance": get_point_balance(crew),
        "camera_end_count": camera_end_count,
    }


def request_point_redemption(crew_member, item_key):
    item = get_point_item_by_key(item_key, active_only=True)
    if not item:
        raise ValueError("교환 항목을 찾을 수 없습니다.")

    available = get_available_points(crew_member)
    cost = int(item.cost_points)
    if available < cost:
        raise ValueError("보유 포인트가 부족합니다.")

    redemption = PointRedemption.objects.create(
        crew_member=crew_member,
        item_key=item.key,
        item_name=item.name,
        cost_points=cost,
        status=PointRedemption.Status.PENDING,
    )
    return redemption


def set_point_balance(crew_member, target_balance, user=None, memo=""):
    target_balance = int(target_balance)
    if target_balance < 0:
        raise ValueError("포인트는 0 이상이어야 합니다.")

    current = get_point_balance(crew_member)
    delta = target_balance - current
    if delta == 0:
        return None, current

    tx = PointTransaction.objects.create(
        crew_member=crew_member,
        points=delta,
        kind=PointTransaction.Kind.MANUAL_ADJUST,
        memo=memo or f"관리자 직접 수정: {current}P -> {target_balance}P",
        created_by=user if getattr(user, "is_authenticated", False) else None,
        updated_by=user if getattr(user, "is_authenticated", False) else None,
    )
    return tx, get_point_balance(crew_member)


def confirm_point_redemption(redemption, user=None):
    with transaction.atomic():
        redemption = PointRedemption.objects.select_for_update().get(pk=redemption.pk)
        if redemption.status != PointRedemption.Status.PENDING:
            raise ValueError("대기 중인 교환 요청만 확인할 수 있습니다.")
        if get_point_balance(redemption.crew_member) < redemption.cost_points:
            raise ValueError("보유 포인트가 부족하여 차감할 수 없습니다.")

        tx = PointTransaction.objects.create(
            crew_member=redemption.crew_member,
            points=-int(redemption.cost_points),
            kind=PointTransaction.Kind.REDEMPTION_DEDUCT,
            redemption=redemption,
            memo=f"포인트 교환 확인: {redemption.item_name}",
            created_by=user if getattr(user, "is_authenticated", False) else None,
            updated_by=user if getattr(user, "is_authenticated", False) else None,
        )
        redemption.status = PointRedemption.Status.CONFIRMED
        redemption.confirmed_at = timezone.now()
        redemption.confirmed_by = user if getattr(user, "is_authenticated", False) else None
        redemption.updated_by = user if getattr(user, "is_authenticated", False) else None
        redemption.save(
            update_fields=[
                "status",
                "confirmed_at",
                "confirmed_by",
                "updated_by",
                "updated_at",
            ]
        )
    return tx


def cancel_point_redemption(redemption, user=None, note=""):
    if redemption.status != PointRedemption.Status.PENDING:
        raise ValueError("대기 중인 교환 요청만 취소할 수 있습니다.")
    redemption.status = PointRedemption.Status.CANCELLED
    if note:
        redemption.note = note
    redemption.updated_by = user if getattr(user, "is_authenticated", False) else None
    redemption.save(update_fields=["status", "note", "updated_by", "updated_at"])
    return redemption
