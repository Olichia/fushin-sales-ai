from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# =========================================================
# 情境模擬（What-if Simulation）
#
# 刻意不用任何預測模型：全部是使用者輸入條件＋既有活動單位
# 分析同一套「淨營收效應＝活動營收－無活動預期營收」邏輯的
# 規則式試算，維持跟系統其他頁面一致、可解釋的計算方式。
# =========================================================

@dataclass
class WhatIfScenarioInput:
    """單一情境方案的輸入條件。"""

    label: str
    activity_price: float
    baseline_price: float
    estimated_daily_sales: float
    days: int
    has_gift: bool = False
    gift_cost_per_unit: float = 0.0
    platform_overlap: bool = False


@dataclass
class WhatIfScenarioResult:
    """單一情境方案的試算結果。"""

    label: str
    discount_rate: float | None
    estimated_activity_revenue: float
    expected_revenue_without_activity: float
    net_revenue_gain: float
    total_gift_cost: float
    simplified_net_benefit: float
    has_gift: bool
    platform_overlap: bool


def compute_whatif_scenario(
    scenario_input: WhatIfScenarioInput,
) -> WhatIfScenarioResult:
    """
    試算單一方案。

    折扣率 = 1 － (活動價 ÷ 安靜期基準價)，跟活動單位分析頁面
    既有的折扣率算法一致；淨營收增益 = 活動預估營收 － 無活動
    預期營收（用基準價與同一份預估日均銷量推算，不是另一套
    假設）；簡化後淨效益再扣掉贈品成本，全部是加減乘除，
    沒有任何預測模型或黑箱參數。
    """

    discount_rate = None

    if scenario_input.baseline_price:
        discount_rate = 1 - (
            scenario_input.activity_price
            / scenario_input.baseline_price
        )

    estimated_activity_revenue = (
        scenario_input.activity_price
        * scenario_input.estimated_daily_sales
        * scenario_input.days
    )

    expected_revenue_without_activity = (
        scenario_input.baseline_price
        * scenario_input.estimated_daily_sales
        * scenario_input.days
    )

    net_revenue_gain = (
        estimated_activity_revenue
        - expected_revenue_without_activity
    )

    total_gift_cost = (
        scenario_input.gift_cost_per_unit
        * scenario_input.estimated_daily_sales
        * scenario_input.days
        if scenario_input.has_gift
        else 0.0
    )

    simplified_net_benefit = net_revenue_gain - total_gift_cost

    return WhatIfScenarioResult(
        label=scenario_input.label,
        discount_rate=discount_rate,
        estimated_activity_revenue=estimated_activity_revenue,
        expected_revenue_without_activity=(
            expected_revenue_without_activity
        ),
        net_revenue_gain=net_revenue_gain,
        total_gift_cost=total_gift_cost,
        simplified_net_benefit=simplified_net_benefit,
        has_gift=scenario_input.has_gift,
        platform_overlap=scenario_input.platform_overlap,
    )


def compute_whatif_scenarios(
    scenario_inputs: list[WhatIfScenarioInput],
) -> list[WhatIfScenarioResult]:
    """依序試算多個方案（介面上用來比較 A／B／C）。"""

    return [
        compute_whatif_scenario(scenario_input)
        for scenario_input in scenario_inputs
    ]


def select_best_scenario(
    results: list[WhatIfScenarioResult],
) -> WhatIfScenarioResult | None:
    """簡化後淨效益最高的方案，用於畫面上標示推薦選項。"""

    if not results:
        return None

    return max(results, key=lambda result: result.simplified_net_benefit)


# =========================================================
# 從既有活動單位分析取得預設值
#
# 只是給表單一個合理的起始值，使用者仍可自行覆蓋；
# 找不到同商品歷史資料時回傳 None，介面要能處理空值。
# =========================================================

def estimate_daily_sales_from_history(
    unit_overview_dataframe: pd.DataFrame,
    product_id: str,
) -> float | None:
    """取同商品過往活動單位的日均銷量中位數，當作預估日均銷量預設值。"""

    if (
        not isinstance(unit_overview_dataframe, pd.DataFrame)
        or unit_overview_dataframe.empty
    ):
        return None

    product_rows = unit_overview_dataframe[
        unit_overview_dataframe["product_id"].astype(str)
        == str(product_id)
    ]

    sales = pd.to_numeric(
        product_rows.get("unit_avg_sales"), errors="coerce"
    ).dropna()

    if sales.empty:
        return None

    return float(sales.median())


def build_whatif_summary_insight(
    scenario_results: list[WhatIfScenarioResult],
) -> dict[str, str]:
    """
    把模擬結果組成「發現／原因／建議」三段摘要（規則式生成，
    不呼叫 LLM）。

    情境模擬需要讓使用者反覆調整輸入、立即看到比較結果，
    即時 LLM 呼叫的延遲（實測約 10～25 秒）不適合這種互動節奏，
    所以沿用系統其他「AI 洞察卡片」的慣例：直接從已經算出的
    數字組句，維持可解釋、零延遲、零 API 失敗風險。
    """

    if not scenario_results:
        return {
            "finding": "尚無模擬結果。",
            "reason": "尚未輸入方案條件。",
            "action": "請在左側輸入方案條件後按「執行模擬」。",
        }

    best = select_best_scenario(scenario_results)
    worst = min(
        scenario_results,
        key=lambda result: result.simplified_net_benefit,
    )

    benefit_gap = (
        best.simplified_net_benefit - worst.simplified_net_benefit
    )

    finding = (
        f"「{best.label}」的簡化後淨效益最高，約"
        f"{best.simplified_net_benefit:+,.0f} 元；"
        f"比表現最差的「{worst.label}」高出 {benefit_gap:,.0f} 元。"
    )

    reason_parts: list[str] = []

    if best.has_gift:
        reason_parts.append(
            "即使扣除贈品成本，這個方案的淨效益仍是三者中最高，"
            "代表目前輸入的贈品成本相對可控。"
        )
    else:
        reason_parts.append(
            "模型不會假設贈品或更深的折扣會帶動額外銷量，"
            "所以沒有額外成本、折扣也較淺的方案在帳面上通常較有利；"
            "如果您預期贈品或折扣能提升轉換率，"
            "建議直接調高對應方案的「預估日均銷量」再重新比較，"
            "而不是用同一個銷量假設比較所有方案。"
        )

    if any(
        result.platform_overlap for result in scenario_results
    ):
        reason_parts.append(
            "有方案同時勾選「搭配平台活動」，"
            "實際疊加貢獻需要瀑布法配對比較才能拆分，"
            "這裡的試算並未計入這部分效果。"
        )

    action = (
        f"建議以「{best.label}」作為下一檔的優先測試方向，"
        "並在實際執行後回填真實日均銷量，"
        "確認是否與這裡的預估相符，再決定要不要放大或調整方案。"
    )

    return {
        "finding": finding,
        "reason": "".join(reason_parts),
        "action": action,
    }


def estimate_baseline_price_from_history(
    unit_overview_dataframe: pd.DataFrame,
    product_id: str,
) -> float | None:
    """取同商品過往活動單位的安靜期基準價中位數，當作基準價預設值。"""

    if (
        not isinstance(unit_overview_dataframe, pd.DataFrame)
        or unit_overview_dataframe.empty
    ):
        return None

    product_rows = unit_overview_dataframe[
        unit_overview_dataframe["product_id"].astype(str)
        == str(product_id)
    ]

    prices = pd.to_numeric(
        product_rows.get("baseline_price"), errors="coerce"
    ).dropna()

    if prices.empty:
        return None

    return float(prices.median())
