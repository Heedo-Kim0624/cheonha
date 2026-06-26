from dataclasses import dataclass


@dataclass
class ParsedTextDispatch:
    rows: list
    errors: list
    total_boxes: int
    total_households: int


def _safe_int(value):
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _is_coupang_header(line):
    if "|" not in line:
        return False
    normalized = line.replace(" ", "")
    if "이름" in normalized and "건수" in normalized and "가구수" in normalized:
        return True

    parts = [part.strip() for part in line.split("|")]
    return (
        len(parts) >= 4
        and parts[1] == "이름"
        and parts[2] == "건수"
        and parts[3] == "가구수"
    )


def parse_coupang_dispatch_text(raw_text):
    """Parse Coupang pasted volume text into DispatchRecord-compatible rows."""

    lines = str(raw_text or "").splitlines()
    header_index = None
    for index, line in enumerate(lines):
        if _is_coupang_header(line):
            header_index = index
            break

    rows = []
    errors = []
    if header_index is None:
        return ParsedTextDispatch(
            rows=[],
            errors=[{"line_no": 0, "message": "헤더(이름 | 건수 | 가구수)를 찾을 수 없습니다.", "raw": ""}],
            total_boxes=0,
            total_households=0,
        )

    for line_no, line in enumerate(lines[header_index + 1 :], start=header_index + 2):
        raw = line.strip()
        if not raw:
            continue
        if "|" not in raw:
            continue

        parts = [part.strip() for part in raw.split("|")]
        if len(parts) < 4:
            errors.append({"line_no": line_no, "message": "4개 컬럼(권역, 이름, 건수, 가구수)이 필요합니다.", "raw": raw})
            continue

        region_code, manager_name, boxes_raw, households_raw = parts[:4]
        boxes = _safe_int(boxes_raw)
        households = _safe_int(households_raw)
        if not region_code:
            errors.append({"line_no": line_no, "message": "권역 코드가 비어 있습니다.", "raw": raw})
            continue
        if not manager_name:
            errors.append({"line_no": line_no, "message": "배송원 이름이 비어 있습니다.", "raw": raw})
            continue
        if boxes is None:
            errors.append({"line_no": line_no, "message": "건수는 숫자여야 합니다.", "raw": raw})
            continue
        if households is None:
            errors.append({"line_no": line_no, "message": "가구수는 숫자여야 합니다.", "raw": raw})
            continue

        rows.append({
            "row_num": line_no,
            "delivery_type": "COUPANG",
            "partner_name": "",
            "manager_name": manager_name,
            "sub_region": region_code,
            "detail_region": region_code,
            "boxes": boxes,
            "households": households,
            "is_yongcha": False,
        })

    return ParsedTextDispatch(
        rows=rows,
        errors=errors,
        total_boxes=sum(int(row["boxes"] or 0) for row in rows),
        total_households=sum(int(row["households"] or 0) for row in rows),
    )
