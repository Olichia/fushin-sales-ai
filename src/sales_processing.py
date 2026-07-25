from __future__ import annotations

import pandas as pd


# =========================================================
# 系統必要欄位設定
# =========================================================

REQUIRED_FIELDS = [
    "sale_date",
    "product_id",
    "product_name",
    "quantity",
]


FIELD_LABELS = {
    "sale_date": "銷售日期",
    "product_id": "商品編號",
    "product_name": "商品名稱",
    "quantity": "銷售數量",
}


# =========================================================
# 常見原始欄位名稱
# =========================================================
#
# 系統會利用這些名稱，自動建議 Excel 欄位對應。
#
# 格式：
# 系統標準欄位 -> 可能出現在 Excel 裡的欄位名稱
# =========================================================

COLUMN_ALIASES = {
    "sale_date": [
        "日期",
        "訂單日期",
        "銷售日期",
        "交易日期",
        "出貨日期",
        "建立日期",
        "付款日期",
        "sale_date",
        "sale date",
        "order_date",
        "order date",
        "transaction_date",
        "transaction date",
        "date",
    ],
    "product_id": [
        "商品編號",
        "產品編號",
        "商品料號",
        "產品料號",
        "商品代碼",
        "產品代碼",
        "貨號",
        "料號",
        "品號",
        "編號",
        "sku",
        "sku id",
        "product_id",
        "product id",
        "item_id",
        "item id",
    ],
    "product_name": [
        "商品名稱",
        "產品名稱",
        "商品名",
        "產品名",
        "品名",
        "商品",
        "產品",
        "product_name",
        "product name",
        "item_name",
        "item name",
    ],
    "quantity": [
        "銷量",
        "銷售量",
        "銷售數量",
        "商品數量",
        "購買數量",
        "訂購數量",
        "出貨數量",
        "數量",
        "quantity",
        "qty",
        "sales_qty",
        "sales qty",
        "sales_quantity",
        "sales quantity",
    ],
}


# =========================================================
# 欄位名稱整理
# =========================================================

def normalize_column_name(
    column_name: object,
) -> str:
    """
    將欄位名稱轉成方便比對的格式。

    例如：
    「 銷售 日期 」會變成「銷售日期」
    「Sale_Date」會變成「saledate」
    """

    return (
        str(column_name)
        .strip()
        .lower()
        .replace("\n", "")
        .replace("\r", "")
        .replace("\t", "")
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("－", "")
        .replace("/", "")
        .replace("\\", "")
        .replace("（", "")
        .replace("）", "")
        .replace("(", "")
        .replace(")", "")
        .replace("[", "")
        .replace("]", "")
        .replace("【", "")
        .replace("】", "")
    )


# =========================================================
# 自動建議欄位對應
# =========================================================

def suggest_sales_mapping(
    dataframe: pd.DataFrame,
) -> dict[str, str | None]:
    """
    根據 Excel 欄位名稱，自動建議四個必要欄位。

    回傳格式：

    {
        "sale_date": "訂單日期",
        "product_id": "商品料號",
        "product_name": "品名",
        "quantity": "出貨數量",
    }

    找不到適合欄位時，值會是 None。
    """

    if dataframe is None:
        raise ValueError(
            "無法進行欄位辨識：資料表不存在。"
        )

    if dataframe.empty and len(dataframe.columns) == 0:
        raise ValueError(
            "無法進行欄位辨識：資料表沒有任何欄位。"
        )

    original_columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    normalized_column_lookup = {
        normalize_column_name(column): column
        for column in original_columns
    }

    suggestions: dict[str, str | None] = {}

    for system_field, aliases in COLUMN_ALIASES.items():
        matched_column: str | None = None

        # -------------------------------------------------
        # 第一階段：完全相符
        # -------------------------------------------------
        #
        # 例如 Excel 欄位為「訂單日期」，
        # aliases 中也有「訂單日期」。
        # -------------------------------------------------

        for alias in aliases:
            normalized_alias = normalize_column_name(
                alias
            )

            if normalized_alias in normalized_column_lookup:
                matched_column = (
                    normalized_column_lookup[
                        normalized_alias
                    ]
                )
                break

        # -------------------------------------------------
        # 第二階段：包含關鍵字
        # -------------------------------------------------
        #
        # 例如 Excel 欄位為：
        # 「商品編號(SKU)」
        #
        # 其中包含「商品編號」。
        # -------------------------------------------------

        if matched_column is None:
            for original_column in original_columns:
                normalized_original = (
                    normalize_column_name(
                        original_column
                    )
                )

                for alias in aliases:
                    normalized_alias = (
                        normalize_column_name(
                            alias
                        )
                    )

                    if (
                        normalized_alias
                        and normalized_alias
                        in normalized_original
                    ):
                        matched_column = original_column
                        break

                if matched_column is not None:
                    break

        suggestions[system_field] = matched_column

    return suggestions


