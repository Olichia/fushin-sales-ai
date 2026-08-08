from __future__ import annotations

import pandas as pd


# =========================================================
# 共用常數
# =========================================================

MINIMUM_DAYS_FOR_CONFIDENCE = 2

CATEGORY_COLOR_MAP = {
    "單一活動正向": "#009B73",
    "重疊活動": "#F45B1B",
    "負增益": "#C62828",
}


# =========================================================
# 活動單位總覽顯示層整理
#
# 這裡的邏輯與「活動洞察」頁面完全同源，供分析總覽／策略中心
# 共用，避免不同頁面各自實作出不一致的分類或風險判斷。
# =========================================================

def prepare_unit_overview_for_display(
    unit_overview_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """數值型別整理，並衍生 color_category／discount_rate 欄位。"""

    unit_overview = unit_overview_dataframe.copy()

    numeric_columns = [
        "unit_avg_sales",
        "baseline_avg_sales",
        "baseline_price",
        "unit_avg_price",
        "sales_increment",
        "volume_effect_per_day",
        "price_effect_per_day",
        "net_revenue_effect_per_day",
        "net_revenue_effect_total",
        "days",
        "month",
    ]

    for column in numeric_columns:
        if column in unit_overview.columns:
            unit_overview[column] = pd.to_numeric(
                unit_overview[column], errors="coerce"
            )

    unit_overview["product_id"] = (
        unit_overview["product_id"].astype(str).str.strip()
    )

    unit_overview["corresponding_activities_label"] = (
        unit_overview["corresponding_activities_label"]
        .fillna("")
        .astype(str)
    )

    def classify_color_category(row: pd.Series) -> str:
        # 「不可分割活動組合」（母子活動群組已被明確定義）與
        # 「多活動疊加,待瀑布法檢驗」（單純疊加多個標籤，還
        # 沒確定能不能拆）都代表這個單位不是單一活動，沿用
        # 同一個「重疊活動」風險色。
        if row.get("classification") in {
            "多活動疊加,待瀑布法檢驗",
            "不可分割活動組合",
        }:
            return "重疊活動"

        net_effect = row.get("net_revenue_effect_per_day")

        if pd.notna(net_effect) and net_effect < 0:
            return "負增益"

        return "單一活動正向"

    unit_overview["color_category"] = unit_overview.apply(
        classify_color_category, axis=1
    )

    unit_overview["discount_rate"] = (
        1
        - unit_overview["unit_avg_price"]
        / unit_overview["baseline_price"]
    )
    unit_overview.loc[
        unit_overview["baseline_price"].isna()
        | (unit_overview["baseline_price"] == 0),
        "discount_rate",
    ] = pd.NA

    return unit_overview


def compute_risk_mask(unit_overview_dataframe: pd.DataFrame) -> pd.Series:
    """降價效應為負，且絕對值大於量增效應＝毛利侵蝕風險。"""

    return (
        unit_overview_dataframe["price_effect_per_day"] < 0
    ) & (
        unit_overview_dataframe["price_effect_per_day"].abs()
        > unit_overview_dataframe["volume_effect_per_day"].abs()
    )


def compute_confidence_label(
    unit_overview_dataframe: pd.DataFrame,
) -> pd.Series:
    """
    涵蓋天數過短，或用了樣本量／代理牌價提示，
    視為資料信心較低。
    """

    low_confidence = (
        (
            unit_overview_dataframe["days"]
            < MINIMUM_DAYS_FOR_CONFIDENCE
        )
        | unit_overview_dataframe["sample_size_note"]
        .fillna("")
        .astype(str)
        .str.len()
        .gt(0)
        | unit_overview_dataframe["proxy_price_note"]
        .fillna("")
        .astype(str)
        .str.len()
        .gt(0)
    )

    return low_confidence.map({True: "較低", False: "較高"})


def compute_actual_revenue_total(
    unit_overview_dataframe: pd.DataFrame,
) -> pd.Series:
    """該活動單位「實際銷量×實際售價」的總營收（非淨增益）。"""

    return (
        unit_overview_dataframe["unit_avg_sales"]
        * unit_overview_dataframe["days"]
        * unit_overview_dataframe["unit_avg_price"]
    )


def compute_strategy_category(
    unit_overview_dataframe: pd.DataFrame,
) -> pd.Series:
    """
    淨增益/日為負＝建議檢討（維持既有規則，不受這輪調整
    影響）；非負值時，達全體活動單位中位數以上＝建議延續，
    未達中位數＝持續觀察（中位數以全部活動單位計算，
    不分正負與可否拆分）。
    """

    net_effect = unit_overview_dataframe["net_revenue_effect_per_day"]
    median_net_effect = net_effect.median()

    category = pd.Series(
        "持續觀察", index=unit_overview_dataframe.index
    )
    category[net_effect >= median_net_effect] = "建議延續"
    category[net_effect < 0] = "建議檢討"

    return category
