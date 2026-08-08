from __future__ import annotations

import pandas as pd

from src.unit_overview_helpers import (
    compute_actual_revenue_total,
    compute_confidence_label,
    compute_risk_mask,
    compute_strategy_category,
    prepare_unit_overview_for_display,
)
from src.unit_recommendation_notes import format_signed_currency


# =========================================================
# 折扣率區間統計（供文字摘要與PDF共用）
# =========================================================

DISCOUNT_BRACKET_BINS = [-1, 0, 0.05, 0.10, 0.15, 0.20, 1]

DISCOUNT_BRACKET_LABELS = [
    "無折扣/漲價",
    "0-5%",
    "5-10%",
    "10-15%",
    "15-20%",
    "20%以上",
]


def compute_discount_bracket_stats(
    unit_overview_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    依折扣率切區間，統計各區間的平均淨增益/日與檔數。
    回傳欄位：discount_bracket、avg_net_effect、unit_count。
    """

    discount_data = unit_overview_dataframe.dropna(
        subset=["discount_rate", "net_revenue_effect_per_day"]
    )

    if discount_data.empty:
        return pd.DataFrame(
            columns=[
                "discount_bracket",
                "avg_net_effect",
                "unit_count",
            ]
        )

    binned = discount_data.copy()
    binned["discount_bracket"] = pd.cut(
        binned["discount_rate"],
        bins=DISCOUNT_BRACKET_BINS,
        labels=DISCOUNT_BRACKET_LABELS,
    )

    stats = binned.groupby(
        "discount_bracket", observed=True
    ).agg(
        avg_net_effect=("net_revenue_effect_per_day", "mean"),
        unit_count=("unit_code", "count"),
    )

    stats = stats[stats["unit_count"] > 0].reset_index()

    return stats


# =========================================================
# 疊加活動組合排行（供文字摘要與PDF共用）
# =========================================================

def compute_top_activity_combos(
    waterfall_summary_dataframe: pd.DataFrame,
    top_n: int = 5,
) -> pd.DataFrame:
    """依增益合計排行前 N 名活動組合（可拆分/不可拆分皆含）。"""

    if (
        waterfall_summary_dataframe is None
        or waterfall_summary_dataframe.empty
    ):
        return pd.DataFrame(
            columns=[
                "corresponding_activities",
                "split_status",
                "interval_count",
                "total_gain",
            ]
        )

    combos = waterfall_summary_dataframe.groupby(
        ["corresponding_activities", "split_status"],
        as_index=False,
    ).agg(
        interval_count=("interval_count", "sum"),
        total_gain=("total_gain", "sum"),
    )

    return combos.sort_values(
        "total_gain", ascending=False
    ).head(top_n)


# =========================================================
# 商品表現排行（供文字摘要與PDF共用）
# =========================================================

def compute_product_ranking(
    unit_overview_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    依商品彙總活動單位數、淨增益合計、實際總營收、
    策略分類分布與風險檔數，依淨增益合計由高到低排序。
    """

    working = unit_overview_dataframe.copy()
    working["策略分類"] = compute_strategy_category(working)
    working["is_risky"] = compute_risk_mask(working)
    working["total_actual_revenue"] = (
        compute_actual_revenue_total(working)
    )

    ranking = working.groupby(
        ["product_id", "product_name"], as_index=False
    ).agg(
        unit_count=("unit_code", "count"),
        net_gain_total=("net_revenue_effect_total", "sum"),
        total_actual_revenue=("total_actual_revenue", "sum"),
        continue_count=(
            "策略分類", lambda s: int((s == "建議延續").sum())
        ),
        observe_count=(
            "策略分類", lambda s: int((s == "持續觀察").sum())
        ),
        review_count=(
            "策略分類", lambda s: int((s == "建議檢討").sum())
        ),
        risk_count=("is_risky", "sum"),
    )

    return ranking.sort_values(
        "net_gain_total", ascending=False
    ).reset_index(drop=True)


# =========================================================
# 主管策略摘要文字（新方法論版）
# =========================================================

def build_activity_unit_strategy_text(
    unit_overview_dataframe: pd.DataFrame,
    waterfall_summary_dataframe: pd.DataFrame,
) -> str:
    """
    產生「主管策略摘要」文字（活動單位分析新方法論版），
    取代舊版依活動前後平均值比較產生的 strategy_report_text。

    格式沿用既有 Markdown 慣例（# 標題、- 條列、一般段落），
    與 src/report_generator.py 現有的文字解析邏輯相容。
    """

    unit_overview = prepare_unit_overview_for_display(
        unit_overview_dataframe
    )
    unit_overview["策略分類"] = compute_strategy_category(
        unit_overview
    )
    unit_overview["is_risky"] = compute_risk_mask(unit_overview)
    unit_overview["資料信心"] = compute_confidence_label(
        unit_overview
    )
    unit_overview["total_actual_revenue"] = (
        compute_actual_revenue_total(unit_overview)
    )

    total_units = len(unit_overview)
    product_count = unit_overview["product_id"].nunique()
    total_gmv = unit_overview["total_actual_revenue"].sum()
    net_gmv = unit_overview["net_revenue_effect_total"].sum()

    continue_count = int(
        (unit_overview["策略分類"] == "建議延續").sum()
    )
    observe_count = int(
        (unit_overview["策略分類"] == "持續觀察").sum()
    )
    review_count = int(
        (unit_overview["策略分類"] == "建議檢討").sum()
    )

    lines: list[str] = []

    lines.append("# 整體概況")
    lines.append(
        f"共完成 {total_units} 個活動單位分析，涵蓋 "
        f"{product_count} 項商品。以「活動單位」為顆粒度、"
        f"相對同月安靜期基準計算，活動期間總營收（GMV）達 "
        f"${total_gmv:,.0f} 元，扣除基準後的淨增益達 "
        f"${net_gmv:,.0f} 元。"
    )
    lines.append(
        f"其中 {continue_count} 個單位（"
        f"{continue_count / total_units:.0%}）淨增益達全體中位數"
        f"以上，建議延續；{observe_count} 個（"
        f"{observe_count / total_units:.0%}）雖為正向但未達中位數，"
        f"建議持續觀察；{review_count} 個（"
        f"{review_count / total_units:.0%}）淨增益為負，建議檢討。"
    )

    # -----------------------------------------------------
    # 商品表現排名
    # -----------------------------------------------------

    ranking = compute_product_ranking(unit_overview)

    if not ranking.empty:
        lines.append("")
        lines.append("# 商品表現排名")

        best_product = ranking.iloc[0]
        worst_product = ranking.iloc[-1]

        most_consistent = ranking.loc[
            (
                ranking["continue_count"]
                / ranking["unit_count"]
            ).idxmax()
        ]

        lines.append(
            f"- {best_product['product_name']} "
            f"淨增益合計全站最高（"
            f"${best_product['net_gain_total']:,.0f} 元），"
            f"共 {int(best_product['unit_count'])} 個活動單位，"
            f"其中 {int(best_product['continue_count'])} 個建議延續、"
            f"{int(best_product['review_count'])} 個建議檢討"
            + (
                f"，另有 {int(best_product['risk_count'])} 個"
                "毛利侵蝕風險單位"
                if best_product["risk_count"] > 0
                else ""
            )
            + "。"
        )

        if most_consistent["product_id"] != best_product["product_id"]:
            consistency_rate = (
                most_consistent["continue_count"]
                / most_consistent["unit_count"]
            )
            lines.append(
                f"- {most_consistent['product_name']} "
                f"表現最穩定：{int(most_consistent['unit_count'])} "
                f"個活動單位中有 {int(most_consistent['continue_count'])} 個"
                f"（{consistency_rate:.0%}）建議延續"
                + (
                    "，未偵測到毛利侵蝕風險"
                    if most_consistent["risk_count"] == 0
                    else ""
                )
                + "。"
            )

        weakest_rate = (
            worst_product["continue_count"]
            / worst_product["unit_count"]
        )

        lines.append(
            f"- {worst_product['product_name']} 表現最弱："
            f"{int(worst_product['unit_count'])} 個單位中僅 "
            f"{int(worst_product['continue_count'])} 個"
            f"（{weakest_rate:.0%}）建議延續，淨增益合計僅 "
            f"${worst_product['net_gain_total']:,.0f} 元，"
            "建議檢討此商品的活動設計或商品本身在活動期間的吸引力。"
        )

    # -----------------------------------------------------
    # 最佳與最差活動單位
    # -----------------------------------------------------

    valid_units = unit_overview.dropna(
        subset=["net_revenue_effect_per_day"]
    )

    if not valid_units.empty:
        lines.append("")
        lines.append("# 活動單位成效重點")

        best_unit = valid_units.sort_values(
            "net_revenue_effect_per_day", ascending=False
        ).iloc[0]

        worst_unit = valid_units.sort_values(
            "net_revenue_effect_per_day", ascending=True
        ).iloc[0]

        lines.append(
            f"- 表現最佳：{best_unit['product_name']}・"
            f"{best_unit['unit_code']}"
            f"（{best_unit['corresponding_activities_label']}），"
            f"淨增益達 ${best_unit['net_revenue_effect_per_day']:,.0f} 元/日。"
        )
        lines.append(
            f"- 表現較差：{worst_unit['product_name']}・"
            f"{worst_unit['unit_code']}"
            f"（{worst_unit['corresponding_activities_label']}），"
            f"淨增益 ${worst_unit['net_revenue_effect_per_day']:,.0f} 元/日。"
        )

    # -----------------------------------------------------
    # 折扣深度洞察
    # -----------------------------------------------------

    bracket_stats = compute_discount_bracket_stats(unit_overview)

    if not bracket_stats.empty:
        lines.append("")
        lines.append("# 折扣深度洞察")

        best_bracket = bracket_stats.loc[
            bracket_stats["avg_net_effect"].idxmax()
        ]

        lines.append(
            f"折扣率落在「{best_bracket['discount_bracket']}」"
            f"區間的活動單位平均淨增益最高（"
            f"${best_bracket['avg_net_effect']:,.0f} 元/日，"
            f"共 {int(best_bracket['unit_count'])} 檔）。"
        )

        deepest_bracket = bracket_stats.iloc[-1]

        if (
            deepest_bracket["discount_bracket"]
            != best_bracket["discount_bracket"]
            and deepest_bracket["avg_net_effect"]
            < best_bracket["avg_net_effect"]
        ):
            lines.append(
                "折扣拉深到「"
                f"{deepest_bracket['discount_bracket']}」"
                "時，平均淨增益反而降至 "
                f"${deepest_bracket['avg_net_effect']:,.0f} 元/日"
                f"（{int(deepest_bracket['unit_count'])} 檔），"
                "深折扣沒有帶來對應的營收增幅，可能只是單純讓出毛利，"
                "建議下一輪優先測試較淺的折扣深度，"
                "深折扣檔期可考慮改用贈品或平台幣加碼取代直接降價。"
            )

    # -----------------------------------------------------
    # 疊加活動組合表現
    # -----------------------------------------------------

    # 這裡要在「全部組合」裡各自找出可拆分／不可拆分的最高者，
    # 不能只從整體前5名（compute_top_activity_combos）裡挑，
    # 否則可能因為某一類全部被擠出前5名而找不到代表案例。
    all_combos = compute_top_activity_combos(
        waterfall_summary_dataframe,
        top_n=len(waterfall_summary_dataframe)
        if waterfall_summary_dataframe is not None
        else 0,
    )

    if not all_combos.empty:
        lines.append("")
        lines.append("# 疊加活動組合表現")

        splittable_combos = all_combos[
            all_combos["split_status"] == "可拆分"
        ]

        unsplittable_combos = all_combos[
            all_combos["split_status"] != "可拆分"
        ]

        if not splittable_combos.empty:
            top_splittable = splittable_combos.iloc[0]

            lines.append(
                f"- 單一活動中，「{top_splittable['corresponding_activities']}」"
                f"貢獻最高可歸因淨增益（"
                f"${top_splittable['total_gain']:,.0f} 元，"
                f"{int(top_splittable['interval_count'])} 個區間，"
                "效果可乾淨拆分）。"
            )

        if not unsplittable_combos.empty:
            top_unsplittable = unsplittable_combos.iloc[0]
            activity_count = len(
                top_unsplittable["corresponding_activities"].split(
                    "、"
                )
            )

            lines.append(
                f"- 疊加活動中，「{top_unsplittable['corresponding_activities']}」"
                f"貢獻最高（${top_unsplittable['total_gain']:,.0f} 元），"
                f"但因同時疊加 {activity_count} 種活動機制，"
                "效果無法拆分歸因到單一活動，建議日後測試時盡量減少"
                "同時疊加的活動數，才能確認真正的營收驅動力。"
            )

    # -----------------------------------------------------
    # 風險提醒
    # -----------------------------------------------------

    risk_rows = unit_overview[
        unit_overview["is_risky"]
    ].sort_values("net_revenue_effect_per_day")

    lines.append("")
    lines.append("# 風險提醒")

    if risk_rows.empty:
        lines.append("目前沒有偵測到明顯的毛利侵蝕風險。")
    else:
        lines.append(
            f"{len(risk_rows)} 個活動單位出現毛利侵蝕風險"
            "（降價效應大於量增效應）："
        )

        for _, row in risk_rows.iterrows():
            discount_text = (
                f"{row['discount_rate']:.0%}"
                if pd.notna(row["discount_rate"])
                else "折扣率不明"
            )

            lines.append(
                f"- {row['product_name']}・{row['unit_code']}："
                f"售價降至 ${row['unit_avg_price']:,.0f} 元"
                f"（原價 ${row['baseline_price']:,.0f} 元，"
                f"折{discount_text}），"
                f"淨損 ${abs(row['net_revenue_effect_per_day']):,.0f} 元。"
            )

        lines.append(
            "建議下檔縮減折扣，或改以贈品吸引轉換。"
        )

    # -----------------------------------------------------
    # 資料信心與判讀限制
    # -----------------------------------------------------

    lines.append("")
    lines.append("# 資料信心與判讀限制")

    high_confidence_count = int(
        (unit_overview["資料信心"] == "較高").sum()
    )
    low_confidence_count = int(
        (unit_overview["資料信心"] == "較低").sum()
    )

    lines.append(
        f"{total_units} 個活動單位中，{high_confidence_count} 個"
        f"（{high_confidence_count / total_units:.0%}）樣本天數足夠、"
        "且未使用代理牌價估計，資料信心較高；"
        f"{low_confidence_count} 個（"
        f"{low_confidence_count / total_units:.0%}）涵蓋天數較短、"
        "配對比對樣本量小，或使用了代理牌價，資料信心較低，"
        "判讀時應更保守。"
    )
    lines.append(
        "- 以上數字為觀察性分析，非隨機實驗結果，"
        "活動期間銷量變化不直接等同活動造成的因果效果。"
    )
    lines.append(
        "- 淨增益已扣除同月安靜期基準，但尚未納入實際成本、"
        "退貨與平台抽成，不能直接視為毛利或淨利潤。"
    )

    return "\n".join(lines)


# =========================================================
# 分析總覽首屏摘要
# =========================================================

def build_executive_brief_summary(
    unit_overview_dataframe: pd.DataFrame,
) -> dict:
    """
    彙整成分析總覽首屏用的精簡摘要：一句話摘要、四個 KPI 計數，
    加上一張 AI 洞察卡要用的 finding/reason/action/confidence。

    完全複用既有的策略分類／風險判斷／色彩分類邏輯
    （compute_strategy_category／compute_risk_mask／
    prepare_unit_overview_for_display 產生的 color_category），
    不重新定義任何規則，只是為了首屏而重新包裝呈現方式。

    「不可分離」（color_category）對應母子活動組合或疊加多個
    活動、瀑布法尚未拆分的活動單位，即摘要句裡「不適合直接
    歸因」的活動數。
    """

    unit_overview = prepare_unit_overview_for_display(
        unit_overview_dataframe
    )
    unit_overview["策略分類"] = compute_strategy_category(
        unit_overview
    )
    unit_overview["is_risky"] = compute_risk_mask(unit_overview)
    unit_overview["資料信心"] = compute_confidence_label(
        unit_overview
    )

    total_units = len(unit_overview)
    continue_count = int(
        (unit_overview["策略分類"] == "建議延續").sum()
    )
    review_count = int(
        (unit_overview["策略分類"] == "建議檢討").sum()
    )
    risk_count = int(unit_overview["is_risky"].sum())
    unclear_count = int(
        (unit_overview["color_category"] == "不可分離").sum()
    )

    headline_text = (
        f"本期共辨識 {total_units} 個活動單位，"
        f"其中 {continue_count} 個值得優先延續、"
        f"{review_count} 個需要檢討，"
        f"另有 {unclear_count} 個因疊加多個活動而不適合直接歸因。"
    )

    risk_rows = unit_overview[
        unit_overview["is_risky"]
    ].dropna(subset=["net_revenue_effect_per_day"])

    continue_rows = unit_overview[
        unit_overview["策略分類"] == "建議延續"
    ].dropna(subset=["net_revenue_effect_per_day"])

    top_risk_row = (
        risk_rows.sort_values("net_revenue_effect_per_day").iloc[0]
        if not risk_rows.empty
        else None
    )

    top_opportunity_row = (
        continue_rows.sort_values(
            "net_revenue_effect_per_day", ascending=False
        ).iloc[0]
        if not continue_rows.empty
        else None
    )

    headline_row = (
        top_risk_row
        if top_risk_row is not None
        else top_opportunity_row
    )

    if top_risk_row is not None:
        insight_finding = (
            f"本期最需要留意的是「{top_risk_row['product_name']}」"
            f"的 {top_risk_row['unit_code']}"
            f"（{top_risk_row['corresponding_activities_label']}）"
            "活動組合，降價效應大於量增效應，屬於毛利侵蝕風險，"
            "淨損約 "
            f"{format_signed_currency(top_risk_row['net_revenue_effect_per_day'])}"
            "/日。"
        )
        insight_reason = (
            "毛利侵蝕風險存在時優先顯示風險單位，"
            "否則顯示淨增益最高的建議延續單位。"
        )
    elif top_opportunity_row is not None:
        insight_finding = (
            f"本期表現最佳的是「{top_opportunity_row['product_name']}」"
            f"的 {top_opportunity_row['unit_code']}"
            f"（{top_opportunity_row['corresponding_activities_label']}）"
            "活動組合，淨營收效應達全體中位數以上，約 "
            f"{format_signed_currency(top_opportunity_row['net_revenue_effect_per_day'])}"
            "/日。"
        )
        insight_reason = (
            "目前沒有偵測到毛利侵蝕風險，"
            "顯示淨增益最高的建議延續單位。"
        )
    else:
        insight_finding = "目前沒有足夠的活動單位資料可產生建議。"
        insight_reason = "尚未有可用的淨營收效應資料。"

    insight_action = (
        "建議前往「AI 策略中心」查看決策佇列與個別化建議，"
        "或使用「情境模擬」測試不同價格與贈品組合。"
    )

    insight_confidence = (
        headline_row["資料信心"]
        if headline_row is not None
        else "較低"
    )

    return {
        "total_units": total_units,
        "continue_count": continue_count,
        "review_count": review_count,
        "risk_count": risk_count,
        "unclear_count": unclear_count,
        "headline_text": headline_text,
        "insight_finding": insight_finding,
        "insight_reason": insight_reason,
        "insight_action": insight_action,
        "insight_confidence": insight_confidence,
    }
