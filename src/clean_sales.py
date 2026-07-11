from pathlib import Path

import pandas as pd


# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 輸入與輸出路徑
RAW_FILE_PATH = PROJECT_ROOT / "data" / "raw" / "銷量.xlsx"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

CLEANED_OUTPUT_PATH = PROCESSED_DIR / "sales_cleaned.csv"
ISSUES_OUTPUT_PATH = PROCESSED_DIR / "sales_quality_issues.csv"
SUMMARY_OUTPUT_PATH = PROCESSED_DIR / "sales_quality_summary.csv"


# 原始欄位名稱可能略有不同，因此建立對照表
COLUMN_ALIASES = {
    "日期": "sale_date",
    "訂單日期": "sale_date",
    "銷售日期": "sale_date",
    "商品編號": "product_id",
    "產品編號": "product_id",
    "編號": "product_id",
    "SKU": "product_id",
    "商品名稱": "product_name",
    "產品名稱": "product_name",
    "品名": "product_name",
    "銷量": "quantity",
    "銷售量": "quantity",
    "數量": "quantity",
}


REQUIRED_COLUMNS = [
    "sale_date",
    "product_id",
    "product_name",
    "quantity",
]


def normalize_column_name(column_name: object) -> str:
    """
    清除欄位名稱前後空白及換行。
    """
    return str(column_name).strip().replace("\n", "")


def rename_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    將中文欄位名稱轉換成系統統一欄位名稱。
    """
    dataframe = dataframe.copy()

    dataframe.columns = [
        normalize_column_name(column)
        for column in dataframe.columns
    ]

    rename_mapping = {}

    for column in dataframe.columns:
        if column in COLUMN_ALIASES:
            rename_mapping[column] = COLUMN_ALIASES[column]

    dataframe = dataframe.rename(columns=rename_mapping)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "銷量表缺少必要欄位："
            + ", ".join(missing_columns)
            + f"\n目前讀取到的欄位：{list(dataframe.columns)}"
        )

    return dataframe


def clean_text_column(series: pd.Series) -> pd.Series:
    """
    清理文字欄位：
    1. 轉成 pandas 文字型別
    2. 清除前後空白
    3. 將空字串轉成缺值
    """
    cleaned = (
        series.astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    return cleaned


def clean_product_id(series: pd.Series) -> pd.Series:
    """
    將商品編號統一轉成文字。

    例如：
    330290.0 -> 330290
    """
    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .replace("", pd.NA)
    )

    return cleaned


def load_sales_data(file_path: Path) -> pd.DataFrame:
    """
    讀取銷量 Excel 的第一張工作表。
    """

    if not file_path.exists():
        raise FileNotFoundError(f"找不到銷量檔案：{file_path}")

    try:
        dataframe = pd.read_excel(
            file_path,
            sheet_name=0,
            engine="openpyxl",
        )

    except PermissionError as error:
        raise PermissionError(
            "無法讀取銷量檔案，請先關閉 Excel。"
        ) from error

    return dataframe


def clean_sales_data(
    raw_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    清理銷量資料，但不刪除任何資料列。
    """

    dataframe = raw_dataframe.copy()

    # 保留 Excel 原始列號。
    # Excel 第一列通常是標題，因此資料第一列是第 2 列。
    dataframe.insert(
        0,
        "source_row_number",
        range(2, len(dataframe) + 2),
    )

    # 統一欄位名稱
    dataframe = rename_columns(dataframe)

    # 只保留需要的主要欄位及原始列號
    dataframe = dataframe[
        [
            "source_row_number",
            "sale_date",
            "product_id",
            "product_name",
            "quantity",
        ]
    ].copy()

    # 保存原始內容，方便日後追查
    dataframe["original_sale_date"] = dataframe["sale_date"]
    dataframe["original_product_id"] = dataframe["product_id"]
    dataframe["original_quantity"] = dataframe["quantity"]

    # 清理日期
    dataframe["sale_date"] = pd.to_datetime(
        dataframe["sale_date"],
        errors="coerce",
    )

    # 清理商品編號
    dataframe["product_id"] = clean_product_id(
        dataframe["product_id"]
    )

    # 清理商品名稱
    dataframe["product_name"] = clean_text_column(
        dataframe["product_name"]
    )

    # 清理銷量
    dataframe["quantity"] = pd.to_numeric(
        dataframe["quantity"],
        errors="coerce",
    )

    # 標記必要欄位缺值
    dataframe["missing_sale_date"] = dataframe[
        "sale_date"
    ].isna()

    dataframe["missing_product_id"] = dataframe[
        "product_id"
    ].isna()

    dataframe["missing_product_name"] = dataframe[
        "product_name"
    ].isna()

    dataframe["missing_quantity"] = dataframe[
        "quantity"
    ].isna()

    # 標記負數或零銷量
    dataframe["negative_quantity"] = (
        dataframe["quantity"].notna()
        & (dataframe["quantity"] < 0)
    )

    dataframe["zero_quantity"] = (
        dataframe["quantity"].notna()
        & (dataframe["quantity"] == 0)
    )

    # 完全重複：
    # 日期、商品編號、商品名稱及銷量全部相同
    dataframe["exact_duplicate"] = dataframe.duplicated(
        subset=[
            "sale_date",
            "product_id",
            "product_name",
            "quantity",
        ],
        keep=False,
    )

    # 同一天、同一商品編號出現多筆資料
    dataframe["same_day_product_multiple"] = dataframe.duplicated(
        subset=[
            "sale_date",
            "product_id",
        ],
        keep=False,
    )

    # 建立問題總旗標
    issue_columns = [
        "missing_sale_date",
        "missing_product_id",
        "missing_product_name",
        "missing_quantity",
        "negative_quantity",
        "exact_duplicate",
        "same_day_product_multiple",
    ]

    dataframe["has_quality_issue"] = dataframe[
        issue_columns
    ].any(axis=1)

    # 建立文字問題說明
    dataframe["quality_issue_description"] = dataframe.apply(
        build_issue_description,
        axis=1,
    )

    # 調整欄位順序
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

    dataframe = dataframe[ordered_columns]

    return dataframe


