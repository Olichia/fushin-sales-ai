from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd


# Pandas 3 預設會把一般文字推斷成 PyArrow 字串。本專案在 macOS 的
# Streamlit 重跑執行緒中曾於 Arrow 原生層發生 segmentation fault；分析流程
# 不需要 Arrow 字串的效能，因此固定採用穩定的 Python object/string 後端。
pd.set_option("future.infer_string", False)
pd.set_option("mode.string_storage", "python")


# =========================================================
# 完整分析設定
# =========================================================

@dataclass(frozen=True)
class AnalysisSettings:
    """完整分析使用的參數設定。"""

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
    """執行完整分析後回傳的所有結果。"""

    integrated_dataframe: pd.DataFrame
    integration_issues_dataframe: pd.DataFrame
    performance_dataframe: pd.DataFrame
    strategy_dataframe: pd.DataFrame
    strategy_report_text: str


# =========================================================
# 共用工具
# =========================================================

def normalize_product_id(series: pd.Series) -> pd.Series:
    """將商品編號轉成一致且乾淨的文字格式。"""

    normalized_values: list[object] = []

    # 不使用 pandas/pyarrow 的字串轉型；目前 macOS 的 pyarrow 原生層在
    # Streamlit 重跑時偶發 segmentation fault，會讓整個網站程序直接終止。
    for value in series:
        if pd.isna(value):
            normalized_values.append(pd.NA)
            continue

        text = re.sub(r"\.0$", "", str(value).strip())
        normalized_values.append(text if text else pd.NA)

    return pd.Series(
        normalized_values,
        index=series.index,
        dtype=object,
        name=series.name,
    )


def normalize_text(series: pd.Series) -> pd.Series:
    """以 Python object 字串整理一般文字欄位，避開 Arrow 原生轉型。"""

    normalized_values: list[object] = []

    for value in series:
        if pd.isna(value):
            normalized_values.append(pd.NA)
            continue

        text = str(value).strip()
        normalized_values.append(text if text else pd.NA)

    return pd.Series(
        normalized_values,
        index=series.index,
        dtype=object,
        name=series.name,
    )


