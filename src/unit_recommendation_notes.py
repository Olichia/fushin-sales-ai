from __future__ import annotations

import pandas as pd


# =========================================================
# 個別化建議文字
#
# 從 PR「feature/strategy-recommendation-rules」移植過來的
# 概念：檔期優惠重疊時，不是只給一句「不能完全歸因」的警語，
# 而是先試著用瀑布法配對比較拆出數字，拆不出來才退回警語。
#
# 跟舊版 src/analysis_pipeline.py 的
# build_attribution_note()／build_personalized_recommendation()
# 不同，這裡讀的是新方法論（src/activity_unit_analysis.py）
# 算出來的 unit_overview／waterfall_pairing_table，
# 完全不依賴活動前後 N 天比較法的欄位。
# =========================================================

def format_signed_currency(value: object) -> str:
    """將數字格式化為帶正負號的金額文字；缺值時回傳說明文字。"""

    if pd.isna(value):
        return "無法估算"

    return f"{float(value):+,.0f} 元"


def build_unit_attribution_note(
    unit_row: pd.Series,
    pairing_rows: pd.DataFrame,
) -> str:
    """
    依瀑布法配對比較結果，逐一說明疊加活動中每個活動的獨立貢獻。

    找得到「扣掉這個活動後組合相同」的真實對照期間時，
    直接引用配對比較拆出的數字；找不到對照期間時，
    誠實標示暫時無法拆分，並附上整體效果供參考。
    """

    if pairing_rows.empty:
        net_effect = unit_row.get("net_revenue_effect_per_day")

        return (
            "本活動單位沒有瀑布法配對比較資料，"
            "僅能提供整體效果：相對安靜期基準淨營收效應約 "
            f"{format_signed_currency(net_effect)}/日。"
        )

    lines: list[str] = []

    for _, pairing_row in pairing_rows.iterrows():
        activity_type = pairing_row.get("activity_type", "此活動")
        split_status = pairing_row.get("split_status")
        net_gain_per_day = pairing_row.get("net_gain_per_day")

        if split_status == "可拆分":
            candidate_units = pairing_row.get("candidate_units")
            net_gain_total = pairing_row.get("net_gain_total")
            target_days = pairing_row.get("target_unit_days")

            total_text = (
                f"（{int(target_days)} 天約 "
                f"{format_signed_currency(net_gain_total)}）"
                if pd.notna(target_days)
                else ""
            )

            lines.append(
                f"「{activity_type}」：已透過瀑布法配對比較，"
                f"用同商品同月份「{candidate_units}」的期間當對照，"
                "估算獨立貢獻約 "
                f"{format_signed_currency(net_gain_per_day)}/日"
                f"{total_text}。"
            )

        else:
            remainder = pairing_row.get(
                "remainder_corresponding_activities",
                "其他活動",
            )

            lines.append(
                f"「{activity_type}」：同商品同月份找不到"
                f"「{remainder}」的對照期間，暫時無法拆出獨立貢獻，"
                "僅能提供整體效果：約 "
                f"{format_signed_currency(net_gain_per_day)}/日。"
            )

    return "".join(lines)


def build_unit_history_note(
    unit_row: pd.Series,
    unit_overview: pd.DataFrame,
) -> str:
    """
    比較這個活動單位跟同商品其他活動單位的歷史淨營收效應。

    問的是跟舊版 build_product_history_context() 同樣的問題
    （這次比這個商品平常表現好還是差），
    只是比較基準從提升率（%）換成淨營收效應（元），
    跟新引擎其他頁面的敘事框架一致。
    """

    product_id = unit_row.get("product_id")
    unit_code = unit_row.get("unit_code")

    history = unit_overview[
        (unit_overview["product_id"] == product_id)
        & (unit_overview["unit_code"] != unit_code)
    ]

    history = history.dropna(subset=["net_revenue_effect_per_day"])

    if history.empty:
        return "同商品目前沒有其他可比較的活動單位。"

    median_effect = history["net_revenue_effect_per_day"].median()
    current_effect = unit_row.get("net_revenue_effect_per_day")

    if pd.isna(current_effect):
        return (
            f"同商品另有 {len(history)} 個可比較的活動單位，"
            f"淨營收效應中位數 {format_signed_currency(median_effect)}/日，"
            "本次淨營收效應暫時無法計算。"
        )

    difference = float(current_effect) - float(median_effect)
    direction = "高" if difference >= 0 else "低"

    return (
        f"同商品另有 {len(history)} 個可比較的活動單位，"
        f"淨營收效應中位數 {format_signed_currency(median_effect)}/日，"
        f"本次較中位數{direction} "
        f"{format_signed_currency(abs(difference))}/日。"
    )


