from pathlib import Path
import re

import pandas as pd

from src.activity_date_utils import parse_flexible_date


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

MARCH_FILE_PATH = RAW_DATA_DIR / "3月品牌活動_通路.xlsx"
APRIL_FILE_PATH = RAW_DATA_DIR / "4月品牌活動_通路.xlsx"

CLEANED_OUTPUT_PATH = (
    PROCESSED_DIR / "activity_main_cleaned.csv"
)

ISSUES_OUTPUT_PATH = (
    PROCESSED_DIR / "activity_parse_issues.csv"
)

SUMMARY_OUTPUT_PATH = (
    PROCESSED_DIR / "activity_quality_summary.csv"
)


# =========================================================
# 欄位名稱對照
# =========================================================

COLUMN_ALIASES = {
    "編號": "product_id",
    "商品編號": "product_id",
    "主商品編號": "product_id",

    "商品名稱": "product_name",
    "產品名稱": "product_name",
    "品名": "product_name",

    "加碼贈品": "activity_gift",
    "活動贈品": "activity_gift",

    "短促時間": "promotion_period_raw",
    "促銷時間": "promotion_period_raw",
    "活動時間": "promotion_period_raw",

    "加碼送": "bonus_period_raw",
    "加碼期間": "bonus_period_raw",

    "贈品品名": "bonus_gift_name",
    "加碼贈品品名": "bonus_gift_name",

    "售價(含稅)": "campaign_price",
    "售價（含稅）": "campaign_price",
    "活動價": "campaign_price",
    "售價": "campaign_price",

    "備註": "remark",
}


STANDARD_COLUMNS = [
    "product_id",
    "product_name",
    "activity_gift",
    "promotion_period_raw",
    "bonus_period_raw",
    "bonus_gift_name",
    "campaign_price",
    "remark",
]


# =========================================================
# 新模板「活動表」欄位對照
#
# 新模板把「開始日期／結束日期」拆成兩個獨立欄位，
# 跟舊格式「單一合併日期文字欄」架構完全不同，
# 所以獨立一套別名表與標準欄位，不與 COLUMN_ALIASES 混用
# （避免「加碼送」語意衝突：舊格式指向日期期間欄，
# 新模板實際內容是贈品文字）。
# =========================================================

NEW_TEMPLATE_START_DATE_COLUMNS = {
    "起始日期",
    "開始日期",
    "活動開始日期",
}


NEW_TEMPLATE_END_DATE_COLUMNS = {
    "結束日期",
    "活動結束日期",
}


NEW_TEMPLATE_COLUMN_ALIASES = {
    "商品編號": "product_id",
    "商品名稱": "product_name",
    "品類": "product_category",
    "起始日期": "activity_start_date_raw",
    "開始日期": "activity_start_date_raw",
    "活動開始日期": "activity_start_date_raw",
    "結束日期": "activity_end_date_raw",
    "活動結束日期": "activity_end_date_raw",
    "售價(含稅)": "campaign_price",
    "售價（含稅）": "campaign_price",
    "活動售價(含稅)": "campaign_price",
    "活動售價（含稅）": "campaign_price",
    "活動價": "campaign_price",
    "售價": "campaign_price",
    "活動贈品": "activity_gift",
    "贈品": "activity_gift",
    "加碼贈品": "bonus_gift_name",
    "加碼送": "bonus_gift_text",
    "加碼活動": "bonus_campaign_text",
    "活動類型": "activity_tag_raw",
    "類型": "activity_tag_raw",
}


NEW_TEMPLATE_STANDARD_COLUMNS = [
    "product_id",
    "product_name",
    "product_category",
    "campaign_price",
    "activity_gift",
    "bonus_gift_text",
    "bonus_campaign_text",
]


def detect_activity_sheet_format(
    raw_dataframe: pd.DataFrame,
) -> str:
    """
    判斷「活動表」是新模板格式（開始/結束日期分兩欄）
    或舊格式（單一合併日期文字欄），回傳
    "new_template" 或 "legacy"。
    """

    normalized_columns = {
        normalize_column_name(column)
        for column in raw_dataframe.columns
    }

    has_start_date = bool(
        normalized_columns
        & NEW_TEMPLATE_START_DATE_COLUMNS
    )
    has_end_date = bool(
        normalized_columns
        & NEW_TEMPLATE_END_DATE_COLUMNS
    )

    if has_start_date and has_end_date:
        return "new_template"

    return "legacy"