# =========================================================
# 欄位對應驗證
# =========================================================

def validate_sales_mapping(
    mapping: dict[str, str | None],
) -> list[str]:
    """
    驗證使用者選擇的欄位對應。

    檢查內容：
    1. 四個必要欄位是否都有選擇
    2. 同一原始欄位是否被重複使用

    回傳錯誤訊息清單。
    沒有問題時回傳空清單。
    """

    errors: list[str] = []

    if not isinstance(mapping, dict):
        return [
            "欄位對應格式錯誤。"
        ]

    # -----------------------------------------------------
    # 檢查必要欄位
    # -----------------------------------------------------

    missing_fields = [
        FIELD_LABELS[field]
        for field in REQUIRED_FIELDS
        if not mapping.get(field)
    ]

    if missing_fields:
        errors.append(
            "尚未選擇必要欄位："
            + "、".join(missing_fields)
        )

    # -----------------------------------------------------
    # 檢查重複選擇
    # -----------------------------------------------------

    selected_columns = [
        str(mapping[field])
        for field in REQUIRED_FIELDS
        if mapping.get(field)
    ]

    duplicate_columns = sorted(
        {
            column
            for column in selected_columns
            if selected_columns.count(column) > 1
        }
    )

    if duplicate_columns:
        errors.append(
            "同一個原始欄位不能對應到多個系統欄位："
            + "、".join(duplicate_columns)
        )

    return errors


# =========================================================
# 文字欄位清理
# =========================================================

def clean_text_column(
    series: pd.Series,
) -> pd.Series:
    """
    清理一般文字欄位。

    處理內容：
    1. 轉成 pandas string 型別
    2. 清除前後空白
    3. 將空字串轉成缺值
    """

    return (
        series.astype("string")
        .str.strip()
        .replace("", pd.NA)
    )


# =========================================================
# 商品編號清理
# =========================================================

def clean_product_id(
    series: pd.Series,
) -> pd.Series:
    """
    將商品編號統一轉成文字。

    例如：
    330290.0 -> 330290

    這可以避免 Excel 將純數字商品編號
    自動讀成浮點數。
    """

    return (
        series.astype("string")
        .str.strip()
        .str.replace(
            r"\.0$",
            "",
            regex=True,
        )
        .replace("", pd.NA)
    )


# =========================================================
# 品質問題文字說明
# =========================================================

def build_issue_description(
    row: pd.Series,
) -> str:
    """
    將每一列的品質問題整理成文字。
    """

    issues: list[str] = []

    if bool(row.get("missing_sale_date", False)):
        issues.append(
            "日期缺漏或格式無法辨識"
        )

    if bool(row.get("missing_product_id", False)):
        issues.append(
            "商品編號缺漏"
        )

    if bool(row.get("missing_product_name", False)):
        issues.append(
            "商品名稱缺漏"
        )

    if bool(row.get("missing_quantity", False)):
        issues.append(
            "銷量缺漏或格式無法辨識"
        )

    if bool(row.get("negative_quantity", False)):
        issues.append(
            "銷量為負數"
        )

    if bool(row.get("exact_duplicate", False)):
        issues.append(
            "完全重複資料"
        )

    if bool(
        row.get(
            "same_day_product_multiple",
            False,
        )
    ):
        issues.append(
            "同日同商品出現多筆資料"
        )

    return "；".join(issues)


