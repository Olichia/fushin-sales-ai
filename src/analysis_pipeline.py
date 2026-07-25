from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# =========================================================
# 完整分析設定
# =========================================================

@dataclass(frozen=True)
class AnalysisSettings:
    """
    完整分析使用的設定。

    baseline_days：
        活動開始前要觀察幾天。

    post_days：
        活動結束後要觀察幾天。

    fill_missing_dates_with_zero：
        沒有銷量紀錄的日期是否視為零銷量。

    high_uplift_threshold：
        高成效活動的提升率門檻。

    low_uplift_threshold：
        低成效活動的提升率門檻。

    minimum_campaign_sales：
        納入高成效判斷的最低活動總銷量。

    only_complete_periods：
        策略報告是否只使用觀察期間完整的活動。
    """

    baseline_days: int = 7
    post_days: int = 7
    fill_missing_dates_with_zero: bool = True

    high_uplift_threshold: float = 0.20
    low_uplift_threshold: float = 0.0
    minimum_campaign_sales: float = 1.0
    only_complete_periods: bool = True


# =========================================================
# 完整分析結果
# =========================================================

@dataclass
class AnalysisPipelineResult:
    """
    執行完整分析後回傳的所有結果。
    """

    integrated_dataframe: pd.DataFrame
    integration_issues_dataframe: pd.DataFrame
    performance_dataframe: pd.DataFrame
    strategy_dataframe: pd.DataFrame
    strategy_report_text: str


# =========================================================
# 共用文字及商品編號整理
# =========================================================

def normalize_product_id(
    series: pd.Series,
) -> pd.Series:
    """
    將商品編號統一轉成乾淨文字。

    例如：
    330290.0 -> 330290
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


def combine_unique_text(
    values: pd.Series,
) -> str | None:
    """
    合併同一群組中不重複且非空白的文字。
    """

    results: list[str] = []

    for value in values.dropna():
        text = str(value).strip()

        if text and text not in results:
            results.append(text)

    if not results:
        return None

    return "、".join(results)


def safe_percentage_change(
    current_value: float,
    baseline_value: float,
) -> float | None:
    """
    安全計算變化率。

    基準為零或空值時，回傳 None。
    """

    if pd.isna(baseline_value):
        return None

    if baseline_value == 0:
        return None

    return (
        current_value - baseline_value
    ) / baseline_value