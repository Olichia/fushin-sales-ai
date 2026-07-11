from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

MARCH_FILE_PATH = RAW_DATA_DIR / "3月品牌活動_通路.xlsx"
APRIL_FILE_PATH = RAW_DATA_DIR / "4月品牌活動_通路.xlsx"

CALENDAR_OUTPUT_PATH = (
    PROCESSED_DIR / "campaign_calendar.csv"
)

BENEFITS_OUTPUT_PATH = (
    PROCESSED_DIR / "promotion_benefits.csv"
)

ISSUES_OUTPUT_PATH = (
    PROCESSED_DIR / "other_activity_issues.csv"
)

SUMMARY_OUTPUT_PATH = (
    PROCESSED_DIR / "other_activity_summary.csv"
)


# =========================================================
# 日期解析規則
# =========================================================

DATE_PATTERN = re.compile(
    r"""
    (?<!\d)
    (?P<start_month>\d{1,2})
    \s*/\s*
    (?P<start_day>\d{1,2})

    (?:
        \s*
        [~～\-–—至]
        \s*

        (?:
            (?P<end_month>\d{1,2})
            \s*/\s*
        )?

        (?P<end_day>\d{1,2})
    )?
    """,
    re.VERBOSE,
)


FULL_DATE_PATTERN = re.compile(
    r"""
    (?P<year>\d{4})
    \s*/\s*
    (?P<month>\d{1,2})
    \s*/\s*
    (?P<day>\d{1,2})
    """,
    re.VERBOSE,
)


# =========================================================
# 共用基本函式
# =========================================================

