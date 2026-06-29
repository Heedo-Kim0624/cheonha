"""Operation report aggregation helpers.

Keep report calculations outside view methods so the same formulas can be
tested and reused without changing public API behavior.
"""

from django.db.models import Q, Sum

from apps.settlement.models import SettlementDetail


SETTLEMENT_AMOUNT_STATUSES = ("CONFIRMED", "PAID")
OPERATION_REPORT_AMOUNT_FIELDS = (
    "amount_total_receive",
    "amount_regular_pay",
    "amount_yongcha_pay",
    "amount_profit",
)
OPERATION_REPORT_SUMMARY_FIELDS = (
    "actual_total_boxes",
    "round_1_boxes",
    "round_2_boxes",
    "round_3_boxes",
    "amount_total_receive",
    "amount_regular_pay",
    "amount_yongcha_pay",
    "amount_profit",
    "round_1_input_count",
    "round_2_input_count",
    "round_3_input_count",
)


def _is_admin_user(user):
    return bool(
        getattr(user, "is_staff", False)
        or (hasattr(user, "is_admin") and user.is_admin())
    )


def empty_operation_report_amounts():
    return {field: 0 for field in OPERATION_REPORT_AMOUNT_FIELDS}


def build_operation_report_summary(rows):
    """Build the public operation-report summary payload from report rows."""

    rows = list(rows or [])
    summary = {
        "row_count": len(rows),
    }
    for field in OPERATION_REPORT_SUMMARY_FIELDS:
        summary[field] = sum(int(row.get(field) or 0) for row in rows)

    # Backward compatibility for existing frontend code.
    summary["total_boxes"] = summary["actual_total_boxes"]
    summary["total_volume"] = summary["actual_total_boxes"]
    return summary


def build_operation_report_csv_header(metric_label, metric_unit):
    return [
        "날짜(배송일)", "요일(배송일)", "조",
        f"실제 처리 {metric_label}", "전체수신(원)", "정규지급(원)", "용차지급(원)", "수익(원)",
        "가구당 박스수",
        f"1회차 {metric_label}", f"2회차 {metric_label}", f"3회차 {metric_label}",
        f"1회차 생산성({metric_unit}/대)", f"3회차 생산성({metric_unit}/대)", f"다회차 생산성({metric_unit}/명)",
        "1회차 투입 대수", "1회차 매니저", "1회차 용차", "1회차 용차비율",
        "2회차 투입 대수", "2회차 매니저", "2회차 용차", "2회차 용차비율",
        "3회차 투입 대수", "3회차 매니저", "3회차 용차", "3회차 용차비율",
    ]


def build_operation_report_csv_row(row):
    return [
        row["work_date"], row["weekday"], row["team_name"],
        row["actual_total_boxes"],
        row["amount_total_receive"], row["amount_regular_pay"], row["amount_yongcha_pay"], row["amount_profit"],
        row["boxes_per_household"],
        row["round_1_boxes"], row["round_2_boxes"], row["round_3_boxes"],
        row["round_1_productivity"], row["round_3_productivity"], row["multi_round_productivity"],
        row["round_1_input_count"], row["round_1_manager_count"], row["round_1_yongcha_count"], row["round_1_yongcha_ratio"],
        row["round_2_input_count"], row["round_2_manager_count"], row["round_2_yongcha_count"], row["round_2_yongcha_ratio"],
        row["round_3_input_count"], row["round_3_manager_count"], row["round_3_yongcha_count"], row["round_3_yongcha_ratio"],
    ]


def write_operation_report_csv(writer, rows, metric_label, metric_unit):
    writer.writerow(build_operation_report_csv_header(metric_label, metric_unit))
    for row in rows:
        writer.writerow(build_operation_report_csv_row(row))


def build_operation_report_amount_lookup(*, start_date, end_date, team_ids, user=None, company_app=None, shipper_code=None):
    """Return settlement amount totals keyed by (delivery_date_iso, team_id).

    This intentionally mirrors the existing operation report behavior:
    only CONFIRMED/PAID settlements are counted, grouped by settlement
    period_start and settlement team.
    """

    normalized_team_ids = {team_id for team_id in team_ids if team_id}
    if not normalized_team_ids:
        return {}

    details = SettlementDetail.objects.filter(
        settlement__status__in=SETTLEMENT_AMOUNT_STATUSES,
        settlement__period_start__gte=start_date,
        settlement__period_start__lte=end_date,
        settlement__team_id__in=normalized_team_ids,
    )
    if shipper_code:
        details = details.filter(settlement__shipper_code=shipper_code)

    if user is not None:
        if _is_admin_user(user):
            if company_app:
                details = details.filter(settlement__team__company_app=company_app)
        elif getattr(user, "team_id", None):
            details = details.filter(settlement__team=user.team)

    amount_rows = details.values(
        "settlement__period_start",
        "settlement__team_id",
    ).annotate(
        amount_total_receive=Sum("receive_amount"),
        amount_regular_pay=Sum("pay_amount", filter=Q(is_yongcha=False)),
        amount_yongcha_pay=Sum("pay_amount", filter=Q(is_yongcha=True)),
        amount_profit=Sum("profit"),
    )

    return {
        (row["settlement__period_start"].isoformat(), row["settlement__team_id"]): {
            "amount_total_receive": int(row["amount_total_receive"] or 0),
            "amount_regular_pay": int(row["amount_regular_pay"] or 0),
            "amount_yongcha_pay": int(row["amount_yongcha_pay"] or 0),
            "amount_profit": int(row["amount_profit"] or 0),
        }
        for row in amount_rows
        if row["settlement__period_start"] and row["settlement__team_id"]
    }