# =========================================================
# 基本資料清理函式
# =========================================================

def normalize_column_name(column_name: object) -> str:
    """
    清除欄位名稱前後空白與換行。
    """
    return (
        str(column_name)
        .strip()
        .replace("\n", "")
    )


def clean_text(series: pd.Series) -> pd.Series:
    """
    清理文字欄位：
    1. 轉成 pandas 文字型別
    2. 清除前後空白
    3. 空字串轉成缺值
    """
    return (
        series.astype("string")
        .str.strip()
        .replace("", pd.NA)
    )


def clean_product_id(series: pd.Series) -> pd.Series:
    """
    商品編號統一轉成文字。

    例如：
    330290.0 -> 330290
    """
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .replace("", pd.NA)
    )


def rename_activity_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    統一活動表欄位名稱。
    """
    dataframe = dataframe.copy()

    dataframe.columns = [
        normalize_column_name(column)
        for column in dataframe.columns
    ]

    rename_mapping = {
        column: COLUMN_ALIASES[column]
        for column in dataframe.columns
        if column in COLUMN_ALIASES
    }

    dataframe = dataframe.rename(
        columns=rename_mapping
    )

    # 檢查統一名稱後是否產生重複欄位
    duplicate_columns = dataframe.columns[
        dataframe.columns.duplicated()
    ].tolist()

    if duplicate_columns:
        print(
            "\n警告：統一欄位名稱後發現重複欄位："
            f"{duplicate_columns}"
        )

        # 同名欄位只保留第一欄
        dataframe = dataframe.loc[
            :,
            ~dataframe.columns.duplicated()
        ].copy()

    # 不同月份可能缺少某些欄位
    for column in STANDARD_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = pd.NA

    return dataframe


# =========================================================
# 活動 Excel 讀取
# =========================================================

def load_activity_sheet(
    file_path: Path,
    source_month: int,
) -> pd.DataFrame:
    """
    讀取指定 Excel 中名稱為「活動表」的工作表。
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"找不到活動檔案：{file_path}"
        )

    try:
        dataframe = pd.read_excel(
            file_path,
            sheet_name="活動表",
            engine="openpyxl",
        )

    except ValueError as error:
        raise ValueError(
            f"{file_path.name} 中找不到「活動表」工作表。"
        ) from error

    except PermissionError as error:
        raise PermissionError(
            f"無法讀取 {file_path.name}，請先關閉 Excel。"
        ) from error

    # Excel 第一列通常是欄位名稱
    # 所以第一筆資料是 Excel 第 2 列
    dataframe.insert(
        0,
        "source_row_number",
        range(2, len(dataframe) + 2),
    )

    dataframe["source_file"] = file_path.name
    dataframe["source_sheet"] = "活動表"
    dataframe["source_month"] = source_month

    return dataframe


# =========================================================
# 日期解析
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