def build_issue_description(row: pd.Series) -> str:
    """
    將每一列的品質問題整理成容易閱讀的文字。
    """

    issues = []

    if row["missing_sale_date"]:
        issues.append("日期缺漏或格式無法辨識")

    if row["missing_product_id"]:
        issues.append("商品編號缺漏")

    if row["missing_product_name"]:
        issues.append("商品名稱缺漏")

    if row["missing_quantity"]:
        issues.append("銷量缺漏或格式無法辨識")

    if row["negative_quantity"]:
        issues.append("銷量為負數")

    if row["exact_duplicate"]:
        issues.append("完全重複資料")

    if row["same_day_product_multiple"]:
        issues.append("同日同商品出現多筆資料")

    return "；".join(issues)


def create_quality_summary(
    cleaned_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    建立資料品質問題摘要表。
    """

    summary_items = [
        {
            "issue_type": "總資料列數",
            "count": len(cleaned_dataframe),
        },
        {
            "issue_type": "有任一品質問題的資料列",
            "count": int(
                cleaned_dataframe["has_quality_issue"].sum()
            ),
        },
        {
            "issue_type": "日期缺漏或無法辨識",
            "count": int(
                cleaned_dataframe["missing_sale_date"].sum()
            ),
        },
        {
            "issue_type": "商品編號缺漏",
            "count": int(
                cleaned_dataframe["missing_product_id"].sum()
            ),
        },
        {
            "issue_type": "商品名稱缺漏",
            "count": int(
                cleaned_dataframe["missing_product_name"].sum()
            ),
        },
        {
            "issue_type": "銷量缺漏或無法辨識",
            "count": int(
                cleaned_dataframe["missing_quantity"].sum()
            ),
        },
        {
            "issue_type": "銷量為負數",
            "count": int(
                cleaned_dataframe["negative_quantity"].sum()
            ),
        },
        {
            "issue_type": "銷量為零",
            "count": int(
                cleaned_dataframe["zero_quantity"].sum()
            ),
        },
        {
            "issue_type": "完全重複資料列",
            "count": int(
                cleaned_dataframe["exact_duplicate"].sum()
            ),
        },
        {
            "issue_type": "同日同商品多筆資料列",
            "count": int(
                cleaned_dataframe[
                    "same_day_product_multiple"
                ].sum()
            ),
        },
    ]

    return pd.DataFrame(summary_items)


def save_results(
    cleaned_dataframe: pd.DataFrame,
    issues_dataframe: pd.DataFrame,
    summary_dataframe: pd.DataFrame,
) -> None:
    """
    將分析結果輸出至 data/processed。
    """

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cleaned_dataframe.to_csv(
        CLEANED_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    issues_dataframe.to_csv(
        ISSUES_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    summary_dataframe.to_csv(
        SUMMARY_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )


def print_summary(
    cleaned_dataframe: pd.DataFrame,
    summary_dataframe: pd.DataFrame,
) -> None:
    """
    在終端機顯示執行結果。
    """

    print("\n" + "=" * 80)
    print("銷量資料清理完成")
    print("=" * 80)

    print(f"原始檔案：{RAW_FILE_PATH}")
    print(f"總資料列數：{len(cleaned_dataframe)}")

    print("\n資料品質摘要：")
    print(summary_dataframe.to_string(index=False))

    print("\n前 5 筆清理結果：")
    display_columns = [
        "source_row_number",
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
        "quality_issue_description",
    ]

    print(
        cleaned_dataframe[display_columns]
        .head()
        .to_string(index=False)
    )

    print("\n輸出檔案：")
    print(f"1. {CLEANED_OUTPUT_PATH}")
    print(f"2. {ISSUES_OUTPUT_PATH}")
    print(f"3. {SUMMARY_OUTPUT_PATH}")


def main() -> None:
    """
    程式主要執行流程。
    """

    raw_dataframe = load_sales_data(RAW_FILE_PATH)

    cleaned_dataframe = clean_sales_data(
        raw_dataframe
    )

    issues_dataframe = cleaned_dataframe[
        cleaned_dataframe["has_quality_issue"]
    ].copy()

    summary_dataframe = create_quality_summary(
        cleaned_dataframe
    )

    save_results(
        cleaned_dataframe,
        issues_dataframe,
        summary_dataframe,
    )

    print_summary(
        cleaned_dataframe,
        summary_dataframe,
    )


if __name__ == "__main__":
    main()