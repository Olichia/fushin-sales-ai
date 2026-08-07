from __future__ import annotations

from typing import Any

import pandas as pd

from src.unit_overview_helpers import (
    compute_actual_revenue_total,
    compute_confidence_label,
    compute_risk_mask,
    compute_strategy_category,
    prepare_unit_overview_for_display,
)


def prepare_ai_strategy_data(
    unit_overview_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """整理 AI 策略中心所需的衍生欄位。"""

    strategy = prepare_unit_overview_for_display(
        unit_overview_dataframe
    )
    strategy["strategy_category"] = (
        compute_strategy_category(strategy)
    )
    strategy["confidence_label"] = (
        compute_confidence_label(strategy)
    )
    strategy["is_risky"] = compute_risk_mask(strategy)
    strategy["total_actual_revenue"] = (
        compute_actual_revenue_total(strategy)
    )
    return strategy


def _clean_text(value: Any, fallback: str = "未命名") -> str:
    if value is None or pd.isna(value):
        return fallback

    text = str(value).strip()
    return text or fallback


def _number(value: Any, fallback: float = 0.0) -> float:
    numeric = pd.to_numeric(value, errors="coerce")
    return float(numeric) if pd.notna(numeric) else fallback


def _evidence_text(row: pd.Series) -> str:
    net_effect = _number(row.get("net_revenue_effect_per_day"))
    days = _number(row.get("days"))
    discount_rate = pd.to_numeric(
        row.get("discount_rate"), errors="coerce"
    )
    activity = _clean_text(
        row.get("corresponding_activities_label"),
        "未標記活動組合",
    )
    confidence = _clean_text(
        row.get("confidence_label"), "待確認"
    )

    discount_text = (
        f"{float(discount_rate):.1%}"
        if pd.notna(discount_rate)
        else "無法計算"
    )

    return (
        f"淨增益/日 {net_effect:+,.0f}；"
        f"觀察 {days:,.0f} 天；折扣率 {discount_text}；"
        f"資料信心 {confidence}；活動：{activity}"
    )


def _recommendation_for_row(row: pd.Series) -> tuple[str, str]:
    category = _clean_text(row.get("strategy_category"), "持續觀察")
    is_risky = bool(row.get("is_risky", False))
    color_category = _clean_text(row.get("color_category"), "")

    if is_risky:
        return (
            "優先檢討",
            "先縮小折扣或改用贈品方案，下一檔保留對照組驗證量增是否足以抵銷降價影響。",
        )

    if color_category == "不可分離":
        return (
            "拆分測試",
            "將疊加活動錯開執行，分別保留單一機制與對照組，確認真正有效的活動來源。",
        )

    if category == "建議延續":
        return (
            "建議延續",
            "保留目前有效機制，先在相似商品進行小規模複製測試，再依結果決定是否擴大。",
        )

    if category == "建議檢討":
        return (
            "調整後重測",
            "不要直接延續原方案；先檢查曝光、商品吸引力與優惠設計，再以較小範圍重新測試。",
        )

    return (
        "持續觀察",
        "目前訊號不足以直接擴大，建議延長觀察或補足樣本後再做下一步決策。",
    )


def _queue_record(row: pd.Series) -> dict[str, Any]:
    status, action = _recommendation_for_row(row)
    product_name = _clean_text(row.get("product_name"))
    product_id = _clean_text(row.get("product_id"), "-")
    unit_code = _clean_text(row.get("unit_code"), "-")
    net_effect = _number(row.get("net_revenue_effect_per_day"))

    return {
        "product_name": product_name,
        "product_id": product_id,
        "unit_code": unit_code,
        "title": f"{product_name}｜{unit_code}",
        "status": status,
        "strategy_category": _clean_text(
            row.get("strategy_category"), "持續觀察"
        ),
        "net_effect_per_day": net_effect,
        "confidence": _clean_text(
            row.get("confidence_label"), "待確認"
        ),
        "evidence": _evidence_text(row),
        "action": action,
        "prompt": (
            f"請深入解讀 {product_name}（商品編號 {product_id}、"
            f"活動單位 {unit_code}）的下一期策略。"
            f"目前資料證據為：{_evidence_text(row)}。"
            "請區分資料觀察、合理推測與可執行建議，並提出替代方案。"
        ),
    }


def build_decision_queue(
    strategy_dataframe: pd.DataFrame,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """依風險、延續機會與待觀察訊號建立精簡決策佇列。"""

    if strategy_dataframe.empty or limit <= 0:
        return []

    selected_indices: list[Any] = []

    def append_indices(indices: list[Any]) -> None:
        for index in indices:
            if index not in selected_indices:
                selected_indices.append(index)
            if len(selected_indices) >= limit:
                return

    risk_rows = strategy_dataframe[
        strategy_dataframe["is_risky"]
        | (strategy_dataframe["strategy_category"] == "建議檢討")
    ].sort_values(
        "net_revenue_effect_per_day",
        ascending=True,
        na_position="last",
    )
    append_indices(risk_rows.index.tolist()[:2])

    opportunity_rows = strategy_dataframe[
        strategy_dataframe["strategy_category"] == "建議延續"
    ].sort_values(
        "net_revenue_effect_per_day",
        ascending=False,
        na_position="last",
    )
    append_indices(opportunity_rows.index.tolist()[:2])

    observe_rows = strategy_dataframe[
        strategy_dataframe["strategy_category"] == "持續觀察"
    ].sort_values(
        ["confidence_label", "net_revenue_effect_per_day"],
        ascending=[True, False],
        na_position="last",
    )
    append_indices(observe_rows.index.tolist())

    remaining = strategy_dataframe.assign(
        _impact=strategy_dataframe[
            "net_revenue_effect_per_day"
        ].abs()
    ).sort_values("_impact", ascending=False)
    append_indices(remaining.index.tolist())

    return [
        _queue_record(strategy_dataframe.loc[index])
        for index in selected_indices[:limit]
    ]


def build_executive_brief(
    strategy_dataframe: pd.DataFrame,
) -> dict[str, Any]:
    """建立首頁第一張 AI 決策摘要，所有敘述皆取自既有分析。"""

    if strategy_dataframe.empty:
        return {
            "finding": "目前沒有可判讀的活動單位。",
            "reason": "尚未取得完整活動單位分析結果。",
            "action": "請先完成 03 執行完整分析。",
            "evidence": "目前資料筆數為 0。",
            "confidence": "低",
            "tone": "neutral",
        }

    urgent = strategy_dataframe[
        strategy_dataframe["is_risky"]
        | (strategy_dataframe["strategy_category"] == "建議檢討")
    ].sort_values(
        "net_revenue_effect_per_day",
        ascending=True,
        na_position="last",
    )

    if not urgent.empty:
        row = urgent.iloc[0]
        product_name = _clean_text(row.get("product_name"))
        net_effect = _number(row.get("net_revenue_effect_per_day"))
        return {
            "finding": (
                f"優先檢討 {product_name}：目前是決策佇列中"
                f"最需要處理的風險訊號，淨增益/日為 {net_effect:+,.0f}。"
            ),
            "reason": (
                "系統依淨增益、降價效應與量增效應排序，"
                "此活動不適合在沒有進一步驗證下直接延續。"
            ),
            "action": _recommendation_for_row(row)[1],
            "evidence": _evidence_text(row),
            "confidence": _clean_text(
                row.get("confidence_label"), "待確認"
            ),
            "tone": "risk",
        }

    opportunity = strategy_dataframe.sort_values(
        "net_revenue_effect_per_day",
        ascending=False,
        na_position="last",
    ).iloc[0]
    product_name = _clean_text(opportunity.get("product_name"))
    net_effect = _number(
        opportunity.get("net_revenue_effect_per_day")
    )
    return {
        "finding": (
            f"優先放大 {product_name} 的有效機制："
            f"目前淨增益/日為 {net_effect:+,.0f}。"
        ),
        "reason": (
            "目前沒有偵測到需要優先處理的負向風險，"
            "因此先從淨增益較高的活動單位建立下一期測試。"
        ),
        "action": _recommendation_for_row(opportunity)[1],
        "evidence": _evidence_text(opportunity),
        "confidence": _clean_text(
            opportunity.get("confidence_label"), "待確認"
        ),
        "tone": "good",
    }


def build_next_period_plan(
    strategy_dataframe: pd.DataFrame,
) -> list[dict[str, str]]:
    """以目前策略分類數量建立可追溯的三步下一期規劃。"""

    continue_count = int(
        (strategy_dataframe["strategy_category"] == "建議延續").sum()
    )
    observe_count = int(
        (strategy_dataframe["strategy_category"] == "持續觀察").sum()
    )
    review_count = int(
        (strategy_dataframe["strategy_category"] == "建議檢討").sum()
    )
    risk_count = int(strategy_dataframe["is_risky"].sum())

    return [
        {
            "step": "01",
            "title": "保留有效機制",
            "description": (
                f"從 {continue_count} 個建議延續活動中挑選資料信心較高者，"
                "在相似商品做小規模複製測試。"
            ),
            "evidence": f"資料佐證：建議延續 {continue_count} 個活動單位。",
        },
        {
            "step": "02",
            "title": "控制風險與拆分變因",
            "description": (
                f"優先處理 {review_count} 個建議檢討活動；"
                f"其中 {risk_count} 個有降價效應高於量增效應的風險。"
            ),
            "evidence": (
                f"資料佐證：建議檢討 {review_count} 個、"
                f"風險活動 {risk_count} 個。"
            ),
        },
        {
            "step": "03",
            "title": "補足樣本再決策",
            "description": (
                f"對 {observe_count} 個持續觀察活動延長觀察，"
                "並固定主要變因與對照組後再評估是否擴大。"
            ),
            "evidence": f"資料佐證：持續觀察 {observe_count} 個活動單位。",
        },
    ]