def normalize_period_text(value: object) -> str:
    """
    統一活動期間文字中的符號。
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
        "、": ",",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def extract_activity_tag(line: str) -> str:
    """
    從活動文字中判斷初步活動標籤。

    注意：
    這只是文字分類，不代表企業正式定義。
    """
    tags = []

    if "限搶" in line or "限時搶購" in line:
        tags.append("限時搶購")

    if "包套" in line:
        tags.append("包套")

    if "品牌日" in line:
        tags.append("品牌日")

    if "品牌週" in line or "品牌周" in line:
        tags.append("品牌週")

    if "加碼" in line:
        tags.append("加碼")

    if "贈" in line:
        tags.append("贈品")

    if not tags:
        tags.append("一般活動期間")

    return "、".join(tags)


def parse_period_text(
    period_text: object,
    year: int = 2026,
) -> list[dict]:
    """
    將同一儲存格中的一個或多個日期拆成多筆。

    可處理：
    3/2-3/6
    4/18~4/19
    4/30
    4/5+4/13+4/20
    4/5加碼限搶
    """

    normalized_text = normalize_period_text(
        period_text
    )

    if not normalized_text:
        return []

    results = []

    # 依換行拆開，保留日期附近文字
    lines = normalized_text.splitlines()

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        line = line.strip()

        if not line:
            continue

        matches = list(
            DATE_PATTERN.finditer(line)
        )

        for match_number, match in enumerate(
            matches,
            start=1,
        ):
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

                end_day = int(
                    end_day_text
                )

            try:
                start_date = pd.Timestamp(
                    year=year,
                    month=start_month,
                    day=start_day,
                )

                end_date = pd.Timestamp(
                    year=year,
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
                    "period_line_number": (
                        line_number
                    ),
                    "period_match_number": (
                        match_number
                    ),
                    "period_source_line": line,
                    "matched_date_text": (
                        match.group(0)
                    ),
                    "activity_tag": (
                        extract_activity_tag(line)
                    ),
                    "activity_start_date": (
                        start_date
                    ),
                    "activity_end_date": (
                        end_date
                    ),
                    "date_valid": date_valid,
                }
            )

    return results


# =========================================================
# 活動資料清理
# =========================================================

def prepare_activity_dataframe(
    raw_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    統一欄位、向下填補商品資料並清理格式。

    自動判斷是新模板格式（開始/結束日期分兩欄）
    或舊格式（單一合併日期文字欄），並分派到
    對應的整理函式。
    """

    if (
        detect_activity_sheet_format(raw_dataframe)
        == "new_template"
    ):
        return _prepare_new_template_activity_dataframe(
            raw_dataframe
        )

    return _prepare_legacy_activity_dataframe(
        raw_dataframe
    )


