from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import pandas as pd


# =========================================================
# 共用日期解析工具
#
# 給「開始/結束日期已分成兩個獨立欄位」的新模板格式使用
# （檔期、鋪底、活動表皆為此類）。
#
# 與 clean_other_activities.py 的 DATE_PATTERN/FULL_DATE_PATTERN
# 不同之處：這裡的輸入是「單一儲存格只會是一個日期」，
# 而且儲存格本身可能已經是 datetime/Timestamp 物件
# （openpyxl 讀入 Excel 日期儲存格時常見），
# 不能只假設輸入一定是 "/" 分隔的字串。
# =========================================================

FULL_DATE_SLASH_PATTERN = re.compile(
    r"(?P<year>\d{4})\s*/\s*(?P<month>\d{1,2})\s*/\s*(?P<day>\d{1,2})"
)

FULL_DATE_DASH_PATTERN = re.compile(
    r"(?P<year>\d{4})\s*-\s*(?P<month>\d{1,2})\s*-\s*(?P<day>\d{1,2})"
)

SHORT_DATE_PATTERN = re.compile(
    r"(?<!\d)(?P<month>\d{1,2})\s*/\s*(?P<day>\d{1,2})(?!\d)"
)


def parse_flexible_date(
    value: Any,
    default_year: int = 2026,
) -> pd.Timestamp:
    """
    統一解析單一日期儲存格，依序嘗試：

    1. value 本身已是 pandas.Timestamp / datetime.datetime / datetime.date
       （Excel 日期儲存格經 openpyxl 讀入後常見此型別）。
    2. 完整日期文字，如 "2026/3/8" 或 "2026-03-08 00:00:00"
       （後者是 str(datetime物件) 產生的格式，需支援 "-" 分隔）。
    3. 純 M/D 文字（無年份），如 "3/8"，用 default_year 補上年份。

    無法解析時回傳 pd.NaT。
    """

    if value is None:
        return pd.NaT

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).normalize()

    if pd.isna(value):
        return pd.NaT

    text = str(value).strip()

    if not text:
        return pd.NaT

    full_slash_match = FULL_DATE_SLASH_PATTERN.search(text)

    if full_slash_match:
        return _build_timestamp(
            int(full_slash_match.group("year")),
            int(full_slash_match.group("month")),
            int(full_slash_match.group("day")),
        )

    full_dash_match = FULL_DATE_DASH_PATTERN.search(text)

    if full_dash_match:
        return _build_timestamp(
            int(full_dash_match.group("year")),
            int(full_dash_match.group("month")),
            int(full_dash_match.group("day")),
        )

    short_match = SHORT_DATE_PATTERN.search(text)

    if short_match:
        return _build_timestamp(
            default_year,
            int(short_match.group("month")),
            int(short_match.group("day")),
        )

    return pd.NaT


def _build_timestamp(
    year: int,
    month: int,
    day: int,
) -> pd.Timestamp:
    try:
        return pd.Timestamp(
            year=year,
            month=month,
            day=day,
        )

    except ValueError:
        return pd.NaT