# =========================================================
# 標準化銷量資料
# =========================================================

def standardize_sales_data(
    dataframe: pd.DataFrame,
    mapping: dict[str, str | None],
) -> pd.DataFrame:
    """
    根據欄位對應建立標準化銷量資料。

    mapping 格式必須是：

    {
        "sale_date": "原始日期欄位",
        "product_id": "原始商品編號欄位",
        "product_name": "原始商品名稱欄位",
        "quantity": "原始銷量欄位",
    }

    此函式不會刪除任何資料列。
    有問題的資料會透過品質欄位標記。
    """

    if dataframe is None:
        raise ValueError(
            "沒有可供標準化的銷量資料。"
        )

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(
            "銷量資料必須是 pandas DataFrame。"
        )

    if len(dataframe.columns) == 0:
        raise ValueError(
            "資料表沒有任何欄位。"
        )

    # -----------------------------------------------------
    # 驗證欄位對應
    # -----------------------------------------------------

    mapping_errors = validate_sales_mapping(
        mapping
    )

    if mapping_errors:
        raise ValueError(
            "；".join(mapping_errors)
        )

    # -----------------------------------------------------
    # 確認原始欄位真的存在
    # -----------------------------------------------------

    missing_source_columns = [
        str(source_column)
        for source_column in mapping.values()
        if (
            source_column
            and source_column not in dataframe.columns
        )
    ]

    if missing_source_columns:
        raise ValueError(
            "以下原始欄位不存在於目前資料表："
            + "、".join(
                missing_source_columns
            )
        )

    # -----------------------------------------------------
    # 建立重新命名規則
    # -----------------------------------------------------
    #
    # 新頁面保存的 mapping 格式是：
    #
    # sale_date -> 訂單日期
    #
    # pandas rename 需要的格式是：
    #
    # 訂單日期 -> sale_date
    # -----------------------------------------------------

    rename_mapping = {
        str(original_column): system_field
        for system_field, original_column
        in mapping.items()
        if original_column
    }

    standardized = dataframe.rename(
        columns=rename_mapping
    ).copy()

    # -----------------------------------------------------
    # 再次確認重新命名後的必要欄位
    # -----------------------------------------------------

    missing_standard_columns = [
        field
        for field in REQUIRED_FIELDS
        if field not in standardized.columns
    ]

    if missing_standard_columns:
        readable_missing_fields = [
            FIELD_LABELS.get(
                field,
                field,
            )
            for field in missing_standard_columns
        ]

        raise ValueError(
            "標準化後仍缺少必要欄位："
            + "、".join(
                readable_missing_fields
            )
        )

    # -----------------------------------------------------
    # 只保留系統需要的四個主要欄位
    # -----------------------------------------------------

    standardized = standardized[
        REQUIRED_FIELDS
    ].copy()

    # -----------------------------------------------------
    # 保存 Excel 原始資料列位置
    # -----------------------------------------------------
    #
    # Excel 第 1 列通常為欄位標題，
    # 因此第一筆資料從第 2 列開始。
    # -----------------------------------------------------

    standardized.insert(
        0,
        "source_row_number",
        range(
            2,
            len(standardized) + 2,
        ),
    )

    # -----------------------------------------------------
    # 保存原始值
    # -----------------------------------------------------

    standardized["original_sale_date"] = (
        standardized["sale_date"]
    )

    standardized["original_product_id"] = (
        standardized["product_id"]
    )

    standardized["original_quantity"] = (
        standardized["quantity"]
    )

    # -----------------------------------------------------
    # 日期標準化
    # -----------------------------------------------------

    standardized["sale_date"] = pd.to_datetime(
        standardized["sale_date"],
        errors="coerce",
    )

    # -----------------------------------------------------
    # 商品編號標準化
    # -----------------------------------------------------

    standardized["product_id"] = clean_product_id(
        standardized["product_id"]
    )

    # -----------------------------------------------------
    # 商品名稱標準化
    # -----------------------------------------------------

    standardized["product_name"] = clean_text_column(
        standardized["product_name"]
    )

    # -----------------------------------------------------
    # 銷量標準化
    # -----------------------------------------------------

    standardized["quantity"] = pd.to_numeric(
        standardized["quantity"],
        errors="coerce",
    )

    # -----------------------------------------------------
    # 品質檢查：必要欄位缺值
    # -----------------------------------------------------

    standardized["missing_sale_date"] = (
        standardized["sale_date"].isna()
    )

    standardized["missing_product_id"] = (
        standardized["product_id"].isna()
    )

    standardized["missing_product_name"] = (
        standardized["product_name"].isna()
    )

    standardized["missing_quantity"] = (
        standardized["quantity"].isna()
    )

    # -----------------------------------------------------
    # 品質檢查：負數及零銷量
    # -----------------------------------------------------

    standardized["negative_quantity"] = (
        standardized["quantity"].notna()
        & (
            standardized["quantity"] < 0
        )
    )

    standardized["zero_quantity"] = (
        standardized["quantity"].notna()
        & (
            standardized["quantity"] == 0
        )
    )

    # -----------------------------------------------------
    # 品質檢查：完全重複
    # -----------------------------------------------------
    #
    # 日期、商品編號、商品名稱、銷量全部相同。
    # -----------------------------------------------------

    standardized["exact_duplicate"] = (
        standardized.duplicated(
            subset=[
                "sale_date",
                "product_id",
                "product_name",
                "quantity",
            ],
            keep=False,
        )
    )

    # -----------------------------------------------------
    # 品質檢查：同日同商品出現多筆
    # -----------------------------------------------------
    #
    # 這不一定是錯誤，因此只標記，
    # 系統不會自動刪除或合併。
    # -----------------------------------------------------

    standardized[
        "same_day_product_multiple"
    ] = standardized.duplicated(
        subset=[
            "sale_date",
            "product_id",
        ],
        keep=False,
    )

    # -----------------------------------------------------
    # 建立品質問題總旗標
    # -----------------------------------------------------
    #
    # 零銷量只作為提示，
    # 目前不列入主要品質問題。
    # 這與原本 pages/3_資料品質.py 的規則一致。
    # -----------------------------------------------------

    issue_columns = [
        "missing_sale_date",
        "missing_product_id",
        "missing_product_name",
        "missing_quantity",
        "negative_quantity",
        "exact_duplicate",
        "same_day_product_multiple",
    ]

    standardized["has_quality_issue"] = (
        standardized[
            issue_columns
        ].any(
            axis=1
        )
    )

    # -----------------------------------------------------
    # 建立品質問題文字說明
    # -----------------------------------------------------

    standardized[
        "quality_issue_description"
    ] = standardized.apply(
        build_issue_description,
        axis=1,
    )

    # -----------------------------------------------------
    # 統一輸出欄位順序
    # -----------------------------------------------------

    ordered_columns = [
        "source_row_number",
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
        "has_quality_issue",
        "quality_issue_description",
        "exact_duplicate",
        "same_day_product_multiple",
        "missing_sale_date",
        "missing_product_id",
        "missing_product_name",
        "missing_quantity",
        "negative_quantity",
        "zero_quantity",
        "original_sale_date",
        "original_product_id",
        "original_quantity",
    ]

    return standardized[
        ordered_columns
    ].copy()