def _prepare_new_template_activity_dataframe(
    raw_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    整理新模板「活動表」：
    商品編號、商品名稱、品類、活動開始/結束日期(分兩欄)、
    活動售價(含稅)、贈品、[四月多一欄]加碼送、加碼活動。

    此格式的日期已經是「開始/結束」兩個獨立欄位，
    不需要（也不能）走 promotion_period_raw +
    parse_period_text() 那條「單一合併日期文字欄」路徑，
    在這裡直接解析成 activity_start_date/end_date，
    並標記 is_pre_split=True 供
    explode_promotion_periods() 短路辨識。
    """

    dataframe = raw_dataframe.copy()

    dataframe.columns = [
        normalize_column_name(column)
        for column in dataframe.columns
    ]

    rename_mapping = {
        column: NEW_TEMPLATE_COLUMN_ALIASES[column]
        for column in dataframe.columns
        if column in NEW_TEMPLATE_COLUMN_ALIASES
    }

    dataframe = dataframe.rename(
        columns=rename_mapping
    )

    for column in [
        *NEW_TEMPLATE_STANDARD_COLUMNS,
        "activity_start_date_raw",
        "activity_end_date_raw",
        "activity_tag_raw",
        "bonus_gift_name",
    ]:
        if column not in dataframe.columns:
            dataframe[column] = pd.NA

    dataframe[
        ["product_id", "product_name", "product_category"]
    ] = dataframe[
        ["product_id", "product_name", "product_category"]
    ].ffill()

    dataframe["product_id"] = (
        clean_product_id(
            dataframe["product_id"]
        )
    )

    text_columns = [
        "product_name",
        "product_category",
        "activity_gift",
        "bonus_gift_name",
        "bonus_gift_text",
        "bonus_campaign_text",
        "activity_tag_raw",
    ]

    for column in text_columns:
        dataframe[column] = clean_text(
            dataframe[column]
        )

    dataframe["campaign_price"] = (
        pd.to_numeric(
            dataframe["campaign_price"],
            errors="coerce",
        )
    )

    dataframe["activity_start_date"] = (
        dataframe["activity_start_date_raw"].apply(
            parse_flexible_date
        )
    )

    dataframe["activity_end_date"] = (
        dataframe["activity_end_date_raw"].apply(
            parse_flexible_date
        )
    )

    dataframe["date_valid"] = (
        dataframe["activity_start_date"].notna()
        & dataframe["activity_end_date"].notna()
        & (
            dataframe["activity_end_date"]
            >= dataframe["activity_start_date"]
        )
    )

    combined_gift_text = (
        dataframe["activity_gift"].fillna("")
        + " "
        + dataframe["bonus_gift_name"].fillna("")
        + " "
        + dataframe["bonus_gift_text"].fillna("")
        + " "
        + dataframe["bonus_campaign_text"].fillna("")
    )

    # 新模板本身有真實的「活動類型」欄位（受控詞彙，如
    # 「短促」「限搶包套」），優先直接使用；只有該值缺漏時
    # 才退回用贈品/加碼送文字關鍵字猜測（extract_activity_tag）
    # 當保險。
    dataframe["activity_tag"] = dataframe[
        "activity_tag_raw"
    ].where(
        dataframe["activity_tag_raw"].notna(),
        combined_gift_text.apply(extract_activity_tag),
    )

    dataframe["is_pre_split"] = True

    # 補上舊格式專屬欄位（維持與 legacy 分支相同的
    # 欄位集合，讓 pd.concat／下游 create_quality_summary()
    # 等函式不需要判斷分支就能安全存取這些欄位）。
    for column in [
        "promotion_period_raw",
        "bonus_period_raw",
        "remark",
    ]:
        dataframe[column] = pd.NA

    columns_to_keep = [
        "source_file",
        "source_sheet",
        "source_month",
        "source_row_number",
        *NEW_TEMPLATE_STANDARD_COLUMNS,
        "promotion_period_raw",
        "bonus_period_raw",
        "bonus_gift_name",
        "remark",
        "activity_start_date",
        "activity_end_date",
        "date_valid",
        "activity_tag",
        "is_pre_split",
    ]

    return dataframe[
        columns_to_keep
    ].copy()


def _prepare_legacy_activity_dataframe(
    raw_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    整理舊格式「活動表」（單一合併日期文字欄）。
    """

    dataframe = rename_activity_columns(
        raw_dataframe
    )

    # 商品編號和商品名稱的空白
    # 代表沿用上一列商品
    dataframe[
        ["product_id", "product_name"]
    ] = dataframe[
        ["product_id", "product_name"]
    ].ffill()

    dataframe["product_id"] = (
        clean_product_id(
            dataframe["product_id"]
        )
    )

    text_columns = [
        "product_name",
        "activity_gift",
        "promotion_period_raw",
        "bonus_period_raw",
        "bonus_gift_name",
        "remark",
    ]

    for column in text_columns:
        dataframe[column] = clean_text(
            dataframe[column]
        )

    dataframe["campaign_price"] = (
        pd.to_numeric(
            dataframe["campaign_price"],
            errors="coerce",
        )
    )

    dataframe["is_pre_split"] = False

    columns_to_keep = [
        "source_file",
        "source_sheet",
        "source_month",
        "source_row_number",
        *STANDARD_COLUMNS,
        "is_pre_split",
    ]

    return dataframe[
        columns_to_keep
    ].copy()


def explode_promotion_periods(
    prepared_dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    將每列短促時間拆成一個活動期間一列。

    同時建立解析問題表。
    """

    activity_records = []
    issue_records = []

    for _, row in prepared_dataframe.iterrows():
        # 新模板的活動開始/結束日期已經是獨立欄位、
        # 事先解析好，不需要（也不能）再走
        # promotion_period_raw + parse_period_text()
        # 那條「單一合併日期文字欄」路徑。
        if row.get("is_pre_split", False):
            if not row["date_valid"]:
                issue_records.append(
                    {
                        "source_file": row["source_file"],
                        "source_sheet": row["source_sheet"],
                        "source_row_number": (
                            row["source_row_number"]
                        ),
                        "product_id": row["product_id"],
                        "product_name": row["product_name"],
                        "issue_type": "活動日期不合法",
                        "problem_text": (
                            f"{row.get('activity_start_date')}"
                            f"~{row.get('activity_end_date')}"
                        ),
                    }
                )

                continue

            activity_records.append(
                {
                    "source_file": row["source_file"],
                    "source_sheet": row["source_sheet"],
                    "source_month": row["source_month"],
                    "source_row_number": (
                        row["source_row_number"]
                    ),
                    "product_id": row["product_id"],
                    "product_name": row["product_name"],
                    "campaign_price": row["campaign_price"],
                    "activity_gift": row["activity_gift"],
                    "bonus_period_raw": pd.NA,
                    "bonus_gift_name": row.get(
                        "bonus_gift_name", pd.NA
                    ),
                    "remark": pd.NA,
                    "promotion_period_raw": pd.NA,
                    "product_category": row.get(
                        "product_category", pd.NA
                    ),
                    "bonus_gift_text": row.get(
                        "bonus_gift_text", pd.NA
                    ),
                    "bonus_campaign_text": row.get(
                        "bonus_campaign_text", pd.NA
                    ),
                    "activity_tag": row["activity_tag"],
                    "activity_start_date": (
                        row["activity_start_date"]
                    ),
                    "activity_end_date": (
                        row["activity_end_date"]
                    ),
                    "date_valid": True,
                }
            )

            continue

        parsed_periods = parse_period_text(
            row["promotion_period_raw"]
        )

        # 短促時間完全沒有資料
        if not parsed_periods:
            issue_records.append(
                {
                    "source_file": (
                        row["source_file"]
                    ),
                    "source_sheet": (
                        row["source_sheet"]
                    ),
                    "source_row_number": (
                        row["source_row_number"]
                    ),
                    "product_id": (
                        row["product_id"]
                    ),
                    "product_name": (
                        row["product_name"]
                    ),
                    "issue_type": (
                        "短促時間為空或無法解析"
                    ),
                    "problem_text": (
                        row["promotion_period_raw"]
                    ),
                }
            )

            continue

        for parsed in parsed_periods:
            record = {
                "source_file": (
                    row["source_file"]
                ),
                "source_sheet": (
                    row["source_sheet"]
                ),
                "source_month": (
                    row["source_month"]
                ),
                "source_row_number": (
                    row["source_row_number"]
                ),
                "product_id": (
                    row["product_id"]
                ),
                "product_name": (
                    row["product_name"]
                ),
                "campaign_price": (
                    row["campaign_price"]
                ),
                "activity_gift": (
                    row["activity_gift"]
                ),
                "bonus_period_raw": (
                    row["bonus_period_raw"]
                ),
                "bonus_gift_name": (
                    row["bonus_gift_name"]
                ),
                "remark": (
                    row["remark"]
                ),
                "promotion_period_raw": (
                    row["promotion_period_raw"]
                ),
                **{
                    key: value
                    for key, value in parsed.items()
                    if key not in {
                        "period_line_number",
                        "period_match_number",
                        "period_source_line",
                        "matched_date_text",
                    }
                },
            }

            activity_records.append(
                record
            )

            if not parsed["date_valid"]:
                issue_records.append(
                    {
                        "source_file": (
                            row["source_file"]
                        ),
                        "source_sheet": (
                            row["source_sheet"]
                        ),
                        "source_row_number": (
                            row[
                                "source_row_number"
                            ]
                        ),
                        "product_id": (
                            row["product_id"]
                        ),
                        "product_name": (
                            row["product_name"]
                        ),
                        "issue_type": (
                            "活動日期不合法"
                        ),
                        "problem_text": (
                            parsed[
                                "matched_date_text"
                            ]
                        ),
                    }
                )

        raw_text = normalize_period_text(
            row["promotion_period_raw"]
        )

        suspicious_patterns = [
            "4-/13",
            "/-",
            "-/",
        ]

        for suspicious_text in (
            suspicious_patterns
        ):
            if suspicious_text in raw_text:
                issue_records.append(
                    {
                        "source_file": (
                            row["source_file"]
                        ),
                        "source_sheet": (
                            row["source_sheet"]
                        ),
                        "source_row_number": (
                            row[
                                "source_row_number"
                            ]
                        ),
                        "product_id": (
                            row["product_id"]
                        ),
                        "product_name": (
                            row["product_name"]
                        ),
                        "issue_type": (
                            "疑似日期輸入錯字"
                        ),
                        "problem_text": (
                            raw_text
                        ),
                    }
                )

    activity_dataframe = pd.DataFrame(
        activity_records
    )

    issues_dataframe = pd.DataFrame(
        issue_records
    )

    return (
        activity_dataframe,
        issues_dataframe,
    )


# =========================================================
# 品質摘要
# =========================================================

def create_quality_summary(
    prepared_dataframe: pd.DataFrame,
    activity_dataframe: pd.DataFrame,
    issues_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    建立活動資料品質摘要。
    """

    summary = [
        {
            "item": "原始活動資料列數",
            "count": len(
                prepared_dataframe
            ),
        },
        {
            "item": "拆解後活動期間筆數",
            "count": len(
                activity_dataframe
            ),
        },
        {
            "item": "商品編號缺漏",
            "count": int(
                prepared_dataframe[
                    "product_id"
                ].isna().sum()
            ),
        },
        {
            "item": "商品名稱缺漏",
            "count": int(
                prepared_dataframe[
                    "product_name"
                ].isna().sum()
            ),
        },
        {
            "item": (
                "活動價格缺漏或無法辨識"
            ),
            "count": int(
                prepared_dataframe[
                    "campaign_price"
                ].isna().sum()
            ),
        },
        {
            "item": "短促時間缺漏",
            "count": int(
                prepared_dataframe.loc[
                    ~prepared_dataframe[
                        "is_pre_split"
                    ].astype(bool),
                    "promotion_period_raw",
                ].isna().sum()
            ),
        },
        {
            "item": "日期解析問題筆數",
            "count": len(
                issues_dataframe
            ),
        },
    ]

    return pd.DataFrame(
        summary
    )


# =========================================================
# 儲存結果
# =========================================================

def save_results(
    activity_dataframe: pd.DataFrame,
    issues_dataframe: pd.DataFrame,
    summary_dataframe: pd.DataFrame,
) -> None:
    """
    儲存清理結果。
    """

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    activity_dataframe.to_csv(
        CLEANED_OUTPUT_PATH,
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


# =========================================================
# 顯示結果
# =========================================================

def print_results(
    activity_dataframe: pd.DataFrame,
    issues_dataframe: pd.DataFrame,
    summary_dataframe: pd.DataFrame,
) -> None:
    """
    在終端機顯示執行結果。
    """

    print("\n" + "=" * 80)
    print("3 月與 4 月主要活動表清理完成")
    print("=" * 80)

    print("\n品質摘要：")
    print(
        summary_dataframe.to_string(
            index=False
        )
    )

    print("\n前 10 筆拆解結果：")

    preview_columns = [
        "source_file",
        "source_row_number",
        "product_id",
        "product_name",
        "activity_start_date",
        "activity_end_date",
        "campaign_price",
        "activity_tag",
    ]

    if activity_dataframe.empty:
        print("沒有成功解析出活動資料。")
    else:
        print(
            activity_dataframe[
                preview_columns
            ]
            .head(10)
            .to_string(index=False)
        )

    print("\n日期解析問題前 10 筆：")

    if issues_dataframe.empty:
        print("未發現日期解析問題。")
    else:
        print(
            issues_dataframe
            .head(10)
            .to_string(index=False)
        )

    print("\n輸出檔案：")
    print(f"1. {CLEANED_OUTPUT_PATH}")
    print(f"2. {ISSUES_OUTPUT_PATH}")
    print(f"3. {SUMMARY_OUTPUT_PATH}")


# =========================================================
# 主程式
# =========================================================

def main() -> None:
    """
    主要執行流程。
    """

    # 分別讀取 3 月與 4 月
    march_raw = load_activity_sheet(
        MARCH_FILE_PATH,
        source_month=3,
    )

    april_raw = load_activity_sheet(
        APRIL_FILE_PATH,
        source_month=4,
    )

    # 先分別清理
    # 避免不同月份欄位合併後產生重複欄位
    march_prepared = (
        prepare_activity_dataframe(
            march_raw
        )
    )

    april_prepared = (
        prepare_activity_dataframe(
            april_raw
        )
    )

    # 清理完成後才合併
    prepared_dataframe = pd.concat(
        [
            march_prepared,
            april_prepared,
        ],
        ignore_index=True,
    )

    (
        activity_dataframe,
        issues_dataframe,
    ) = explode_promotion_periods(
        prepared_dataframe
    )

    summary_dataframe = (
        create_quality_summary(
            prepared_dataframe,
            activity_dataframe,
            issues_dataframe,
        )
    )

    save_results(
        activity_dataframe,
        issues_dataframe,
        summary_dataframe,
    )

    print_results(
        activity_dataframe,
        issues_dataframe,
        summary_dataframe,
    )


if __name__ == "__main__":
    main()
