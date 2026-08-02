from __future__ import annotations

from pathlib import Path
import tempfile

import pandas as pd


from src.clean_activities import (
    create_quality_summary as create_main_activity_summary,
    explode_promotion_periods,
    load_activity_sheet,
    prepare_activity_dataframe,
)

from src.clean_other_activities import (
    create_summary as create_other_activity_summary,
    parse_april_vacuum_coupons,
    parse_base_promotion_sheet,
    parse_brand_day_summary,
    parse_march_product_gifts,
    parse_package_sheet,
    parse_schedule_sheet,
)


# =========================================================
# 主商品活動標準化
# =========================================================

def standardize_main_activities(
    march_path: Path,
    april_path: Path,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    整理 3 月與 4 月的主要商品活動表。

    回傳：
    1. 商品活動標準化資料
    2. 主活動問題資料
    3. 主活動品質摘要
    """

    march_raw = load_activity_sheet(
        march_path,
        source_month=3,
    )

    april_raw = load_activity_sheet(
        april_path,
        source_month=4,
    )

    march_prepared = prepare_activity_dataframe(
        march_raw
    )

    april_prepared = prepare_activity_dataframe(
        april_raw
    )

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
        create_main_activity_summary(
            prepared_dataframe,
            activity_dataframe,
            issues_dataframe,
        )
    )

    return (
        activity_dataframe,
        issues_dataframe,
        summary_dataframe,
    )


# =========================================================
# 其他活動標準化
# =========================================================

def standardize_other_activities(
    march_path: Path,
    april_path: Path,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    整理活動日曆及其他優惠內容。

    包括：
    - 3 月與 4 月檔期
    - 鋪底活動
    - 指定商品贈品
    - 吸塵器折價券
    - 品牌日及品牌週
    - 包套活動

    回傳：
    1. 活動日曆
    2. 優惠內容
    3. 問題資料
    4. 品質摘要
    """

    calendar_records: list[dict] = []
    benefit_records: list[dict] = []
    issue_records: list[dict] = []

    march_sheet_names = set(
        pd.ExcelFile(march_path).sheet_names
    )
    april_sheet_names = set(
        pd.ExcelFile(april_path).sheet_names
    )

    # -----------------------------------------------------
    # 3 月檔期
    # -----------------------------------------------------

    records, issues = parse_schedule_sheet(
        march_path,
        source_month=3,
    )

    calendar_records.extend(records)
    issue_records.extend(issues)

    # -----------------------------------------------------
    # 4 月檔期
    # -----------------------------------------------------

    records, issues = parse_schedule_sheet(
        april_path,
        source_month=4,
    )

    calendar_records.extend(records)
    issue_records.extend(issues)

    # -----------------------------------------------------
    # 3 月鋪底
    # -----------------------------------------------------

    (
        records,
        benefits,
        issues,
    ) = parse_base_promotion_sheet(
        march_path,
        "三月鋪底",
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # -----------------------------------------------------
    # 4 月鋪底
    # -----------------------------------------------------

    (
        records,
        benefits,
        issues,
    ) = parse_base_promotion_sheet(
        april_path,
        "四月鋪底",
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # -----------------------------------------------------
    # 3 月指定商品贈品
    # -----------------------------------------------------

    if "0308-0312滿額贈即享券" in march_sheet_names:
        benefits, issues = (
            parse_march_product_gifts(
                march_path
            )
        )

        benefit_records.extend(benefits)
        issue_records.extend(issues)

    # -----------------------------------------------------
    # 4 月吸塵器折價券
    # -----------------------------------------------------

    if "超品日吸塵器折價券" in april_sheet_names:
        benefits, issues = (
            parse_april_vacuum_coupons(
                april_path
            )
        )

        benefit_records.extend(benefits)
        issue_records.extend(issues)

    # -----------------------------------------------------
    # 品牌日及品牌週
    # -----------------------------------------------------

    if "品牌日+品牌週" in april_sheet_names:
        (
            records,
            benefits,
            issues,
        ) = parse_brand_day_summary(
            april_path
        )

        calendar_records.extend(records)
        benefit_records.extend(benefits)
        issue_records.extend(issues)

    # -----------------------------------------------------
    # 包套活動
    # -----------------------------------------------------

    package_sheet_names = {
        "包套活動",
        "包套",
    }

    if package_sheet_names & april_sheet_names:
        (
            records,
            benefits,
            issues,
        ) = parse_package_sheet(
            april_path
        )

        calendar_records.extend(records)
        benefit_records.extend(benefits)
        issue_records.extend(issues)

    # -----------------------------------------------------
    # 建立 DataFrame
    # -----------------------------------------------------

    calendar_dataframe = pd.DataFrame(
        calendar_records
    )

    benefits_dataframe = pd.DataFrame(
        benefit_records
    )

    issue_columns = [
        "source_file",
        "source_sheet",
        "source_row_number",
        "issue_type",
        "problem_text",
    ]

    issues_dataframe = pd.DataFrame(
        issue_records,
        columns=issue_columns,
    )

    # -----------------------------------------------------
    # 排序
    # -----------------------------------------------------

    if not calendar_dataframe.empty:
        calendar_dataframe = (
            calendar_dataframe
            .sort_values(
                by=[
                    "campaign_start_date",
                    "source_file",
                    "source_row_number",
                ],
                na_position="last",
            )
            .reset_index(
                drop=True
            )
        )

    if not benefits_dataframe.empty:
        benefits_dataframe = (
            benefits_dataframe
            .sort_values(
                by=[
                    "benefit_start_date",
                    "source_file",
                    "source_sheet",
                    "source_row_number",
                ],
                na_position="last",
            )
            .reset_index(
                drop=True
            )
        )

    summary_dataframe = (
        create_other_activity_summary(
            calendar_dataframe,
            benefits_dataframe,
            issues_dataframe,
        )
    )

    return (
        calendar_dataframe,
        benefits_dataframe,
        issues_dataframe,
        summary_dataframe,
    )


# =========================================================
# 合併主活動與其他活動問題
# =========================================================

def combine_activity_issues(
    main_issues_dataframe: pd.DataFrame,
    other_issues_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    合併兩套活動清理流程產生的問題資料。

    主活動資料有時不包含 problem_text，
    因此先補上欄位再合併。
    """

    main_issues_for_merge = (
        main_issues_dataframe.copy()
    )

    other_issues_for_merge = (
        other_issues_dataframe.copy()
    )

    if (
        not main_issues_for_merge.empty
        and "problem_text"
        not in main_issues_for_merge.columns
    ):
        main_issues_for_merge[
            "problem_text"
        ] = pd.NA

    return pd.concat(
        [
            main_issues_for_merge,
            other_issues_for_merge,
        ],
        ignore_index=True,
        sort=False,
    )


# =========================================================
# 一次執行完整活動資料處理
# =========================================================

def process_activity_files(
    march_file_bytes: bytes,
    april_file_bytes: bytes,
) -> dict[str, pd.DataFrame]:
    """
    將已上傳的 3 月與 4 月 Excel bytes
    寫入暫存檔並執行所有活動標準化。

    回傳格式：

    {
        "activity_standardized_dataframe": ...,
        "activity_calendar_dataframe": ...,
        "promotion_benefits_dataframe": ...,
        "activity_issues_dataframe": ...,
        "main_activity_summary_dataframe": ...,
        "other_activity_summary_dataframe": ...,
    }
    """

    if not march_file_bytes:
        raise ValueError(
            "3 月活動檔案內容不存在。"
        )

    if not april_file_bytes:
        raise ValueError(
            "4 月活動檔案內容不存在。"
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(
            temp_dir
        )

        march_path = (
            temp_path
            / "3月品牌活動_通路.xlsx"
        )

        april_path = (
            temp_path
            / "4月品牌活動_通路.xlsx"
        )

        march_path.write_bytes(
            march_file_bytes
        )

        april_path.write_bytes(
            april_file_bytes
        )

        (
            main_activity_dataframe,
            main_activity_issues_dataframe,
            main_activity_summary_dataframe,
        ) = standardize_main_activities(
            march_path,
            april_path,
        )

        (
            calendar_dataframe,
            benefits_dataframe,
            other_issues_dataframe,
            other_summary_dataframe,
        ) = standardize_other_activities(
            march_path,
            april_path,
        )

    activity_issues_dataframe = (
        combine_activity_issues(
            main_issues_dataframe=(
                main_activity_issues_dataframe
            ),
            other_issues_dataframe=(
                other_issues_dataframe
            ),
        )
    )

    return {
        "activity_standardized_dataframe": (
            main_activity_dataframe
        ),
        "activity_calendar_dataframe": (
            calendar_dataframe
        ),
        "promotion_benefits_dataframe": (
            benefits_dataframe
        ),
        "activity_issues_dataframe": (
            activity_issues_dataframe
        ),
        "main_activity_summary_dataframe": (
            main_activity_summary_dataframe
        ),
        "other_activity_summary_dataframe": (
            other_summary_dataframe
        ),
    }


# =========================================================
# 活動結果摘要
# =========================================================

def create_activity_data_summary(
    activity_standardized_dataframe: pd.DataFrame,
    activity_calendar_dataframe: pd.DataFrame | None,
    promotion_benefits_dataframe: pd.DataFrame | None,
    activity_issues_dataframe: pd.DataFrame | None,
) -> dict[str, int]:
    """
    建立活動資料最終確認區使用的摘要。
    """

    return {
        "main_activity_rows": len(
            activity_standardized_dataframe
        ),
        "calendar_rows": (
            len(activity_calendar_dataframe)
            if activity_calendar_dataframe is not None
            else 0
        ),
        "benefit_rows": (
            len(promotion_benefits_dataframe)
            if promotion_benefits_dataframe is not None
            else 0
        ),
        "issue_rows": (
            len(activity_issues_dataframe)
            if activity_issues_dataframe is not None
            else 0
        ),
    }