def build_unit_mechanism_plan(mechanism_text: str) -> str:
    """
    依活動機制關鍵字，提出下一檔可執行的單一變因測試建議。

    對應舊版 build_mechanism_test_plan()，規則不變，
    只是輸入文字改讀新引擎 unit_price_table 的
    activity_tag／gift／bonus_campaign_text。
    """

    text = mechanism_text or ""

    if any(keyword in text for keyword in ["限搶", "限時"]):
        return (
            "保留商品與價格，僅測試一個限搶時段或限量門檻，"
            "逐時追蹤曝光、下單與售罄時間。"
        )

    if any(keyword in text for keyword in ["加碼", "贈", "贈品"]):
        return (
            "固定曝光與價格，只測試贈品內容或滿額門檻其中一項，"
            "追蹤贈品兌換率、轉換率與每筆贈品成本。"
        )

    if any(keyword in text for keyword in ["包套", "組合"]):
        return (
            "固定主商品價格，只調整一個組合品或組合價，"
            "追蹤組合滲透率、客單價與連帶購買率。"
        )

    if any(keyword in text for keyword in ["折", "券", "降價"]):
        return (
            "固定流量來源，只測試一個折扣或券門檻，"
            "同時追蹤實付價、轉換率與淨營收效應。"
        )

    return (
        "維持商品、價格與渠道不變，每次只調整曝光、活動天數"
        "或優惠門檻其中一項，避免多變因造成無法歸因。"
    )


def build_unit_personalized_recommendation_sections(
    unit_row: pd.Series,
    pairing_rows: pd.DataFrame,
    unit_overview: pd.DataFrame,
    mechanism_text: str,
    strategy_category: str,
) -> list[tuple[str, str]]:
    """
    組成四段式個別化建議的 (標籤, 內容) 清單：
    【績效診斷】【檔期歸因】【建議決策】【下一檔執行】。

    段落結構沿用舊版 build_personalized_recommendation()，
    但資料來源、指標與框架全部換成新引擎的活動單位分析結果。
    回傳結構化清單（而不是單一字串），方便呼叫端各自決定排版
    （例如每個標籤後方內容要靠左對齊的 hanging indent 版面）。
    """

    product_name = unit_row.get("product_name") or "此商品"
    unit_code = unit_row.get("unit_code", "")
    activities_label = (
        unit_row.get("corresponding_activities_label") or "無"
    )
    days = unit_row.get("days")
    net_effect = unit_row.get("net_revenue_effect_per_day")

    days_text = (
        f"{int(days)} 天" if pd.notna(days) else "此期間"
    )

    history_note = build_unit_history_note(unit_row, unit_overview)
    attribution_note = build_unit_attribution_note(
        unit_row, pairing_rows
    )
    mechanism_plan = build_unit_mechanism_plan(mechanism_text)

    diagnosis = (
        f"「{product_name}」活動單位 {unit_code}"
        f"（對應活動：{activities_label}）執行 {days_text}，"
        f"淨營收效應約 {format_signed_currency(net_effect)}/日；"
        f"{history_note}"
    )

    if strategy_category == "建議延續":
        decision = (
            "成效達建議延續標準，可考慮延續此組合，"
            "並測試擴大曝光或增加備貨"
        )
    elif strategy_category == "建議檢討":
        decision = (
            "淨營收效應為負，不建議直接延續原方案，"
            "應先檢查價格、曝光與商品適配"
        )
    else:
        decision = (
            "淨營收效應為正但未達整體中位數，"
            "建議持續觀察後續表現再決定是否放大"
        )

    return [
        ("【績效診斷】", diagnosis),
        ("【檔期歸因】", attribution_note),
        ("【建議決策】", f"{decision}。"),
        ("【下一檔執行】", mechanism_plan),
    ]


def build_unit_personalized_recommendation(
    unit_row: pd.Series,
    pairing_rows: pd.DataFrame,
    unit_overview: pd.DataFrame,
    mechanism_text: str,
    strategy_category: str,
) -> str:
    """
    組成四段式個別化建議純文字，各段以空行分隔。

    需要各段落分開排版（例如靠左對齊）時，
    改用 build_unit_personalized_recommendation_sections()。
    """

    sections = build_unit_personalized_recommendation_sections(
        unit_row=unit_row,
        pairing_rows=pairing_rows,
        unit_overview=unit_overview,
        mechanism_text=mechanism_text,
        strategy_category=strategy_category,
    )

    return "\n\n".join(
        f"{label}{text}" for label, text in sections
    )