def coerce_arrow_strings_to_object(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """把既有 pickle／上傳資料中的 Arrow 字串安全轉成 object。"""

    converted = dataframe.copy()

    # Pandas 3 也可能把 DataFrame 欄名存成 Arrow 字串 Index；即使欄位內容
    # 已轉型，dropna(subset=...) 的欄位選取仍會進入 pyarrow.take。
    converted.columns = pd.Index(
        [str(column) for column in converted.columns],
        dtype=object,
    )

    if getattr(converted.index.dtype, "storage", None) == "pyarrow":
        converted.index = pd.Index(
            [value for value in converted.index],
            dtype=object,
            name=converted.index.name,
        )

    for column in converted.columns:
        dtype = converted[column].dtype

        if (
            isinstance(dtype, pd.StringDtype)
            and getattr(dtype, "storage", None) == "pyarrow"
        ):
            converted[column] = normalize_text(converted[column])

    return converted


def combine_unique_text(values: pd.Series) -> str | None:
    """合併同一群組中不重複且非空白的文字。"""

    results: list[str] = []

    for value in values.dropna():
        text = str(value).strip()

        if text and text not in results:
            results.append(text)

    if not results:
        return None

    return "、".join(results)


def safe_unique_text_list(values: pd.Series) -> list[str]:
    """以純 Python 取得不重複文字，避開 Arrow unique 原生崩潰。"""

    results: list[str] = []

    for value in values:
        if pd.isna(value):
            continue

        text = str(value).strip()

        if text and text not in results:
            results.append(text)

    return results


def safe_percentage_change(
    current_value: float,
    baseline_value: float,
) -> float | None:
    """安全計算變化率；基準為零或空值時回傳 None。"""

    if pd.isna(baseline_value):
        return None

    if baseline_value == 0:
        return None

    return (current_value - baseline_value) / baseline_value


def format_percentage(value: object) -> str:
    """將數字格式化為百分比文字。"""

    if pd.isna(value):
        return "無法計算"

    return f"{float(value):.1%}"


def activity_label(row: pd.Series) -> str:
    """建立策略報告使用的商品活動標籤。"""

    product_id = str(row.get("product_id", "未提供編號"))

    product_name = row.get(
        "product_name",
        "未提供名稱",
    )

    if pd.isna(product_name):
        product_name = "未提供名稱"

    start_date = row.get("activity_start_date")
    end_date = row.get("activity_end_date")

    start_text = (
        start_date.strftime("%Y-%m-%d")
        if pd.notna(start_date)
        else "-"
    )

    end_text = (
        end_date.strftime("%Y-%m-%d")
        if pd.notna(end_date)
        else "-"
    )

    return (
        f"{product_id}｜{product_name}"
        f"｜{start_text}～{end_text}"
    )


def has_text(value: object) -> bool:
    """判斷欄位是否包含可供策略判讀的文字。"""

    return pd.notna(value) and bool(str(value).strip())


def unique_text_labels(value: object) -> list[str]:
    """拆解 Excel 儲存格中的活動／優惠名稱並保留原始順序。"""

    if not has_text(value):
        return []

    labels: list[str] = []

    for item in re.split(r"[、,，;；\n]+", str(value)):
        label = item.strip()

        if label and label not in labels:
            labels.append(label)

    return labels


def activity_excel_context(row: pd.Series) -> dict[str, object]:
    """整理活動 Excel 實際記載的主活動、同期檔期與優惠。"""

    activity_tags = unique_text_labels(row.get("activity_tag"))
    campaigns = unique_text_labels(
        row.get("overlapping_campaigns")
    )
    benefits = unique_text_labels(
        row.get("overlapping_benefits")
    )

    context_parts: list[str] = []

    if activity_tags:
        context_parts.append(
            "主活動：" + "、".join(activity_tags[:3])
        )

    if campaigns:
        context_parts.append(
            "同期檔期：" + "、".join(campaigns[:4])
        )

    if benefits:
        context_parts.append(
            "同期優惠：" + "、".join(benefits[:4])
        )

    return {
        "activity_tags": activity_tags,
        "campaigns": campaigns,
        "benefits": benefits,
        "label": "；".join(context_parts),
        "has_excel_context": bool(context_parts),
        "has_overlap": bool(campaigns or benefits),
    }


def infer_campaign_period(row: pd.Series) -> str:
    """先採用 Excel 實際活動內容，無內容時才依日期推測。"""

    excel_context = activity_excel_context(row)

    if excel_context["has_excel_context"]:
        return str(excel_context["label"])

    text_parts = [
        row.get("activity_gift"),
    ]

    campaign_text = " ".join(
        str(value)
        for value in text_parts
        if has_text(value)
    ).lower()

    keyword_periods = [
        (("春節", "過年", "年貨"), "農曆春節／年貨檔"),
        (("女王節", "女神節", "38節", "3.8"), "3.8 女王節檔"),
        (("白色情人",), "白色情人節檔"),
        (("母親節",), "母親節檔"),
        (("520",), "520 檔"),
        (("618", "年中慶"), "618／年中慶檔"),
        (("父親節", "88節"), "父親節檔"),
        (("開學",), "開學檔"),
        (("99購物", "9.9", "九九購物"), "9.9 購物節檔"),
        (("雙十", "國慶"), "雙十／國慶檔"),
        (("1111", "11.11", "雙11", "雙 11"), "雙 11 檔"),
        (("black friday", "黑五"), "黑色星期五檔"),
        (("1212", "12.12", "雙12", "雙 12"), "雙 12 檔"),
        (("聖誕", "christmas"), "聖誕檔"),
        (("年終", "跨年"), "年終／跨年檔"),
    ]

    for keywords, period_name in keyword_periods:
        if any(
            keyword in campaign_text
            for keyword in keywords
        ):
            return period_name

    start_date = row.get("activity_start_date")
    end_date = row.get("activity_end_date")

    if pd.isna(start_date) or pd.isna(end_date):
        return "檔期資料不足"

    activity_dates = pd.date_range(
        pd.Timestamp(start_date).normalize(),
        pd.Timestamp(end_date).normalize(),
        freq="D",
    )

    month_days = {
        (date.month, date.day)
        for date in activity_dates
    }

    date_windows = [
        (3, range(1, 9), "3.8 女王節檔"),
        (3, range(12, 18), "白色情人節／三月中旬檔"),
        (5, range(1, 13), "母親節前導檔"),
        (5, range(15, 21), "520 檔"),
        (6, range(12, 21), "618／年中慶檔"),
        (8, range(1, 9), "父親節檔"),
        (9, range(1, 11), "9.9 購物節檔"),
        (10, range(7, 11), "雙十／國慶檔"),
        (11, range(1, 12), "雙 11 檔"),
        (12, range(1, 13), "雙 12 檔"),
        (12, range(20, 26), "聖誕檔"),
        (12, range(26, 32), "年終／跨年檔"),
    ]

    for month, days, period_name in date_windows:
        if any(
            (month, day) in month_days
            for day in days
        ):
            return period_name

    if any(date.day >= 25 for date in activity_dates):
        return "月底／發薪後檔"

    if any(date.day <= 5 for date in activity_dates):
        return "月初檔"

    return "日期推測：一般／品牌自訂檔"


def format_date_range(
    start_value: object,
    end_value: object,
) -> str:
    """將觀察期間格式化為易讀日期範圍。"""

    start_date = pd.to_datetime(start_value, errors="coerce")
    end_date = pd.to_datetime(end_value, errors="coerce")

    if pd.isna(start_date) or pd.isna(end_date):
        return "日期未提供"

    return (
        f"{start_date.strftime('%Y-%m-%d')}～"
        f"{end_date.strftime('%Y-%m-%d')}"
    )


def build_missing_data_note(row: pd.Series) -> str:
    """逐段說明活動無法正式分類時缺少的資料。"""

    gaps: list[str] = []

    period_definitions = [
        (
            "baseline_complete",
            "活動前基準",
            "baseline_start_date",
            "baseline_end_date",
        ),
        (
            "campaign_complete",
            "活動期間",
            "activity_start_date",
            "activity_end_date",
        ),
        (
            "post_complete",
            "活動後觀察",
            "post_start_date",
            "post_end_date",
        ),
    ]

    for flag, name, start_column, end_column in period_definitions:
        complete_flag = (
            bool(row.get(flag))
            if flag in row.index
            else bool(row.get("all_periods_complete", False))
        )

        if not complete_flag:
            gaps.append(
                f"{name}資料未完整覆蓋（需要 "
                f"{format_date_range(row.get(start_column), row.get(end_column))}）"
            )

    baseline_average = row.get(
        "baseline_average_daily_sales"
    )

    if pd.isna(baseline_average):
        gaps.append("活動前日均銷量缺漏，無法計算提升率")
    elif float(baseline_average) == 0:
        gaps.append("活動前日均銷量為 0，提升率無法作為分類依據")
    elif pd.isna(row.get("uplift_rate")):
        gaps.append("提升率無法計算")

    if not gaps:
        return "資料完整，可進行正式策略分類。"

    return "；".join(gaps) + "。"


def data_completeness_label(row: pd.Series) -> str:
    """將日期覆蓋狀態改成不帶主觀判斷的完整度名稱。"""

    if bool(row.get("all_periods_complete", False)):
        return "完整（活動前、中、後皆齊）"

    if bool(row.get("campaign_complete", False)):
        return "部分（活動期完整，前或後缺漏）"

    return "不足（活動期本身未完整）"


def build_product_history_context(
    row: pd.Series,
    comparable_dataframe: pd.DataFrame,
    include_current_comparison: bool = True,
) -> str:
    """將單筆活動與同商品其他可比活動的歷史表現比較。"""

    product_id = str(row.get("product_id", ""))
    history = comparable_dataframe[
        normalize_product_id(comparable_dataframe["product_id"])
        == product_id
    ].copy()

    current_start = pd.to_datetime(
        row.get("activity_start_date"),
        errors="coerce",
    )
    current_end = pd.to_datetime(
        row.get("activity_end_date"),
        errors="coerce",
    )

    if not history.empty:
        same_row_mask = (
            pd.to_datetime(
                history["activity_start_date"],
                errors="coerce",
            ).eq(current_start)
            & pd.to_datetime(
                history["activity_end_date"],
                errors="coerce",
            ).eq(current_end)
        )
        history = history[~same_row_mask].copy()

    history = history.dropna(subset=["uplift_rate"])

    if history.empty:
        return "同商品目前沒有其他資料完整的活動可比較"

    median_uplift = history["uplift_rate"].median()
    current_uplift = row.get("uplift_rate")

    if not include_current_comparison:
        return (
            f"同商品另有 {len(history)} 筆資料完整的可比活動，"
            f"提升率中位數 {format_percentage(median_uplift)}"
        )

    if pd.isna(current_uplift) or pd.isna(median_uplift):
        comparison = "本次提升率暫時無法與歷史中位數比較"
    else:
        difference = float(current_uplift) - float(median_uplift)
        direction = "高" if difference >= 0 else "低"
        comparison = (
            f"本次較歷史中位數{direction} "
            f"{abs(difference):.1%} 個百分點"
        )

    return (
        f"同商品另有 {len(history)} 筆資料完整的可比活動，"
        f"提升率中位數 {format_percentage(median_uplift)}，"
        f"{comparison}"
    )


def build_mechanism_test_plan(row: pd.Series) -> str:
    """依 Excel 活動機制提出下一檔可執行的單一變因測試。"""

    mechanism_text = " ".join(
        str(row.get(column))
        for column in ["activity_tag", "activity_gift"]
        if has_text(row.get(column))
    )

    if any(keyword in mechanism_text for keyword in ["限搶", "限時"]):
        return (
            "保留商品與價格，僅測試一個限搶時段或限量門檻，"
            "逐時追蹤曝光、下單與售罄時間"
        )

    if any(keyword in mechanism_text for keyword in ["加碼", "贈", "贈品"]):
        return (
            "固定曝光與價格，只測試贈品內容或滿額門檻其中一項，"
            "追蹤贈品兌換率、轉換率與每筆贈品成本"
        )

    if any(keyword in mechanism_text for keyword in ["包套", "組合"]):
        return (
            "固定主商品價格，只調整一個組合品或組合價，"
            "追蹤組合滲透率、客單價與連帶購買率"
        )

    if any(keyword in mechanism_text for keyword in ["折", "券", "降價"]):
        return (
            "固定流量來源，只測試一個折扣或券門檻，"
            "同時追蹤實付價、轉換率與增量毛利"
        )

    return (
        "維持商品、價格與渠道不變，每次只調整曝光、活動天數"
        "或優惠門檻其中一項，避免多變因造成無法歸因"
    )


def calculate_strategy_metrics(
    row: pd.Series,
) -> dict[str, object]:
    """計算策略表可直接使用的代營運延伸指標。"""

    baseline_average = row.get(
        "baseline_average_daily_sales"
    )
    campaign_average = row.get(
        "campaign_average_daily_sales"
    )
    post_average = row.get(
        "post_average_daily_sales"
    )
    campaign_total = row.get("campaign_total_sales")
    activity_days = row.get("activity_days")
    campaign_price = row.get("campaign_price")

    incremental_sales: object = pd.NA
    incremental_revenue: object = pd.NA
    daily_revenue: object = pd.NA
    post_retention_rate: object = pd.NA
    post_vs_baseline_rate: object = pd.NA

    if (
        pd.notna(campaign_total)
        and pd.notna(baseline_average)
        and pd.notna(activity_days)
    ):
        incremental_sales = float(campaign_total) - (
            float(baseline_average) * float(activity_days)
        )

    if (
        pd.notna(incremental_sales)
        and pd.notna(campaign_price)
    ):
        incremental_revenue = (
            float(incremental_sales)
            * float(campaign_price)
        )

    if (
        pd.notna(row.get("estimated_revenue"))
        and pd.notna(activity_days)
        and float(activity_days) > 0
    ):
        daily_revenue = (
            float(row.get("estimated_revenue"))
            / float(activity_days)
        )

    if (
        pd.notna(post_average)
        and pd.notna(campaign_average)
        and float(campaign_average) > 0
    ):
        post_retention_rate = (
            float(post_average)
            / float(campaign_average)
        )

    if (
        pd.notna(post_average)
        and pd.notna(baseline_average)
        and float(baseline_average) > 0
    ):
        post_vs_baseline_rate = (
            float(post_average) - float(baseline_average)
        ) / float(baseline_average)

    return {
        "基準日均銷量": baseline_average,
        "活動日均銷量": campaign_average,
        "活動增量銷量": incremental_sales,
        "推估增量營收": incremental_revenue,
        "活動日均營收": daily_revenue,
        "活動後銷量延續率": post_retention_rate,
        "活動後較基準變化": post_vs_baseline_rate,
    }


def build_attribution_note(
    row: pd.Series,
    campaign_period: str,
    metrics: dict[str, object],
) -> str:
    """產生保守且可驗證的檔期與成效歸因說明。"""

    notes: list[str] = []

    excel_context = activity_excel_context(row)

    if excel_context["has_excel_context"]:
        notes.append(
            f"活動 Excel 顯示「{campaign_period}」；"
            "這些是本次歸因候選，不是只由日期猜測的檔期"
        )
    elif campaign_period not in {
        "日期推測：一般／品牌自訂檔",
        "檔期資料不足",
    }:
        notes.append(
            f"活動表沒有可用名稱，僅依日期推測可能接近"
            f"「{campaign_period}」，需人工確認"
        )
    else:
        notes.append(
            "活動表未提供可辨識的檔期名稱，較適合先視為"
            "品牌自有活動，並與相鄰無活動週比較"
        )

    overlapping_campaigns = row.get(
        "overlapping_campaigns"
    )
    overlapping_benefits = row.get(
        "overlapping_benefits"
    )

    overlap_labels = (
        unique_text_labels(overlapping_campaigns)
        + unique_text_labels(overlapping_benefits)
    )

    if overlap_labels:
        notes.append(
            "同期間另有「"
            + "；".join(overlap_labels)
            + "」，目前不能把增量完全歸因於單一活動"
        )

    post_vs_baseline_rate = metrics[
        "活動後較基準變化"
    ]

    if (
        pd.notna(post_vs_baseline_rate)
        and float(post_vs_baseline_rate) <= -0.10
    ):
        notes.append(
            "活動後日均銷量低於活動前基準至少 10%，"
            "可能有需求提前透支或活動結束後回落"
        )
    elif (
        pd.notna(post_vs_baseline_rate)
        and float(post_vs_baseline_rate) >= 0.10
    ):
        notes.append(
            "活動後日均銷量仍高於活動前基準至少 10%，"
            "可能存在曝光延續或新需求留存"
        )

    if not bool(row.get("all_periods_complete", False)):
        notes.append(
            "觀察期間尚未完整覆蓋，本次只能列出候選原因，"
            "不能進行正式成效歸因"
        )

    notes.append(
        "以上為關聯性推估，建議以未參與活動的相似商品、"
        "同期去年或區域／渠道對照組驗證"
    )

    return "；".join(notes) + "。"


def build_strategy_reason(
    row: pd.Series,
    category: str,
    settings: AnalysisSettings,
) -> str:
    """用實際數字說明單筆活動為何落入該策略分類。"""

    uplift = row.get("uplift_rate")
    campaign_sales = row.get("campaign_total_sales")

    uplift_text = format_percentage(uplift)
    sales_text = (
        f"{float(campaign_sales):,.0f}"
        if pd.notna(campaign_sales)
        else "無法計算"
    )

    if category == "資料不足／待補資料":
        return (
            "本活動先保留在清單，但不套用延續／優化／檢討規則。"
            + build_missing_data_note(row)
        )

    if category == "建議延續":
        rule_text = (
            f"提升率 ≥ {settings.high_uplift_threshold:.1%}，"
            f"且總銷量 ≥ {settings.minimum_campaign_sales:,.0f}"
        )
    elif category == "建議檢討":
        rule_text = (
            f"提升率 < {settings.low_uplift_threshold:.1%}"
        )
    else:
        rule_text = (
            f"{settings.low_uplift_threshold:.1%} ≤ 提升率 < "
            f"{settings.high_uplift_threshold:.1%}，或提升率已達"
            "高門檻但總銷量未達最低規模"
        )

    return (
        f"本活動提升率 {uplift_text}、總銷量 {sales_text}，"
        f"套用規則「{rule_text}」後歸為{category}。"
    )


def build_personalized_recommendation(
    row: pd.Series,
    category: str,
    campaign_period: str,
    metrics: dict[str, object],
    settings: AnalysisSettings,
    history_context: str,
) -> str:
    """依單筆活動表現、期間與風險產生差異化建議。"""

    product_name = row.get("product_name")
    product_text = (
        str(product_name).strip()
        if has_text(product_name)
        else str(row.get("product_id", "此商品"))
    )

    uplift_text = format_percentage(row.get("uplift_rate"))
    activity_days = row.get("activity_days")
    days_text = (
        f"{int(activity_days)} 天"
        if pd.notna(activity_days)
        else "目前活動期間"
    )
    campaign_sales = row.get("campaign_total_sales")
    sales_text = (
        f"{float(campaign_sales):,.0f} 件"
        if pd.notna(campaign_sales)
        else "銷量資料不足"
    )
    incremental_sales = metrics["活動增量銷量"]
    increment_text = (
        f"約 {float(incremental_sales):+,.0f} 件"
        if pd.notna(incremental_sales)
        else "暫時無法估算"
    )
    post_retention_rate = metrics["活動後銷量延續率"]
    overlap_exists = any(
        has_text(row.get(column))
        for column in [
            "overlapping_campaigns",
            "overlapping_benefits",
        ]
    )

    if category == "資料不足／待補資料":
        return (
            f"【績效診斷】「{product_text}」於 {campaign_period}執行"
            f" {days_text}，目前記錄到 {sales_text}；{history_context}。"
            "【建議決策】暫不判定延續、優化或檢討，也不採用未完整"
            "期間計算的提升率與增量。"
            f"【下一檔執行】{build_missing_data_note(row)}"
            "【驗證方式】由使用者選定活動前基準與活動後觀察天數，"
            "補齊相對應日期後重算，並保留活動 Excel 的檔期與優惠標記。"
        )

    opening = (
        f"「{product_text}」在 {campaign_period}的 {days_text}內"
        f"銷售 {sales_text}，日均銷量較活動前變動 {uplift_text}，"
        f"推估增量為 {increment_text}；{history_context}。"
    )

    actions: list[str] = []

    if category == "建議延續":
        if (
            pd.notna(post_retention_rate)
            and float(post_retention_rate) >= 0.80
        ):
            actions.append(
                "活動後仍保留至少八成活動期日均銷量，"
                "下次可先增加 10%～20% 曝光或備貨，"
                "並維持相同商品與優惠機制做單一變因驗證"
            )
        else:
            actions.append(
                "成效達延續門檻，但活動後回落較明顯；"
                "建議保留核心優惠，先以相同天數重跑，"
                "不要同時放大折扣與曝光"
            )

        if pd.notna(row.get("campaign_average_daily_sales")):
            suggested_stock = (
                float(row.get("campaign_average_daily_sales"))
                * (
                    float(activity_days)
                    if pd.notna(activity_days)
                    else 1.0
                )
                * 1.15
            )
            actions.append(
                f"若下次期間相同，可先以約 {suggested_stock:,.0f} 件"
                "作為含 15% 緩衝的備貨參考，再依實際庫存週轉修正"
            )

    elif category == "建議優化":
        if (
            pd.notna(row.get("uplift_rate"))
            and float(row.get("uplift_rate"))
            >= settings.high_uplift_threshold
        ):
            actions.append(
                "提升率已高但總銷量規模不足，優先判斷是否為"
                "曝光、庫存或受眾過窄，而不是直接加深折扣；"
                "下次可擴大一個流量入口並保留對照組"
            )
        elif (
            pd.notna(row.get("uplift_rate"))
            and float(row.get("uplift_rate")) >= 0
        ):
            actions.append(
                "活動帶來正向但有限的增幅，建議在優惠門檻、"
                "主圖／文案或曝光時段中只選一項做 A/B 測試，"
                "以提升率與增量營收共同決定是否放大"
            )
        else:
            actions.append(
                "目前接近低成效邊界，先縮小活動範圍，"
                "重新檢查價格帶、組合商品與目標客群匹配度"
            )

        if pd.notna(activity_days) and float(activity_days) >= 10:
            actions.append(
                "檔期偏長，應拆看前／中／後段日銷，"
                "確認是否因後段疲乏拉低平均成效"
            )
        elif pd.notna(activity_days) and float(activity_days) <= 3:
            actions.append(
                "檔期偏短，可先確認曝光是否充分，再測試延長"
                " 1～2 天，而非直接判定商品沒有潛力"
            )

    else:
        post_vs_baseline_rate = metrics[
            "活動後較基準變化"
        ]

        if (
            pd.notna(post_vs_baseline_rate)
            and float(post_vs_baseline_rate) > 0
        ):
            actions.append(
                "活動期表現低於基準、但活動後回升，可能是活動"
                "設計抑制轉換或消費者延後購買；應檢查價格、"
                "結帳門檻與贈品規則，不建議照原方案延續"
            )
        else:
            actions.append(
                "活動期未優於基準，先停止原樣複製，依序檢查"
                "缺貨、頁面流量、轉換率、實付價與競品價格；"
                "確認問題來源後再用較小預算重測"
            )

    mechanism_plan = build_mechanism_test_plan(row)
    decision_text = actions[0]
    execution_parts = actions[1:] + [mechanism_plan]
    validation_parts = [
        "以活動提升率、增量銷量與增量營收作為第一層成效指標，"
        "補有成本資料後改以增量毛利作為放大或停損依據"
    ]

    if overlap_exists:
        validation_parts.append(
            "活動 Excel 顯示本次存在同期檔期或優惠重疊；"
            "下次應保留一組未疊加優惠的對照商品／渠道，"
            "才能拆出主活動、平台流量與優惠各自的增量"
        )
    else:
        validation_parts.append(
            "以下一檔同商品、相近星期結構與相同觀察窗比較，"
            "避免只看單次活動的絕對銷量"
        )

    if not bool(row.get("all_periods_complete", False)):
        validation_parts.append(
            "資料完整度不足，應補齊活動前後觀察日再決策"
        )

    return (
        f"【績效診斷】{opening}"
        f"【建議決策】{decision_text}。"
        f"【下一檔執行】{'；'.join(execution_parts)}。"
        f"【驗證方式】{'；'.join(validation_parts)}。"
    )


# =========================================================
# 第一階段：銷量與活動資料整合
# =========================================================

def prepare_daily_sales(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """將同日同商品銷量加總成每日商品粒度。"""

    sales = dataframe.copy()

    required_columns = [
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in sales.columns
    ]

    if missing_columns:
        raise ValueError(
            "銷量資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    sales["sale_date"] = pd.to_datetime(
        sales["sale_date"],
        errors="coerce",
    )

    sales["product_id"] = normalize_product_id(
        sales["product_id"]
    )

    sales["product_name"] = normalize_text(sales["product_name"])

    sales["quantity"] = pd.to_numeric(
        sales["quantity"],
        errors="coerce",
    )

    sales = sales.dropna(
        subset=[
            "sale_date",
            "product_id",
            "quantity",
        ]
    ).copy()

    if sales.empty:
        raise ValueError("銷量資料整理後沒有可使用的紀錄。")

    daily_sales = (
        sales.groupby(
            ["sale_date", "product_id"],
            as_index=False,
        )
        .agg(
            product_name=(
                "product_name",
                combine_unique_text,
            ),
            quantity=("quantity", "sum"),
            source_record_count=("quantity", "size"),
            had_exact_duplicate=(
                "exact_duplicate",
                "max",
            )
            if "exact_duplicate" in sales.columns
            else (
                "quantity",
                lambda series: False,
            ),
            had_same_day_multiple=(
                "same_day_product_multiple",
                "max",
            )
            if "same_day_product_multiple" in sales.columns
            else (
                "quantity",
                lambda series: False,
            ),
        )
    )

    return daily_sales


def prepare_product_activity_days(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """將商品活動區間展開成每日商品活動資料。"""

    activity = dataframe.copy()

    required_columns = [
        "product_id",
        "activity_start_date",
        "activity_end_date",
        "campaign_price",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in activity.columns
    ]

    if missing_columns:
        raise ValueError(
            "商品活動資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    activity["product_id"] = normalize_product_id(
        activity["product_id"]
    )

    activity["activity_start_date"] = pd.to_datetime(
        activity["activity_start_date"],
        errors="coerce",
    )

    activity["activity_end_date"] = pd.to_datetime(
        activity["activity_end_date"],
        errors="coerce",
    )

    activity["campaign_price"] = pd.to_numeric(
        activity["campaign_price"],
        errors="coerce",
    )

    activity = activity.dropna(
        subset=[
            "product_id",
            "activity_start_date",
            "activity_end_date",
        ]
    ).copy()

    activity_records: list[dict[str, object]] = []

    for row in activity.itertuples():
        if row.activity_end_date < row.activity_start_date:
            continue

        for activity_date in pd.date_range(
            row.activity_start_date,
            row.activity_end_date,
            freq="D",
        ):
            activity_records.append(
                {
                    "sale_date": activity_date,
                    "product_id": row.product_id,
                    "campaign_price": row.campaign_price,
                    "activity_tag": getattr(
                        row,
                        "activity_tag",
                        None,
                    ),
                    "activity_gift": getattr(
                        row,
                        "activity_gift",
                        None,
                    ),
                    "bonus_gift_name": getattr(
                        row,
                        "bonus_gift_name",
                        None,
                    ),
                    "activity_source_file": getattr(
                        row,
                        "source_file",
                        None,
                    ),
                    "activity_source_row": getattr(
                        row,
                        "source_row_number",
                        None,
                    ),
                }
            )

    activity_days = pd.DataFrame(activity_records)

    if activity_days.empty:
        return activity_days

    activity_days = (
        activity_days.groupby(
            ["sale_date", "product_id"],
            as_index=False,
        )
        .agg(
            campaign_price=("campaign_price", "min"),
            activity_tag=(
                "activity_tag",
                combine_unique_text,
            ),
            activity_gift=(
                "activity_gift",
                combine_unique_text,
            ),
            bonus_gift_name=(
                "bonus_gift_name",
                combine_unique_text,
            ),
            product_activity_count=("product_id", "size"),
        )
    )

    activity_days["is_product_activity_day"] = True

    return activity_days


def prepare_calendar_days(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """將平台或品牌活動區間展開成每日活動。"""

    calendar = dataframe.copy()

    required_columns = [
        "campaign_start_date",
        "campaign_end_date",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in calendar.columns
    ]

    if missing_columns:
        raise ValueError(
            "活動日曆資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    calendar["campaign_start_date"] = pd.to_datetime(
        calendar["campaign_start_date"],
        errors="coerce",
    )

    calendar["campaign_end_date"] = pd.to_datetime(
        calendar["campaign_end_date"],
        errors="coerce",
    )

    calendar = calendar.dropna(
        subset=[
            "campaign_start_date",
            "campaign_end_date",
        ]
    ).copy()

    calendar_records: list[dict[str, object]] = []

    for row in calendar.itertuples():
        if row.campaign_end_date < row.campaign_start_date:
            continue

        for campaign_date in pd.date_range(
            row.campaign_start_date,
            row.campaign_end_date,
            freq="D",
        ):
            calendar_records.append(
                {
                    "sale_date": campaign_date,
                    "campaign_name": getattr(
                        row,
                        "campaign_name",
                        None,
                    ),
                    "campaign_level": getattr(
                        row,
                        "campaign_level",
                        None,
                    ),
                }
            )

    calendar_days = pd.DataFrame(calendar_records)

    if calendar_days.empty:
        return calendar_days

    calendar_days = (
        calendar_days.groupby(
            "sale_date",
            as_index=False,
        )
        .agg(
            campaign_name=(
                "campaign_name",
                combine_unique_text,
            ),
            campaign_level=(
                "campaign_level",
                combine_unique_text,
            ),
            calendar_activity_count=("campaign_name", "size"),
        )
    )

    calendar_days["is_calendar_activity_day"] = True

    return calendar_days


def prepare_benefit_days(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """將優惠區間展開為指定商品優惠與全站優惠。"""

    benefits = dataframe.copy()

    required_columns = [
        "product_id",
        "benefit_start_date",
        "benefit_end_date",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in benefits.columns
    ]

    if missing_columns:
        raise ValueError(
            "優惠內容資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    benefits["product_id"] = normalize_product_id(
        benefits["product_id"]
    )

    benefits["benefit_start_date"] = pd.to_datetime(
        benefits["benefit_start_date"],
        errors="coerce",
    )

    benefits["benefit_end_date"] = pd.to_datetime(
        benefits["benefit_end_date"],
        errors="coerce",
    )

    benefits = benefits.dropna(
        subset=[
            "benefit_start_date",
            "benefit_end_date",
        ]
    ).copy()

    product_benefit_records: list[dict[str, object]] = []
    global_benefit_records: list[dict[str, object]] = []

    for row in benefits.itertuples():
        if row.benefit_end_date < row.benefit_start_date:
            continue

        for benefit_date in pd.date_range(
            row.benefit_start_date,
            row.benefit_end_date,
            freq="D",
        ):
            record = {
                "sale_date": benefit_date,
                "benefit_type": getattr(
                    row,
                    "benefit_type",
                    None,
                ),
                "benefit_content": getattr(
                    row,
                    "benefit_content",
                    None,
                ),
                "campaign_name": getattr(
                    row,
                    "campaign_name",
                    None,
                ),
                "threshold_amount": getattr(
                    row,
                    "threshold_amount",
                    None,
                ),
                "reward_percentage": getattr(
                    row,
                    "reward_percentage",
                    None,
                ),
                "reward_amount": getattr(
                    row,
                    "reward_amount",
                    None,
                ),
            }

            if pd.notna(row.product_id):
                record["product_id"] = row.product_id
                product_benefit_records.append(record)
            else:
                global_benefit_records.append(record)

    product_benefits = pd.DataFrame(product_benefit_records)
    global_benefits = pd.DataFrame(global_benefit_records)

    if not product_benefits.empty:
        product_benefits = (
            product_benefits.groupby(
                ["sale_date", "product_id"],
                as_index=False,
            )
            .agg(
                product_benefit_type=(
                    "benefit_type",
                    combine_unique_text,
                ),
                product_benefit_content=(
                    "benefit_content",
                    combine_unique_text,
                ),
                product_benefit_campaign=(
                    "campaign_name",
                    combine_unique_text,
                ),
                product_benefit_count=("benefit_type", "size"),
            )
        )

        product_benefits["has_product_benefit"] = True

    if not global_benefits.empty:
        global_benefits = (
            global_benefits.groupby(
                "sale_date",
                as_index=False,
            )
            .agg(
                global_benefit_type=(
                    "benefit_type",
                    combine_unique_text,
                ),
                global_benefit_content=(
                    "benefit_content",
                    combine_unique_text,
                ),
                global_benefit_campaign=(
                    "campaign_name",
                    combine_unique_text,
                ),
                global_benefit_count=("benefit_type", "size"),
            )
        )

        global_benefits["has_global_benefit"] = True

    return product_benefits, global_benefits


def build_integrated_data(
    sales_dataframe: pd.DataFrame,
    main_activity_dataframe: pd.DataFrame,
    calendar_dataframe: pd.DataFrame,
    benefits_dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """建立每日商品活動整合資料與整合問題清單。"""

    if sales_dataframe is None:
        raise ValueError("缺少標準化銷量資料。")

    if main_activity_dataframe is None:
        raise ValueError("缺少商品活動價格資料。")

    if calendar_dataframe is None:
        raise ValueError("缺少活動日曆資料。")

    if benefits_dataframe is None:
        raise ValueError("缺少優惠內容資料。")

    daily_sales = prepare_daily_sales(sales_dataframe)

    product_activity_days = prepare_product_activity_days(
        main_activity_dataframe
    )

    calendar_days = prepare_calendar_days(calendar_dataframe)

    (
        product_benefit_days,
        global_benefit_days,
    ) = prepare_benefit_days(benefits_dataframe)

    integrated = daily_sales.copy()

    if not product_activity_days.empty:
        integrated = integrated.merge(
            product_activity_days,
            on=["sale_date", "product_id"],
            how="left",
        )

    if not calendar_days.empty:
        integrated = integrated.merge(
            calendar_days,
            on="sale_date",
            how="left",
        )

    if not product_benefit_days.empty:
        integrated = integrated.merge(
            product_benefit_days,
            on=["sale_date", "product_id"],
            how="left",
        )

    if not global_benefit_days.empty:
        integrated = integrated.merge(
            global_benefit_days,
            on="sale_date",
            how="left",
        )

    boolean_columns = [
        "is_product_activity_day",
        "is_calendar_activity_day",
        "has_product_benefit",
        "has_global_benefit",
    ]

    for column in boolean_columns:
        if column not in integrated.columns:
            integrated[column] = False
        else:
            integrated[column] = (
                integrated[column]
                .fillna(False)
                .astype(bool)
            )

    integrated["has_any_activity"] = integrated[
        boolean_columns
    ].any(axis=1)

    if "campaign_price" not in integrated.columns:
        integrated["campaign_price"] = pd.NA

    integrated["estimated_revenue"] = (
        integrated["quantity"]
        * integrated["campaign_price"]
    )

    integrated = integrated.sort_values(
        by=["sale_date", "product_id"]
    ).reset_index(drop=True)

    integration_issues = integrated[
        integrated["is_product_activity_day"]
        & integrated["campaign_price"].isna()
    ].copy()

    return integrated, integration_issues


# =========================================================
# 第二階段：活動成效分析
# =========================================================

def prepare_daily_performance_sales(
    integrated_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """整理活動成效分析使用的每日商品銷量。"""

    integrated = coerce_arrow_strings_to_object(
        integrated_dataframe
    )

    required_columns = [
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in integrated.columns
    ]

    if missing_columns:
        raise ValueError(
            "整合資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    integrated["sale_date"] = pd.to_datetime(
        integrated["sale_date"],
        errors="coerce",
    )

    integrated["product_id"] = normalize_product_id(
        integrated["product_id"]
    )

    integrated["quantity"] = pd.to_numeric(
        integrated["quantity"],
        errors="coerce",
    )

    if "campaign_price" in integrated.columns:
        integrated["campaign_price"] = pd.to_numeric(
            integrated["campaign_price"],
            errors="coerce",
        )

    integrated = integrated.dropna(
        subset=[
            "sale_date",
            "product_id",
            "quantity",
        ]
    ).copy()

    if integrated.empty:
        raise ValueError("整合資料整理後沒有可使用的銷量紀錄。")

    daily_sales = (
        integrated.groupby(
            ["sale_date", "product_id"],
            as_index=False,
        )
        .agg(
            product_name=(
                "product_name",
                combine_unique_text,
            ),
            quantity=("quantity", "sum"),
            campaign_price=("campaign_price", "min")
            if "campaign_price" in integrated.columns
            else ("quantity", lambda _: pd.NA),
            campaign_name=(
                "campaign_name",
                combine_unique_text,
            )
            if "campaign_name" in integrated.columns
            else ("quantity", lambda _: None),
            global_benefit_type=(
                "global_benefit_type",
                combine_unique_text,
            )
            if "global_benefit_type" in integrated.columns
            else ("quantity", lambda _: None),
            product_benefit_type=(
                "product_benefit_type",
                combine_unique_text,
            )
            if "product_benefit_type" in integrated.columns
            else ("quantity", lambda _: None),
        )
    )

    return daily_sales


def prepare_activity_periods(
    activity_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """整理可供成效分析使用的商品活動期間。"""

    activities = coerce_arrow_strings_to_object(
        activity_dataframe
    )

    required_columns = [
        "product_id",
        "activity_start_date",
        "activity_end_date",
        "campaign_price",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in activities.columns
    ]

    if missing_columns:
        raise ValueError(
            "商品活動資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    activities["product_id"] = normalize_product_id(
        activities["product_id"]
    )

    activities["activity_start_date"] = pd.to_datetime(
        activities["activity_start_date"],
        errors="coerce",
    )

    activities["activity_end_date"] = pd.to_datetime(
        activities["activity_end_date"],
        errors="coerce",
    )

    activities["campaign_price"] = pd.to_numeric(
        activities["campaign_price"],
        errors="coerce",
    )

    activities = activities.dropna(
        subset=[
            "product_id",
            "activity_start_date",
            "activity_end_date",
        ]
    ).copy()

    activities = activities[
        activities["activity_end_date"]
        >= activities["activity_start_date"]
    ].copy()

    if activities.empty:
        raise ValueError("目前沒有可用的商品活動期間資料。")

    return activities


def get_period_daily_sales(
    daily_sales: pd.DataFrame,
    product_id: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    fill_zero: bool,
) -> tuple[pd.DataFrame, int, int]:
    """取得指定商品與日期區間的每日銷量。"""

    expected_dates = pd.date_range(
        start_date,
        end_date,
        freq="D",
    )

    required_output_columns = [
        "sale_date",
        "quantity",
        "campaign_price",
        "campaign_name",
        "global_benefit_type",
        "product_benefit_type",
    ]

    period_source = daily_sales.copy()

    for column in required_output_columns:
        if column not in period_source.columns:
            period_source[column] = pd.NA

    product_period_sales = period_source[
        (period_source["product_id"] == product_id)
        & period_source["sale_date"].between(
            start_date,
            end_date,
        )
    ][required_output_columns].copy()

    recorded_day_count = product_period_sales[
        "sale_date"
    ].nunique()

    if fill_zero:
        calendar_dataframe = pd.DataFrame(
            {"sale_date": expected_dates}
        )

        product_period_sales = calendar_dataframe.merge(
            product_period_sales,
            on="sale_date",
            how="left",
        )

        product_period_sales["quantity"] = (
            product_period_sales["quantity"].fillna(0)
        )

    return (
        product_period_sales,
        len(expected_dates),
        int(recorded_day_count),
    )


def calculate_activity_performance(
    activity_row: pd.Series,
    daily_sales: pd.DataFrame,
    data_min_date: pd.Timestamp,
    data_max_date: pd.Timestamp,
    settings: AnalysisSettings,
) -> dict[str, object]:
    """計算單一商品活動前、中、後的成效。"""

    product_id = str(activity_row["product_id"])
    activity_start = activity_row["activity_start_date"]
    activity_end = activity_row["activity_end_date"]

    baseline_start = activity_start - pd.Timedelta(
        days=int(settings.baseline_days)
    )
    baseline_end = activity_start - pd.Timedelta(days=1)

    post_start = activity_end + pd.Timedelta(days=1)
    post_end = activity_end + pd.Timedelta(
        days=int(settings.post_days)
    )

    (
        baseline_sales,
        baseline_expected_days,
        baseline_recorded_days,
    ) = get_period_daily_sales(
        daily_sales,
        product_id,
        baseline_start,
        baseline_end,
        settings.fill_missing_dates_with_zero,
    )

    (
        campaign_sales,
        campaign_expected_days,
        campaign_recorded_days,
    ) = get_period_daily_sales(
        daily_sales,
        product_id,
        activity_start,
        activity_end,
        settings.fill_missing_dates_with_zero,
    )

    (
        post_sales,
        post_expected_days,
        post_recorded_days,
    ) = get_period_daily_sales(
        daily_sales,
        product_id,
        post_start,
        post_end,
        settings.fill_missing_dates_with_zero,
    )

    baseline_average = (
        baseline_sales["quantity"].mean()
        if not baseline_sales.empty
        else pd.NA
    )

    campaign_average = (
        campaign_sales["quantity"].mean()
        if not campaign_sales.empty
        else pd.NA
    )

    post_average = (
        post_sales["quantity"].mean()
        if not post_sales.empty
        else pd.NA
    )

    campaign_total = (
        campaign_sales["quantity"].sum()
        if not campaign_sales.empty
        else 0
    )

    uplift_rate = safe_percentage_change(
        campaign_average,
        baseline_average,
    )

    post_change_rate = safe_percentage_change(
        post_average,
        campaign_average,
    )

    baseline_complete = (
        baseline_start >= data_min_date
        and baseline_end <= data_max_date
    )

    campaign_complete = (
        activity_start >= data_min_date
        and activity_end <= data_max_date
    )

    post_complete = (
        post_start >= data_min_date
        and post_end <= data_max_date
    )

    all_periods_complete = (
        baseline_complete
        and campaign_complete
        and post_complete
    )

    campaign_price_values = (
        campaign_sales["campaign_price"].dropna()
        if (
            not campaign_sales.empty
            and "campaign_price" in campaign_sales.columns
        )
        else pd.Series(dtype=float)
    )

    if not campaign_price_values.empty:
        effective_campaign_price = campaign_price_values.min()
    else:
        effective_campaign_price = activity_row.get(
            "campaign_price",
            pd.NA,
        )

    if pd.notna(effective_campaign_price):
        estimated_revenue = (
            campaign_total * effective_campaign_price
        )
    else:
        estimated_revenue = pd.NA

    overlapping_campaigns = (
        safe_unique_text_list(
            campaign_sales["campaign_name"]
        )
        if not campaign_sales.empty
        else []
    )

    overlapping_benefits: list[str] = []

    if not campaign_sales.empty:
        for benefit_column in [
            "global_benefit_type",
            "product_benefit_type",
        ]:
            if benefit_column in campaign_sales.columns:
                values = safe_unique_text_list(
                    campaign_sales[benefit_column]
                )

                for value in values:
                    if value not in overlapping_benefits:
                        overlapping_benefits.append(value)

    if all_periods_complete:
        data_confidence = "較高"
    elif campaign_complete:
        data_confidence = "中等"
    else:
        data_confidence = "較低"

    return {
        "product_id": product_id,
        "product_name": activity_row.get(
            "product_name",
            None,
        ),
        "activity_start_date": activity_start,
        "activity_end_date": activity_end,
        "activity_days": (
            activity_end - activity_start
        ).days
        + 1,
        "campaign_price": effective_campaign_price,
        "activity_tag": activity_row.get(
            "activity_tag",
            None,
        ),
        "activity_gift": activity_row.get(
            "activity_gift",
            None,
        ),
        "baseline_start_date": baseline_start,
        "baseline_end_date": baseline_end,
        "post_start_date": post_start,
        "post_end_date": post_end,
        "baseline_average_daily_sales": baseline_average,
        "campaign_average_daily_sales": campaign_average,
        "post_average_daily_sales": post_average,
        "campaign_total_sales": campaign_total,
        "uplift_rate": uplift_rate,
        "post_change_rate": post_change_rate,
        "estimated_revenue": estimated_revenue,
        "baseline_expected_days": baseline_expected_days,
        "baseline_recorded_days": baseline_recorded_days,
        "campaign_expected_days": campaign_expected_days,
        "campaign_recorded_days": campaign_recorded_days,
        "post_expected_days": post_expected_days,
        "post_recorded_days": post_recorded_days,
        "baseline_complete": baseline_complete,
        "campaign_complete": campaign_complete,
        "post_complete": post_complete,
        "all_periods_complete": all_periods_complete,
        "overlapping_campaigns": (
            "、".join(overlapping_campaigns)
            if overlapping_campaigns
            else None
        ),
        "overlapping_benefits": (
            "、".join(overlapping_benefits)
            if overlapping_benefits
            else None
        ),
        "data_confidence": data_confidence,
    }


def analyze_activity_performance(
    integrated_dataframe: pd.DataFrame,
    activity_dataframe: pd.DataFrame,
    settings: AnalysisSettings | None = None,
) -> pd.DataFrame:
    """計算所有商品活動的前、中、後成效。"""

    settings = settings or AnalysisSettings()

    if settings.baseline_days < 1:
        raise ValueError("活動前基準天數至少需要 1 天。")

    if settings.post_days < 1:
        raise ValueError("活動後觀察天數至少需要 1 天。")

    daily_sales = prepare_daily_performance_sales(
        integrated_dataframe
    )

    activities = prepare_activity_periods(
        activity_dataframe
    )

    data_min_date = daily_sales["sale_date"].min()
    data_max_date = daily_sales["sale_date"].max()

    performance_records = [
        calculate_activity_performance(
            activity_row=activity_row,
            daily_sales=daily_sales,
            data_min_date=data_min_date,
            data_max_date=data_max_date,
            settings=settings,
        )
        for _, activity_row in activities.iterrows()
    ]

    performance_dataframe = pd.DataFrame(
        performance_records
    )

    if performance_dataframe.empty:
        return performance_dataframe

    performance_dataframe = (
        performance_dataframe.sort_values(
            by=[
                "activity_start_date",
                "product_id",
            ]
        ).reset_index(drop=True)
    )

    return performance_dataframe


# =========================================================
# 第三階段：策略建議報告
# =========================================================

def prepare_performance_dataframe(
    performance_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """整理策略報告需要的資料型別。"""

    performance = performance_dataframe.copy()

    date_columns = [
        "activity_start_date",
        "activity_end_date",
    ]

    for column in date_columns:
        if column in performance.columns:
            performance[column] = pd.to_datetime(
                performance[column],
                errors="coerce",
            )

    numeric_columns = [
        "baseline_average_daily_sales",
        "campaign_average_daily_sales",
        "post_average_daily_sales",
        "campaign_total_sales",
        "uplift_rate",
        "post_change_rate",
        "estimated_revenue",
    ]

    for column in numeric_columns:
        if column in performance.columns:
            performance[column] = pd.to_numeric(
                performance[column],
                errors="coerce",
            )

    boolean_columns = [
        "baseline_complete",
        "campaign_complete",
        "post_complete",
        "all_periods_complete",
    ]

    for column in boolean_columns:
        if column in performance.columns:
            performance[column] = (
                performance[column]
                .fillna(False)
                .astype(bool)
            )

    return performance


def generate_strategy_report(
    performance_dataframe: pd.DataFrame,
    settings: AnalysisSettings | None = None,
) -> tuple[pd.DataFrame, str]:
    """依照活動成效結果產生策略資料表與文字報告。"""

    settings = settings or AnalysisSettings()

    if (
        settings.high_uplift_threshold
        <= settings.low_uplift_threshold
    ):
        raise ValueError(
            "高成效提升率門檻必須大於低成效提升率門檻。"
        )

    if performance_dataframe is None:
        raise ValueError("缺少活動成效分析結果。")

    if performance_dataframe.empty:
        raise ValueError("目前沒有可產生策略報告的活動資料。")

    performance = prepare_performance_dataframe(
        performance_dataframe
    )

    required_columns = [
        "all_periods_complete",
        "uplift_rate",
        "campaign_total_sales",
        "baseline_average_daily_sales",
        "post_change_rate",
        "overlapping_campaigns",
        "overlapping_benefits",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in performance.columns
    ]

    if missing_columns:
        raise ValueError(
            "成效分析資料缺少策略報告必要欄位："
            + "、".join(missing_columns)
        )

    decision_ready_mask = performance["uplift_rate"].notna()

    if settings.only_complete_periods:
        decision_ready_mask = (
            decision_ready_mask
            & performance["all_periods_complete"]
        )

    valid_uplift = performance[
        decision_ready_mask
    ].copy()

    continue_mask = (
        (
            valid_uplift["uplift_rate"]
            >= settings.high_uplift_threshold
        )
        & (
            valid_uplift["campaign_total_sales"]
            >= settings.minimum_campaign_sales
        )
    )

    review_mask = (
        valid_uplift["uplift_rate"]
        < settings.low_uplift_threshold
    )

    optimize_mask = ~(continue_mask | review_mask)

    high_performance = valid_uplift[
        continue_mask
    ].copy()

    low_performance = valid_uplift[
        review_mask
    ].copy()

    stable_performance = valid_uplift[
        optimize_mask
    ].copy()

    incomplete_periods = performance[
        ~performance["all_periods_complete"]
    ].copy()

    zero_or_missing_baseline = performance[
        performance[
            "baseline_average_daily_sales"
        ].isna()
        | (
            performance[
                "baseline_average_daily_sales"
            ]
            == 0
        )
    ].copy()

    overlap_risk = performance[
        performance["overlapping_campaigns"].notna()
        | performance["overlapping_benefits"].notna()
    ].copy()

    post_decline = performance[
        performance["post_change_rate"] < -0.20
    ].copy()

    strategy_rows: list[dict[str, object]] = []

    for row_index, row in performance.iterrows():
        decision_ready = bool(
            decision_ready_mask.loc[row_index]
        )

        if not decision_ready:
            category = "資料不足／待補資料"
        elif row["uplift_rate"] < settings.low_uplift_threshold:
            category = "建議檢討"
        elif (
            row["uplift_rate"]
            >= settings.high_uplift_threshold
            and row["campaign_total_sales"]
            >= settings.minimum_campaign_sales
        ):
            category = "建議延續"
        else:
            category = "建議優化"

        campaign_period = infer_campaign_period(row)
        strategy_metrics = calculate_strategy_metrics(row)
        excel_context = activity_excel_context(row)

        if not decision_ready:
            strategy_metrics = {
                metric_name: pd.NA
                for metric_name in strategy_metrics
            }

        history_context = build_product_history_context(
            row=row,
            comparable_dataframe=valid_uplift,
            include_current_comparison=decision_ready,
        )

        strategy_rows.append(
            {
                "策略分類": category,
                "商品活動": activity_label(row),
                "活動提升率": row["uplift_rate"],
                "活動總銷量": row[
                    "campaign_total_sales"
                ],
                "推估營收": row.get("estimated_revenue"),
                "資料信心": row.get("data_confidence"),
                "資料完整度": data_completeness_label(row),
                "活動天數": row.get("activity_days"),
                "正式判讀": decision_ready,
                "資料缺漏說明": build_missing_data_note(row),
                **strategy_metrics,
                "判斷依據": build_strategy_reason(
                    row=row,
                    category=category,
                    settings=settings,
                ),
                "可能影響檔期／活動": campaign_period,
                "檔期判讀來源": (
                    "活動 Excel"
                    if excel_context["has_excel_context"]
                    else "日期推測"
                ),
                "活動／優惠重疊": bool(
                    excel_context["has_overlap"]
                ),
                "檔期／歸因判讀": build_attribution_note(
                    row=row,
                    campaign_period=campaign_period,
                    metrics=strategy_metrics,
                ),
                "建議": build_personalized_recommendation(
                    row=row,
                    category=category,
                    campaign_period=campaign_period,
                    metrics=strategy_metrics,
                    settings=settings,
                    history_context=history_context,
                ),
            }
        )

    strategy_dataframe = pd.DataFrame(strategy_rows)

    if not strategy_dataframe.empty:
        category_order = {
            "建議延續": 0,
            "建議優化": 1,
            "建議檢討": 2,
            "資料不足／待補資料": 3,
        }
        strategy_dataframe["分類排序"] = (
            strategy_dataframe["策略分類"].map(
                category_order
            )
        )
        strategy_dataframe = (
            strategy_dataframe.sort_values(
                by=["分類排序", "活動提升率"],
                ascending=[True, False],
            )
            .drop(columns=["分類排序"])
            .reset_index(drop=True)
        )

    total_count = len(performance)
    complete_count = int(
        performance["all_periods_complete"].sum()
    )

    category_counts = strategy_dataframe[
        "策略分類"
    ].value_counts()
    high_count = int(category_counts.get("建議延續", 0))
    low_count = int(category_counts.get("建議檢討", 0))
    stable_count = int(category_counts.get("建議優化", 0))
    insufficient_count = int(
        category_counts.get("資料不足／待補資料", 0)
    )

    median_uplift = valid_uplift["uplift_rate"].median()

    report_lines = [
        "# 策略建議報表",
        "",
        "## 一、分析摘要",
        "",
        f"- 共分析 {total_count} 筆商品活動。",
        f"- 完整前、中、後觀察期間：{complete_count} 筆。",
        f"- 建議延續：{high_count} 筆。",
        f"- 建議優化：{stable_count} 筆。",
        f"- 建議檢討：{low_count} 筆。",
        f"- 資料不足／待補資料：{insufficient_count} 筆（仍保留在清單）。",
        (
            "- 可計算活動的提升率中位數："
            f"{format_percentage(median_uplift)}。"
        ),
        "",
        "## 二、分類標準",
        "",
        (
            "- 建議延續：活動提升率 ≥ "
            f"{settings.high_uplift_threshold:.1%}，且活動總銷量 ≥ "
            f"{settings.minimum_campaign_sales:,.0f}。"
        ),
        (
            "- 建議檢討：活動提升率 < "
            f"{settings.low_uplift_threshold:.1%}。"
        ),
        (
            "- 建議優化：提升率介於上述門檻，或提升率已達高門檻"
            "但活動總銷量未達最低規模。"
        ),
        (
            "- 活動提升率 =（活動期平均日銷量－活動前平均日銷量）"
            "÷ 活動前平均日銷量。"
        ),
        (
            "- 資料不足／待補資料：活動前、中、後觀察期間未完整，"
            "或活動前基準為 0，先不套用三種正式策略分類。"
        ),
        (
            "- 活動與檔期名稱以活動 Excel 為主要依據；"
            "只有 Excel 無可用名稱時才以日期推測。"
        ),
        "",
        "## 三、策略建議",
        "",
    ]

    if high_performance.empty:
        report_lines.append(
            "- 目前沒有符合高成效門檻且資料完整的活動。"
        )
    else:
        report_lines.append(
            "- 建議延續高提升率且活動總銷量具規模的活動，"
            "並測試擴大曝光、備貨或套用至相似商品。"
        )

    if low_performance.empty:
        report_lines.append(
            "- 目前沒有低於低成效門檻的完整活動。"
        )
    else:
        report_lines.append(
            "- 低成效活動應優先檢查定價、曝光、庫存、"
            "商品適配與活動重疊，不建議直接複製原方案。"
        )

    if not post_decline.empty:
        report_lines.append(
            "- 部分活動結束後銷量明顯下降，"
            "可能存在需求提前透支，"
            "後續應評估活動頻率與間隔。"
        )

    if not overlap_risk.empty:
        report_lines.append(
            "- 多筆活動與平台檔期或其他優惠重疊，"
            "目前無法將效果完全歸因於單一活動。"
        )

    report_lines.extend(
        [
            "",
            "## 四、資料限制",
            "",
            (
                "- 觀察期間不完整："
                f"{len(incomplete_periods)} 筆。"
            ),
            (
                "- 基準銷量為 0 或缺漏："
                f"{len(zero_or_missing_baseline)} 筆。"
            ),
            (
                "- 存在重疊活動或優惠："
                f"{len(overlap_risk)} 筆。"
            ),
            "- 推估營收未納入實際成交折扣、退貨、平台幣與贈品成本。",
            "- 本報告描述活動期間的銷量變化，不代表已證明因果關係。",
        ]
    )

    strategy_report_text = "\n".join(report_lines)

    return strategy_dataframe, strategy_report_text


# =========================================================
# 完整三階段流程
# =========================================================

def run_full_analysis(
    sales_dataframe: pd.DataFrame,
    main_activity_dataframe: pd.DataFrame,
    calendar_dataframe: pd.DataFrame,
    benefits_dataframe: pd.DataFrame,
    settings: AnalysisSettings | None = None,
) -> AnalysisPipelineResult:
    """依序執行資料整合、成效分析與策略報告。"""

    settings = settings or AnalysisSettings()

    (
        integrated_dataframe,
        integration_issues_dataframe,
    ) = build_integrated_data(
        sales_dataframe=sales_dataframe,
        main_activity_dataframe=main_activity_dataframe,
        calendar_dataframe=calendar_dataframe,
        benefits_dataframe=benefits_dataframe,
    )

    performance_dataframe = analyze_activity_performance(
        integrated_dataframe=integrated_dataframe,
        activity_dataframe=main_activity_dataframe,
        settings=settings,
    )

    (
        strategy_dataframe,
        strategy_report_text,
    ) = generate_strategy_report(
        performance_dataframe=performance_dataframe,
        settings=settings,
    )

    return AnalysisPipelineResult(
        integrated_dataframe=integrated_dataframe,
        integration_issues_dataframe=(
            integration_issues_dataframe
        ),
        performance_dataframe=performance_dataframe,
        strategy_dataframe=strategy_dataframe,
        strategy_report_text=strategy_report_text,
    )