def normalize_text(value: Any) -> str:
    """
    將 Excel 儲存格轉為乾淨文字。
    """

    if pd.isna(value):
        return ""

    text = str(value).strip()

    replacements = {
        "（": "(",
        "）": ")",
        "～": "~",
        "－": "-",
        "—": "-",
        "–": "-",
        "＋": "+",
        "，": ",",
        "％": "%",
        "＄": "$",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def clean_product_id(value: Any) -> str | None:
    """
    商品編號統一轉為文字。

    例如：
    330290.0 -> 330290
    """

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    text = re.sub(r"\.0$", "", text)

    return text


def numeric_value(value: Any) -> float | None:
    """
    將儲存格轉為數字，失敗時回傳 None。
    """

    if pd.isna(value):
        return None

    converted = pd.to_numeric(
        pd.Series([value]),
        errors="coerce",
    ).iloc[0]

    if pd.isna(converted):
        return None

    return float(converted)


def load_sheet(
    file_path: Path,
    sheet_name: str,
    header: int | None = 0,
) -> pd.DataFrame:
    """
    讀取指定工作表。
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"找不到檔案：{file_path}"
        )

    try:
        dataframe = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=header,
            engine="openpyxl",
        )

    except ValueError as error:
        raise ValueError(
            f"{file_path.name} 找不到工作表："
            f"{sheet_name}"
        ) from error

    except PermissionError as error:
        raise PermissionError(
            f"無法讀取 {file_path.name}，"
            "請先關閉 Excel。"
        ) from error

    return dataframe


# =========================================================
# 日期解析函式
# =========================================================

def parse_date_ranges(
    value: Any,
    default_year: int = 2026,
) -> list[dict[str, Any]]:
    """
    從文字中找出一個或多個日期或日期區間。

    可辨識例如：
    3/1-3/7
    4/20一天
    4/21~4/25
    2026/4/20品牌日
    4/20品牌日-4/21-4/25品牌周
    """

    text = normalize_text(value)

    if not text:
        return []

    results: list[dict[str, Any]] = []

    # 先處理完整年月日，例如 2026/4/20
    full_date_matches = list(
        FULL_DATE_PATTERN.finditer(text)
    )

    occupied_ranges: list[tuple[int, int]] = []

    for match in full_date_matches:
        year = int(match.group("year"))
        month = int(match.group("month"))
        day = int(match.group("day"))

        try:
            date_value = pd.Timestamp(
                year=year,
                month=month,
                day=day,
            )

            results.append(
                {
                    "start_date": date_value,
                    "end_date": date_value,
                    "matched_text": match.group(0),
                    "date_valid": True,
                }
            )

        except ValueError:
            results.append(
                {
                    "start_date": pd.NaT,
                    "end_date": pd.NaT,
                    "matched_text": match.group(0),
                    "date_valid": False,
                }
            )

        occupied_ranges.append(
            (match.start(), match.end())
        )

    # 再處理 M/D 或 M/D-M/D
    for match in DATE_PATTERN.finditer(text):
        # 避免把 2026/4/20 中的 26/4 誤認成日期
        is_occupied = any(
            match.start() >= start
            and match.end() <= end
            for start, end in occupied_ranges
        )

        if is_occupied:
            continue

        start_month = int(
            match.group("start_month")
        )

        start_day = int(
            match.group("start_day")
        )

        end_month_text = match.group(
            "end_month"
        )

        end_day_text = match.group(
            "end_day"
        )

        if end_day_text is None:
            end_month = start_month
            end_day = start_day

        else:
            end_month = (
                int(end_month_text)
                if end_month_text
                else start_month
            )

            end_day = int(end_day_text)

        try:
            start_date = pd.Timestamp(
                year=default_year,
                month=start_month,
                day=start_day,
            )

            end_date = pd.Timestamp(
                year=default_year,
                month=end_month,
                day=end_day,
            )

            date_valid = (
                end_date >= start_date
            )

        except ValueError:
            start_date = pd.NaT
            end_date = pd.NaT
            date_valid = False

        results.append(
            {
                "start_date": start_date,
                "end_date": end_date,
                "matched_text": match.group(0),
                "date_valid": date_valid,
            }
        )

    # 移除完全相同的解析結果
    unique_results = []
    seen = set()

    for result in results:
        key = (
            str(result["start_date"]),
            str(result["end_date"]),
            result["matched_text"],
        )

        if key not in seen:
            unique_results.append(result)
            seen.add(key)

    return unique_results


def parse_first_date_range(
    value: Any,
) -> dict[str, Any] | None:
    """
    只取得文字中的第一個日期區間。
    """

    results = parse_date_ranges(value)

    if not results:
        return None

    return results[0]


# =========================================================
# 優惠內容文字解析
# =========================================================

def extract_threshold(
    text: str,
) -> float | None:
    """
    擷取滿額門檻。

    例如：
    滿$3999送8%平台幣 -> 3999
    滿額1199 -> 1199
    單品滿1800使用 -> 1800
    """

    patterns = [
        r"滿額\s*\$?\s*([\d,]+)",
        r"滿\s*\$?\s*([\d,]+)",
        r"單品滿\s*\$?\s*([\d,]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return float(
                match.group(1).replace(",", "")
            )

    return None


def extract_percentage(
    text: str,
) -> float | None:
    """
    擷取百分比，並轉成小數。

    例如：
    8% -> 0.08
    """

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*%",
        text,
    )

    if not match:
        return None

    return float(match.group(1)) / 100


def extract_limit_amount(
    text: str,
) -> float | None:
    """
    擷取回饋上限。

    例如：
    上限500 -> 500
    """

    match = re.search(
        r"上限\s*\$?\s*([\d,]+)",
        text,
    )

    if not match:
        return None

    return float(
        match.group(1).replace(",", "")
    )


def extract_fixed_reward(
    text: str,
) -> float | None:
    """
    擷取固定平台幣金額。

    例如：
    滿$1399送130平台幣 -> 130
    """

    match = re.search(
        r"送\s*\$?\s*([\d,]+)\s*平台幣",
        text,
    )

    if not match:
        return None

    return float(
        match.group(1).replace(",", "")
    )


def extract_quota(
    text: str,
) -> float | None:
    """
    擷取限量名額。

    例如：
    650名 -> 650
    抽30名 -> 30
    限量100名 -> 100
    """

    patterns = [
        r"限量\s*([\d,]+)\s*名",
        r"抽\s*([\d,]+)\s*名",
        r"\(\s*([\d,]+)\s*名\s*\)",
        r"([\d,]+)\s*名",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return float(
                match.group(1).replace(",", "")
            )

    return None


def classify_benefit_type(
    title: str,
    content: str,
) -> str:
    """
    根據標題與內容初步分類優惠類型。
    """

    combined = f"{title} {content}"

    if "折價券" in combined or "折" in combined:
        return "折價券"

    if "平台幣" in combined:
        return "平台幣"

    if "下單抽" in combined or "登記抽" in combined:
        return "抽獎"

    if "買就抽" in combined:
        return "抽獎"

    if "贈" in combined or "滿額" in combined:
        return "滿額贈"

    if "包套" in combined or "投廣" in combined:
        return "媒體投廣"

    return "其他活動"


def classify_scope(
    product_id: str | None,
) -> str:
    """
    區分活動適用範圍。
    """

    if product_id:
        return "指定商品"

    return "全站或品牌活動"


# =========================================================
# 標準輸出紀錄
# =========================================================

def build_calendar_record(
    *,
    source_file: str,
    source_sheet: str,
    source_row_number: int,
    campaign_name: str,
    period_text: str,
    start_date: Any,
    end_date: Any,
    matched_text: str,
    campaign_level: str = "全站或品牌",
    note: str = "",
) -> dict[str, Any]:
    """
    建立標準活動日曆紀錄。
    """

    return {
        "source_file": source_file,
        "source_sheet": source_sheet,
        "source_row_number": source_row_number,
        "campaign_name": campaign_name,
        "campaign_level": campaign_level,
        "campaign_start_date": start_date,
        "campaign_end_date": end_date,
        "matched_date_text": matched_text,
        "period_text_raw": period_text,
        "note": note,
    }


def build_benefit_record(
    *,
    source_file: str,
    source_sheet: str,
    source_row_number: int,
    product_id: str | None = None,
    product_name: str = "",
    campaign_name: str = "",
    benefit_type: str = "",
    benefit_content: str = "",
    start_date: Any = pd.NaT,
    end_date: Any = pd.NaT,
    threshold_amount: float | None = None,
    reward_percentage: float | None = None,
    reward_amount: float | None = None,
    reward_limit_amount: float | None = None,
    quota: float | None = None,
    activity_price: float | None = None,
    discounted_price: float | None = None,
    note: str = "",
) -> dict[str, Any]:
    """
    建立標準優惠內容紀錄。
    """

    return {
        "source_file": source_file,
        "source_sheet": source_sheet,
        "source_row_number": source_row_number,
        "scope": classify_scope(product_id),
        "product_id": product_id,
        "product_name": product_name,
        "campaign_name": campaign_name,
        "benefit_type": benefit_type,
        "benefit_content": benefit_content,
        "benefit_start_date": start_date,
        "benefit_end_date": end_date,
        "threshold_amount": threshold_amount,
        "reward_percentage": reward_percentage,
        "reward_amount": reward_amount,
        "reward_limit_amount": reward_limit_amount,
        "quota": quota,
        "activity_price": activity_price,
        "discounted_price": discounted_price,
        "note": note,
    }


def build_issue_record(
    *,
    source_file: str,
    source_sheet: str,
    source_row_number: int,
    issue_type: str,
    problem_text: str,
) -> dict[str, Any]:
    """
    建立資料問題紀錄。
    """

    return {
        "source_file": source_file,
        "source_sheet": source_sheet,
        "source_row_number": source_row_number,
        "issue_type": issue_type,
        "problem_text": problem_text,
    }


# =========================================================
# 解析「檔期」工作表
# =========================================================

def parse_schedule_sheet(
    file_path: Path,
    source_month: int,
) -> tuple[list[dict], list[dict]]:
    """
    解析 3 月或 4 月的「檔期」工作表。
    """

    dataframe = load_sheet(
        file_path,
        "檔期",
        header=None,
    )

    calendar_records = []
    issue_records = []

    # 第一列為標題，因此從第 2 列開始
    for dataframe_index in range(
        1,
        len(dataframe),
    ):
        row = dataframe.iloc[dataframe_index]

        campaign_name = normalize_text(
            row.iloc[0]
        )

        period_text = normalize_text(
            row.iloc[1]
        )

        source_row_number = dataframe_index + 1

        if not campaign_name and not period_text:
            continue

        parsed_dates = parse_date_ranges(
            period_text
        )

        if not parsed_dates:
            issue_records.append(
                build_issue_record(
                    source_file=file_path.name,
                    source_sheet="檔期",
                    source_row_number=(
                        source_row_number
                    ),
                    issue_type="檔期日期無法解析",
                    problem_text=period_text,
                )
            )

            continue

        for parsed in parsed_dates:
            calendar_records.append(
                build_calendar_record(
                    source_file=file_path.name,
                    source_sheet="檔期",
                    source_row_number=(
                        source_row_number
                    ),
                    campaign_name=campaign_name,
                    period_text=period_text,
                    start_date=parsed[
                        "start_date"
                    ],
                    end_date=parsed[
                        "end_date"
                    ],
                    matched_text=parsed[
                        "matched_text"
                    ],
                    campaign_level="平台檔期",
                    note=(
                        f"來源月份：{source_month}月"
                    ),
                )
            )

            if not parsed["date_valid"]:
                issue_records.append(
                    build_issue_record(
                        source_file=file_path.name,
                        source_sheet="檔期",
                        source_row_number=(
                            source_row_number
                        ),
                        issue_type="檔期日期不合法",
                        problem_text=parsed[
                            "matched_text"
                        ],
                    )
                )

    return calendar_records, issue_records


# =========================================================
# 解析「三月鋪底／四月鋪底」
# =========================================================

SECTION_TITLES = {
    "送平台幣",
    "登記送平台幣",
    "鋪底贈",
    "原廠鋪底贈",
    "下單抽",
    "折價券",
}


def parse_base_promotion_sheet(
    file_path: Path,
    sheet_name: str,
) -> tuple[
    list[dict],
    list[dict],
    list[dict],
]:
    """
    解析三月鋪底或四月鋪底。

    因為這類工作表具有階層結構，
    程式會記住目前活動期間及優惠區塊。
    """

    dataframe = load_sheet(
        file_path,
        sheet_name,
        header=None,
    )

    calendar_records = []
    benefit_records = []
    issue_records = []

    current_campaign_name = ""
    current_section = ""
    current_start_date = pd.NaT
    current_end_date = pd.NaT
    current_period_text = ""

    for dataframe_index in range(
        1,
        len(dataframe),
    ):
        row = dataframe.iloc[dataframe_index]

        col_a = normalize_text(
            row.iloc[0]
            if len(row) > 0
            else ""
        )

        col_b = normalize_text(
            row.iloc[1]
            if len(row) > 1
            else ""
        )

        col_c = normalize_text(
            row.iloc[2]
            if len(row) > 2
            else ""
        )

        col_d_raw = (
            row.iloc[3]
            if len(row) > 3
            else None
        )

        col_d_text = normalize_text(
            col_d_raw
        )

        source_row_number = dataframe_index + 1

        if not any(
            [col_a, col_b, col_c, col_d_text]
        ):
            continue

        # -----------------------------------------
        # 活動期間標題，例如：
        # 女王節暖身 / 走期：3/2-3/6
        # 品牌日 / 走期：4/20一天
        # -----------------------------------------

        if "走期" in col_b:
            parsed = parse_first_date_range(
                col_b
            )

            if parsed:
                current_campaign_name = (
                    col_a or current_campaign_name
                )

                current_start_date = parsed[
                    "start_date"
                ]

                current_end_date = parsed[
                    "end_date"
                ]

                current_period_text = col_b

                calendar_records.append(
                    build_calendar_record(
                        source_file=file_path.name,
                        source_sheet=sheet_name,
                        source_row_number=(
                            source_row_number
                        ),
                        campaign_name=(
                            current_campaign_name
                        ),
                        period_text=col_b,
                        start_date=current_start_date,
                        end_date=current_end_date,
                        matched_text=parsed[
                            "matched_text"
                        ],
                        campaign_level=(
                            "品牌鋪底活動"
                        ),
                    )
                )

            else:
                issue_records.append(
                    build_issue_record(
                        source_file=file_path.name,
                        source_sheet=sheet_name,
                        source_row_number=(
                            source_row_number
                        ),
                        issue_type=(
                            "鋪底活動日期無法解析"
                        ),
                        problem_text=col_b,
                    )
                )

            # 若這列本身是鋪底贈或下單抽，
            # 同時更新目前優惠區塊
            if col_a:
                current_section = col_a

            continue

        # -----------------------------------------
        # 優惠區塊標題
        # -----------------------------------------

        normalized_title = col_a.replace(
            "\n",
            "",
        )

        matched_section = next(
            (
                title
                for title in SECTION_TITLES
                if title in normalized_title
            ),
            None,
        )

        if matched_section:
            current_section = matched_section

            # 標題列本身若有內容也保留
            if (
                col_b
                and "滿額登記送平台幣"
                not in col_b
            ):
                benefit_records.append(
                    build_benefit_record(
                        source_file=file_path.name,
                        source_sheet=sheet_name,
                        source_row_number=(
                            source_row_number
                        ),
                        campaign_name=(
                            current_campaign_name
                        ),
                        benefit_type=(
                            classify_benefit_type(
                                current_section,
                                col_b,
                            )
                        ),
                        benefit_content=col_b,
                        start_date=(
                            current_start_date
                        ),
                        end_date=(
                            current_end_date
                        ),
                    )
                )

            continue

        # 跳過表頭列
        if col_a in {"門檻", "名稱"}:
            continue

        if col_c in {
            "品名",
            "MO品名",
        }:
            continue

        # -----------------------------------------
        # 平台幣內容
        # -----------------------------------------

        if "平台幣" in col_b:
            benefit_records.append(
                build_benefit_record(
                    source_file=file_path.name,
                    source_sheet=sheet_name,
                    source_row_number=(
                        source_row_number
                    ),
                    campaign_name=(
                        current_campaign_name
                    ),
                    benefit_type="平台幣",
                    benefit_content=col_b,
                    start_date=(
                        current_start_date
                    ),
                    end_date=current_end_date,
                    threshold_amount=(
                        extract_threshold(col_b)
                    ),
                    reward_percentage=(
                        extract_percentage(col_b)
                    ),
                    reward_amount=(
                        extract_fixed_reward(
                            col_b
                        )
                    ),
                    reward_limit_amount=(
                        extract_limit_amount(
                            col_b
                        )
                    ),
                    quota=extract_quota(col_b),
                    note=current_section,
                )
            )

            continue

        # -----------------------------------------
        # 滿額贈、抽獎、折價券內容
        # -----------------------------------------

        benefit_content_parts = [
            part
            for part in [
                col_a,
                col_b,
                col_c,
            ]
            if part
        ]

        benefit_content = "｜".join(
            benefit_content_parts
        )

        if not benefit_content:
            continue

        if current_section:
            benefit_type = (
                classify_benefit_type(
                    current_section,
                    benefit_content,
                )
            )

            benefit_records.append(
                build_benefit_record(
                    source_file=file_path.name,
                    source_sheet=sheet_name,
                    source_row_number=(
                        source_row_number
                    ),
                    campaign_name=(
                        current_campaign_name
                    ),
                    benefit_type=benefit_type,
                    benefit_content=(
                        benefit_content
                    ),
                    start_date=(
                        current_start_date
                    ),
                    end_date=current_end_date,
                    threshold_amount=(
                        extract_threshold(
                            benefit_content
                        )
                    ),
                    reward_percentage=(
                        extract_percentage(
                            benefit_content
                        )
                    ),
                    reward_amount=(
                        extract_fixed_reward(
                            benefit_content
                        )
                    ),
                    reward_limit_amount=(
                        extract_limit_amount(
                            benefit_content
                        )
                    ),
                    quota=extract_quota(
                        benefit_content
                    ),
                    note=(
                        f"數量欄：{col_d_text}"
                        if col_d_text
                        else current_section
                    ),
                )
            )

    return (
        calendar_records,
        benefit_records,
        issue_records,
    )


# =========================================================
# 解析 3 月指定商品滿額即享券
# =========================================================

def parse_march_product_gifts(
    file_path: Path,
) -> tuple[list[dict], list[dict]]:
    """
    解析 0308-0312滿額贈即享券。
    """

    sheet_name = "0308-0312滿額贈即享券"

    dataframe = load_sheet(
        file_path,
        sheet_name,
        header=0,
    )

    benefit_records = []
    issue_records = []

    fixed_start = pd.Timestamp(
        "2026-03-08"
    )

    fixed_end = pd.Timestamp(
        "2026-03-12"
    )

    for dataframe_index, row in (
        dataframe.iterrows()
    ):
        product_id = clean_product_id(
            row.iloc[0]
        )

        gift_name = normalize_text(
            row.iloc[1]
        )

        activity_price = numeric_value(
            row.iloc[2]
        )

        source_row_number = (
            dataframe_index + 2
        )

        if not product_id:
            continue

        benefit_records.append(
            build_benefit_record(
                source_file=file_path.name,
                source_sheet=sheet_name,
                source_row_number=(
                    source_row_number
                ),
                product_id=product_id,
                campaign_name=(
                    "3/8-3/12滿額贈即享券"
                ),
                benefit_type="指定商品贈品",
                benefit_content=gift_name,
                start_date=fixed_start,
                end_date=fixed_end,
                activity_price=activity_price,
                note=(
                    "活動日期依工作表名稱判定"
                ),
            )
        )

        if not gift_name:
            issue_records.append(
                build_issue_record(
                    source_file=file_path.name,
                    source_sheet=sheet_name,
                    source_row_number=(
                        source_row_number
                    ),
                    issue_type="指定商品贈品缺漏",
                    problem_text=product_id,
                )
            )

    return benefit_records, issue_records


# =========================================================
# 解析 4 月吸塵器 8 折券
# =========================================================

def parse_april_vacuum_coupons(
    file_path: Path,
) -> tuple[list[dict], list[dict]]:
    """
    解析超品日吸塵器折價券。
    """

    sheet_name = "超品日吸塵器折價券"

    dataframe = load_sheet(
        file_path,
        sheet_name,
        header=0,
    )

    benefit_records = []
    issue_records = []

    current_start = pd.Timestamp(
        "2026-04-20"
    )

    current_end = pd.Timestamp(
        "2026-04-20"
    )

    for dataframe_index, row in (
        dataframe.iterrows()
    ):
        product_id = clean_product_id(
            row.iloc[0]
        )

        product_name = normalize_text(
            row.iloc[1]
        )

        activity_price = numeric_value(
            row.iloc[2]
        )

        discounted_price = numeric_value(
            row.iloc[3]
        )

        period_text = normalize_text(
            row.iloc[4]
        )

        source_row_number = (
            dataframe_index + 2
        )

        if not product_id:
            continue

        if period_text:
            parsed = parse_first_date_range(
                period_text
            )

            if parsed:
                current_start = parsed[
                    "start_date"
                ]

                current_end = parsed[
                    "end_date"
                ]

            else:
                issue_records.append(
                    build_issue_record(
                        source_file=file_path.name,
                        source_sheet=sheet_name,
                        source_row_number=(
                            source_row_number
                        ),
                        issue_type=(
                            "吸塵器折價券日期無法解析"
                        ),
                        problem_text=period_text,
                    )
                )

        benefit_records.append(
            build_benefit_record(
                source_file=file_path.name,
                source_sheet=sheet_name,
                source_row_number=(
                    source_row_number
                ),
                product_id=product_id,
                product_name=product_name,
                campaign_name="4/20超品日",
                benefit_type="8折折價券",
                benefit_content=(
                    "吸塵器全系列8折折價券"
                ),
                start_date=current_start,
                end_date=current_end,
                reward_percentage=0.20,
                activity_price=activity_price,
                discounted_price=(
                    discounted_price
                ),
                note=period_text,
            )
        )

    return benefit_records, issue_records


# =========================================================
# 解析「品牌日+品牌週」摘要
# =========================================================

def parse_brand_day_summary(
    file_path: Path,
) -> tuple[
    list[dict],
    list[dict],
    list[dict],
]:
    """
    解析品牌日+品牌週摘要表。

    這張表比較像企劃摘要，而不是交易明細。
    """

    sheet_name = "品牌日+品牌週"

    dataframe = load_sheet(
        file_path,
        sheet_name,
        header=0,
    )

    calendar_records = []
    benefit_records = []
    issue_records = []

    event_start = pd.Timestamp(
        "2026-04-20"
    )

    event_end = pd.Timestamp(
        "2026-04-20"
    )

    for dataframe_index, row in (
        dataframe.iterrows()
    ):
        item_name = normalize_text(
            row.iloc[0]
        )

        content = normalize_text(
            row.iloc[1]
        )

        source_row_number = (
            dataframe_index + 2
        )

        if not item_name and not content:
            continue

        if item_name == "日期":
            parsed = parse_first_date_range(
                content
            )

            if parsed:
                event_start = parsed[
                    "start_date"
                ]

                event_end = parsed[
                    "end_date"
                ]

                calendar_records.append(
                    build_calendar_record(
                        source_file=file_path.name,
                        source_sheet=sheet_name,
                        source_row_number=(
                            source_row_number
                        ),
                        campaign_name="品牌日",
                        period_text=content,
                        start_date=event_start,
                        end_date=event_end,
                        matched_text=parsed[
                            "matched_text"
                        ],
                        campaign_level=(
                            "品牌活動摘要"
                        ),
                    )
                )

            else:
                issue_records.append(
                    build_issue_record(
                        source_file=file_path.name,
                        source_sheet=sheet_name,
                        source_row_number=(
                            source_row_number
                        ),
                        issue_type=(
                            "品牌日日期無法解析"
                        ),
                        problem_text=content,
                    )
                )

            continue

        benefit_type = classify_benefit_type(
            item_name,
            content,
        )

        benefit_records.append(
            build_benefit_record(
                source_file=file_path.name,
                source_sheet=sheet_name,
                source_row_number=(
                    source_row_number
                ),
                campaign_name="品牌日",
                benefit_type=benefit_type,
                benefit_content=content,
                start_date=event_start,
                end_date=event_end,
                threshold_amount=(
                    extract_threshold(content)
                ),
                reward_percentage=(
                    extract_percentage(content)
                ),
                reward_amount=(
                    extract_fixed_reward(content)
                ),
                reward_limit_amount=(
                    extract_limit_amount(content)
                ),
                quota=extract_quota(content),
                note=item_name,
            )
        )

    return (
        calendar_records,
        benefit_records,
        issue_records,
    )


# =========================================================
# 解析「包套」
# =========================================================

def parse_package_sheet(
    file_path: Path,
) -> tuple[
    list[dict],
    list[dict],
    list[dict],
]:
    """
    解析包套投廣資料。
    """

    sheet_name = "包套"

    dataframe = load_sheet(
        file_path,
        sheet_name,
        header=0,
    )

    calendar_records = []
    benefit_records = []
    issue_records = []

    for dataframe_index, row in (
        dataframe.iterrows()
    ):
        month_text = normalize_text(
            row.iloc[0]
        )

        content = normalize_text(
            row.iloc[1]
        )

        source_row_number = (
            dataframe_index + 2
        )

        if not content:
            continue

        parsed = parse_first_date_range(
            content
        )

        if not parsed:
            issue_records.append(
                build_issue_record(
                    source_file=file_path.name,
                    source_sheet=sheet_name,
                    source_row_number=(
                        source_row_number
                    ),
                    issue_type="包套日期無法解析",
                    problem_text=content,
                )
            )

            continue

        calendar_records.append(
            build_calendar_record(
                source_file=file_path.name,
                source_sheet=sheet_name,
                source_row_number=(
                    source_row_number
                ),
                campaign_name="包套投廣",
                period_text=content,
                start_date=parsed[
                    "start_date"
                ],
                end_date=parsed["end_date"],
                matched_text=parsed[
                    "matched_text"
                ],
                campaign_level="媒體包套",
                note=month_text,
            )
        )

        benefit_records.append(
            build_benefit_record(
                source_file=file_path.name,
                source_sheet=sheet_name,
                source_row_number=(
                    source_row_number
                ),
                campaign_name="包套投廣",
                benefit_type="媒體投廣",
                benefit_content=content,
                start_date=parsed[
                    "start_date"
                ],
                end_date=parsed["end_date"],
                note=month_text,
            )
        )

    return (
        calendar_records,
        benefit_records,
        issue_records,
    )


# =========================================================
# 建立摘要與儲存
# =========================================================

def create_summary(
    calendar_dataframe: pd.DataFrame,
    benefits_dataframe: pd.DataFrame,
    issues_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    建立本階段資料處理摘要。
    """

    summary_rows = [
        {
            "item": "活動日曆資料筆數",
            "count": len(
                calendar_dataframe
            ),
        },
        {
            "item": "優惠內容資料筆數",
            "count": len(
                benefits_dataframe
            ),
        },
        {
            "item": "指定商品優惠筆數",
            "count": int(
                (
                    benefits_dataframe[
                        "scope"
                    ]
                    == "指定商品"
                ).sum()
            )
            if not benefits_dataframe.empty
            else 0,
        },
        {
            "item": "全站或品牌優惠筆數",
            "count": int(
                (
                    benefits_dataframe[
                        "scope"
                    ]
                    == "全站或品牌活動"
                ).sum()
            )
            if not benefits_dataframe.empty
            else 0,
        },
        {
            "item": "資料問題筆數",
            "count": len(
                issues_dataframe
            ),
        },
    ]

    if not benefits_dataframe.empty:
        type_counts = (
            benefits_dataframe[
                "benefit_type"
            ]
            .value_counts(dropna=False)
        )

        for benefit_type, count in (
            type_counts.items()
        ):
            summary_rows.append(
                {
                    "item": (
                        f"優惠類型：{benefit_type}"
                    ),
                    "count": int(count),
                }
            )

    return pd.DataFrame(summary_rows)


def save_results(
    calendar_dataframe: pd.DataFrame,
    benefits_dataframe: pd.DataFrame,
    issues_dataframe: pd.DataFrame,
    summary_dataframe: pd.DataFrame,
) -> None:
    """
    輸出 CSV。
    """

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    calendar_dataframe.to_csv(
        CALENDAR_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    benefits_dataframe.to_csv(
        BENEFITS_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    issues_dataframe.to_csv(
        ISSUES_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    summary_dataframe.to_csv(
        SUMMARY_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )


def print_results(
    calendar_dataframe: pd.DataFrame,
    benefits_dataframe: pd.DataFrame,
    issues_dataframe: pd.DataFrame,
    summary_dataframe: pd.DataFrame,
) -> None:
    """
    終端機顯示執行摘要。
    """

    print("\n" + "=" * 80)
    print("第三階段 B：其他活動資料整理完成")
    print("=" * 80)

    print("\n資料摘要：")
    print(
        summary_dataframe.to_string(
            index=False
        )
    )

    print("\n活動日曆前 10 筆：")

    if calendar_dataframe.empty:
        print("沒有活動日曆資料。")
    else:
        calendar_preview = [
            "source_sheet",
            "campaign_name",
            "campaign_start_date",
            "campaign_end_date",
            "period_text_raw",
        ]

        print(
            calendar_dataframe[
                calendar_preview
            ]
            .head(10)
            .to_string(index=False)
        )

    print("\n優惠內容前 10 筆：")

    if benefits_dataframe.empty:
        print("沒有優惠內容資料。")
    else:
        benefit_preview = [
            "source_sheet",
            "scope",
            "product_id",
            "campaign_name",
            "benefit_type",
            "benefit_content",
            "benefit_start_date",
            "benefit_end_date",
        ]

        print(
            benefits_dataframe[
                benefit_preview
            ]
            .head(10)
            .to_string(index=False)
        )

    print("\n資料問題前 10 筆：")

    if issues_dataframe.empty:
        print("沒有發現資料解析問題。")
    else:
        print(
            issues_dataframe
            .head(10)
            .to_string(index=False)
        )

    print("\n輸出檔案：")
    print(f"1. {CALENDAR_OUTPUT_PATH}")
    print(f"2. {BENEFITS_OUTPUT_PATH}")
    print(f"3. {ISSUES_OUTPUT_PATH}")
    print(f"4. {SUMMARY_OUTPUT_PATH}")


# =========================================================
# 主程式
# =========================================================

def main() -> None:
    """
    整合所有其他活動工作表。
    """

    calendar_records: list[dict] = []
    benefit_records: list[dict] = []
    issue_records: list[dict] = []

    # -----------------------------------------
    # 3 月檔期
    # -----------------------------------------

    records, issues = parse_schedule_sheet(
        MARCH_FILE_PATH,
        source_month=3,
    )

    calendar_records.extend(records)
    issue_records.extend(issues)

    # -----------------------------------------
    # 4 月檔期
    # -----------------------------------------

    records, issues = parse_schedule_sheet(
        APRIL_FILE_PATH,
        source_month=4,
    )

    calendar_records.extend(records)
    issue_records.extend(issues)

    # -----------------------------------------
    # 3 月鋪底
    # -----------------------------------------

    (
        records,
        benefits,
        issues,
    ) = parse_base_promotion_sheet(
        MARCH_FILE_PATH,
        "三月鋪底",
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # -----------------------------------------
    # 4 月鋪底
    # -----------------------------------------

    (
        records,
        benefits,
        issues,
    ) = parse_base_promotion_sheet(
        APRIL_FILE_PATH,
        "四月鋪底",
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # -----------------------------------------
    # 3 月指定商品即享券
    # -----------------------------------------

    benefits, issues = (
        parse_march_product_gifts(
            MARCH_FILE_PATH
        )
    )

    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # -----------------------------------------
    # 4 月吸塵器折價券
    # -----------------------------------------

    benefits, issues = (
        parse_april_vacuum_coupons(
            APRIL_FILE_PATH
        )
    )

    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # -----------------------------------------
    # 品牌日摘要
    # -----------------------------------------

    (
        records,
        benefits,
        issues,
    ) = parse_brand_day_summary(
        APRIL_FILE_PATH
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # -----------------------------------------
    # 包套
    # -----------------------------------------

    (
        records,
        benefits,
        issues,
    ) = parse_package_sheet(
        APRIL_FILE_PATH
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # -----------------------------------------
    # 轉成 DataFrame
    # -----------------------------------------

    calendar_dataframe = pd.DataFrame(
        calendar_records
    )

    benefits_dataframe = pd.DataFrame(
        benefit_records
    )

    issues_dataframe = pd.DataFrame(
        issue_records
    )

    # 日期排序
    if not calendar_dataframe.empty:
        calendar_dataframe = (
            calendar_dataframe.sort_values(
                by=[
                    "campaign_start_date",
                    "source_file",
                    "source_row_number",
                ],
                na_position="last",
            )
            .reset_index(drop=True)
        )

    if not benefits_dataframe.empty:
        benefits_dataframe = (
            benefits_dataframe.sort_values(
                by=[
                    "benefit_start_date",
                    "source_file",
                    "source_sheet",
                    "source_row_number",
                ],
                na_position="last",
            )
            .reset_index(drop=True)
        )

    summary_dataframe = create_summary(
        calendar_dataframe,
        benefits_dataframe,
        issues_dataframe,
    )

    save_results(
        calendar_dataframe,
        benefits_dataframe,
        issues_dataframe,
        summary_dataframe,
    )

    print_results(
        calendar_dataframe,
        benefits_dataframe,
        issues_dataframe,
        summary_dataframe,
    )


if __name__ == "__main__":
    main()