# =========================================================
# 建立資料品質摘要
# =========================================================

def create_sales_quality_summary(
    standardized_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    建立適合直接顯示於 Streamlit 的品質摘要。

    回傳欄位：
    問題、筆數
    """

    required_quality_columns = [
        "missing_sale_date",
        "missing_product_id",
        "missing_product_name",
        "missing_quantity",
        "negative_quantity",
        "zero_quantity",
        "exact_duplicate",
        "same_day_product_multiple",
        "has_quality_issue",
    ]

    missing_columns = [
        column
        for column in required_quality_columns
        if column not in standardized_dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "無法建立品質摘要，缺少欄位："
            + "、".join(missing_columns)
        )

    summary_items = [
        {
            "問題": "總資料列數",
            "筆數": len(
                standardized_dataframe
            ),
        },
        {
            "問題": "有任一品質問題",
            "筆數": int(
                standardized_dataframe[
                    "has_quality_issue"
                ].sum()
            ),
        },
        {
            "問題": "日期缺漏或無法辨識",
            "筆數": int(
                standardized_dataframe[
                    "missing_sale_date"
                ].sum()
            ),
        },
        {
            "問題": "商品編號缺漏",
            "筆數": int(
                standardized_dataframe[
                    "missing_product_id"
                ].sum()
            ),
        },
        {
            "問題": "商品名稱缺漏",
            "筆數": int(
                standardized_dataframe[
                    "missing_product_name"
                ].sum()
            ),
        },
        {
            "問題": "銷量缺漏或無法辨識",
            "筆數": int(
                standardized_dataframe[
                    "missing_quantity"
                ].sum()
            ),
        },
        {
            "問題": "銷量為負數",
            "筆數": int(
                standardized_dataframe[
                    "negative_quantity"
                ].sum()
            ),
        },
        {
            "問題": "銷量為零",
            "筆數": int(
                standardized_dataframe[
                    "zero_quantity"
                ].sum()
            ),
        },
        {
            "問題": "完全重複資料列",
            "筆數": int(
                standardized_dataframe[
                    "exact_duplicate"
                ].sum()
            ),
        },
        {
            "問題": "同日同商品多筆",
            "筆數": int(
                standardized_dataframe[
                    "same_day_product_multiple"
                ].sum()
            ),
        },
    ]

    return pd.DataFrame(
        summary_items
    )


# =========================================================
# 取得品質問題資料
# =========================================================

def get_sales_issues_dataframe(
    standardized_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    從標準化資料中篩選出需要確認的資料列。

    不會修改原始 DataFrame。
    """

    if (
        "has_quality_issue"
        not in standardized_dataframe.columns
    ):
        raise ValueError(
            "資料表缺少 has_quality_issue 欄位。"
        )

    return standardized_dataframe[
        standardized_dataframe[
            "has_quality_issue"
        ]
    ].copy()


# =========================================================
# 建立銷量資料摘要
# =========================================================

def create_sales_data_summary(
    standardized_dataframe: pd.DataFrame,
) -> dict[str, object]:
    """
    建立最終確認區可以使用的摘要資訊。

    回傳範例：

    {
        "total_rows": 1000,
        "issue_rows": 25,
        "valid_rows": 975,
        "start_date": Timestamp(...),
        "end_date": Timestamp(...),
        "date_range_text": "2026-01-01 至 2026-03-31",
        "product_count": 80,
        "total_quantity": 15200.0,
    }
    """

    if standardized_dataframe is None:
        raise ValueError(
            "無法建立摘要：標準化資料不存在。"
        )

    total_rows = len(
        standardized_dataframe
    )

    issue_rows = int(
        standardized_dataframe[
            "has_quality_issue"
        ].sum()
    )

    valid_rows = total_rows - issue_rows

    valid_dates = standardized_dataframe[
        "sale_date"
    ].dropna()

    if valid_dates.empty:
        start_date = None
        end_date = None
        date_range_text = "無有效日期"

    else:
        start_date = valid_dates.min()
        end_date = valid_dates.max()

        date_range_text = (
            f"{start_date:%Y-%m-%d}"
            " 至 "
            f"{end_date:%Y-%m-%d}"
        )

    product_count = int(
        standardized_dataframe[
            "product_id"
        ].dropna().nunique()
    )

    total_quantity = float(
        standardized_dataframe[
            "quantity"
        ].dropna().sum()
    )

    return {
        "total_rows": total_rows,
        "issue_rows": issue_rows,
        "valid_rows": valid_rows,
        "start_date": start_date,
        "end_date": end_date,
        "date_range_text": date_range_text,
        "product_count": product_count,
        "total_quantity": total_quantity,
    }