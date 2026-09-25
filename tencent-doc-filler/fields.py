from __future__ import annotations

import re
from datetime import datetime

# 与 qq-bot repair_form_api.FORM_FIELD_ORDER 一致
FORM_FIELD_ORDER: tuple[str, ...] = (
    "故障教室",
    "报修时间",
    "周次",
    "报修类型",
    "报修人",
    "报修人学院",
    "是否为外聘老师",
    "报修方式",
    "处理人",
    "是否更换设备",
    "处理情况",
    "故障发生原因",
    "处理方式",
)

# 图2 标准列：A=序号（不填），B~N 共 13 列业务字段
FIRST_DATA_COLUMN = "B"
LAST_DATA_COLUMN = "N"
DATA_COLUMN_COUNT = 13


def normalize_report_date(raw: str) -> str:
    """2026-06-07 → 2026/6/7，与表格现有格式一致。"""
    text = (raw or "").strip()
    if not text:
        return text
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(text[:19], fmt)
            return f"{dt.year}/{dt.month}/{dt.day}"
        except ValueError:
            continue
    return text.replace("-", "/")


def normalize_week(raw: str) -> str:
    """第14周 → 14。"""
    text = (raw or "").strip()
    m = re.search(r"\d+", text)
    return m.group(0) if m else text


def normalize_form_for_sheet(form: dict[str, str]) -> dict[str, str]:
    """按表格约束规范化字段值。"""
    out = {k: str(v or "").strip() for k, v in form.items()}
    if out.get("报修时间"):
        out["报修时间"] = normalize_report_date(out["报修时间"])
    if out.get("周次"):
        out["周次"] = normalize_week(out["周次"])
    if out.get("是否为外聘老师") in ("是", "否"):
        pass
    elif out.get("是否为外聘老师"):
        out["是否为外聘老师"] = "是" if "是" in out["是否为外聘老师"] else "否"
    return out


def form_to_row_values(form: dict[str, str]) -> list[str]:
    """仅 B~N 共 13 列，不写 A 列序号。"""
    normalized = normalize_form_for_sheet(form)
    return [normalized.get(field, "") for field in FORM_FIELD_ORDER]


def build_write_range(sheet_id: str, row: int) -> str:
    return f"{sheet_id}!{FIRST_DATA_COLUMN}{row}:{LAST_DATA_COLUMN}{row}"


def validate_form(form: dict[str, str]) -> list[str]:
    missing = [k for k in FORM_FIELD_ORDER if not str(form.get(k, "") or "").strip()]
    return missing
