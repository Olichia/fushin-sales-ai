from pathlib import Path
import sys

import pandas as pd
import streamlit as st


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.insight_cards import render_ai_insight_card, render_scenario_card
from src.session_helpers import initialize_session_state
from src.unit_overview_helpers import prepare_unit_overview_for_display
from src.whatif_simulation import (
    WhatIfScenarioInput,
    build_whatif_summary_insight,
    compute_whatif_scenarios,
    estimate_baseline_price_from_history,
    estimate_daily_sales_from_history,
    select_best_scenario,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.markdown(
    """
    <div class="step-label">WHAT-IF SIMULATION</div>

    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>情境模擬</h1>
    </div>

    <p class="product-page-description">
        調整下一檔活動的價格與贈品條件，比較不同促銷組合的預估淨效益。
        這是規則式情境試算，不是預測模型；銷量假設來自歷史相似活動
        中位數或您輸入的數值，不是因果預測。
    </p>
    """,
    unsafe_allow_html=True,
)


def dataframe_ready(dataframe) -> bool:
    """判斷 DataFrame 是否存在且有資料。"""

    return (
        isinstance(dataframe, pd.DataFrame)
        and not dataframe.empty
    )


# =========================================================
# 取得既有資料
# =========================================================

unit_overview_raw = st.session_state.get(
    "activity_unit_overview_dataframe"
)

unit_analysis_completed = bool(
    st.session_state.get("unit_analysis_completed", False)
)

new_engine_ready = (
    unit_analysis_completed
    and dataframe_ready(unit_overview_raw)
)

if not new_engine_ready:
    st.warning(
        "尚未產生活動單位分析結果。"
        "請先於「03 執行完整分析」頁面完成分析"
        "（需先完成銷量與活動資料確認），才能帶入歷史資料試算。"
    )
    st.stop()

unit_overview = prepare_unit_overview_for_display(unit_overview_raw)


# =========================================================
# 方案條件
# =========================================================

st.subheader("方案條件")

product_options = (
    unit_overview[["product_id", "product_name"]]
    .drop_duplicates()
    .sort_values("product_id")
)

product_label_map = {
    f"{row.product_name}（{row.product_id}）": row.product_id
    for row in product_options.itertuples()
}

input_col, output_col = st.columns([1, 1.6], gap="large")

with input_col:
    with st.container(border=True):
        selected_product_label = st.selectbox(
            "商品",
            options=list(product_label_map.keys()),
        )
        selected_product_id = product_label_map[
            selected_product_label
        ]

        default_baseline_price = (
            estimate_baseline_price_from_history(
                unit_overview, selected_product_id
            )
            or 0.0
        )

        default_daily_sales = (
            estimate_daily_sales_from_history(
                unit_overview, selected_product_id
            )
            or 0.0
        )

        baseline_price = st.number_input(
            "安靜期基準價（元）",
            min_value=0.0,
            value=float(round(default_baseline_price, 0)),
            step=10.0,
            help="同商品過往活動單位的安靜期基準價中位數，可自行調整。",
        )

        activity_price = st.number_input(
            "活動價（元）",
            min_value=0.0,
            value=float(
                round(default_baseline_price * 0.9, 0)
                if default_baseline_price
                else 0.0
            ),
            step=10.0,
        )

        has_gift = st.checkbox("搭配贈品", value=True)

        gift_cost_per_unit = st.number_input(
            "贈品成本（元／件）",
            min_value=0.0,
            value=200.0,
            step=10.0,
            disabled=not has_gift,
        )

        platform_overlap = st.checkbox(
            "同時搭配平台活動",
            value=False,
            help=(
                "僅供紀錄與提醒，不會計入下方淨效益試算——"
                "平台活動疊加對營收的實際貢獻，"
                "需要瀑布法配對比較才能拆分，"
                "此處故意不假裝能算出來。"
            ),
        )

        days = st.number_input(
            "活動天數",
            min_value=1,
            value=7,
            step=1,
        )

        estimated_daily_sales = st.number_input(
            "預估日均銷量",
            min_value=0.0,
            value=float(round(default_daily_sales, 1)),
            step=1.0,
            help="預設取同商品過往活動單位的日均銷量中位數，可自行調整。",
        )

        run_simulation = st.button(
            "執行模擬",
            type="primary",
            use_container_width=True,
        )

    if run_simulation:
        st.session_state["whatif_has_run"] = True


# =========================================================
# 模擬結果
# =========================================================

with output_col:
    if not st.session_state.get("whatif_has_run"):
        st.info(
            "輸入方案條件後按「執行模擬」，"
            "系統會自動比較「無贈品」「您的方案」「再降價」三種情境。"
        )

    else:
        deeper_discount_price = round(activity_price * 0.9, 0)

        scenario_inputs = [
            WhatIfScenarioInput(
                label="方案 A・無贈品",
                activity_price=activity_price,
                baseline_price=baseline_price,
                estimated_daily_sales=estimated_daily_sales,
                days=int(days),
                has_gift=False,
                gift_cost_per_unit=0.0,
                platform_overlap=platform_overlap,
            ),
            WhatIfScenarioInput(
                label="方案 B・您的方案",
                activity_price=activity_price,
                baseline_price=baseline_price,
                estimated_daily_sales=estimated_daily_sales,
                days=int(days),
                has_gift=has_gift,
                gift_cost_per_unit=gift_cost_per_unit,
                platform_overlap=platform_overlap,
            ),
            WhatIfScenarioInput(
                label="方案 C・再降價 10%",
                activity_price=deeper_discount_price,
                baseline_price=baseline_price,
                estimated_daily_sales=estimated_daily_sales,
                days=int(days),
                has_gift=False,
                gift_cost_per_unit=0.0,
                platform_overlap=platform_overlap,
            ),
        ]

        scenario_results = compute_whatif_scenarios(
            scenario_inputs
        )
        best_scenario = select_best_scenario(scenario_results)

        # 暫存最近一次試算結果，供「行動生成」頁引用，
        # 不需要使用者重新輸入一次條件。
        st.session_state["whatif_last_scenario_results"] = (
            scenario_results
        )
        # 同時保存原始方案輸入，讓行動生成頁可帶入活動價、基準價等
        # 可公開欄位；不再只剩內部營收試算數字。
        st.session_state["whatif_last_scenario_inputs"] = (
            scenario_inputs
        )
        st.session_state["whatif_last_product_id"] = (
            selected_product_id
        )
        st.session_state["whatif_last_product_name"] = (
            selected_product_label.split("（")[0]
        )

        st.caption(
            "方案 A／C 由方案 B 的條件自動衍生：A 拿掉贈品、"
            "C 在活動價基礎上再降 10% 且不含贈品，"
            "方便同時比較「要不要送贈品」與「乾脆降更多價」。"
        )

        summary_insight = build_whatif_summary_insight(
            scenario_results
        )

        render_ai_insight_card(
            finding=summary_insight["finding"],
            reason=summary_insight["reason"],
            action=summary_insight["action"],
        )

        st.write("")

        scenario_card_meta = [
            ("方案 A", "無贈品", "neutral"),
            (
                "方案 B",
                "贈品組合" if has_gift else "無贈品",
                "good" if has_gift else "neutral",
            ),
            ("方案 C", "深折扣", "risk"),
        ]

        scenario_columns = st.columns(3)

        for column, result, (title, badge_text, badge_tone) in zip(
            scenario_columns, scenario_results, scenario_card_meta
        ):
            with column:
                is_best = (
                    best_scenario is not None
                    and result.label == best_scenario.label
                )

                rows = [
                    (
                        "折扣率",
                        (
                            f"{result.discount_rate:.1%}"
                            if result.discount_rate is not None
                            else "—"
                        ),
                    ),
                    (
                        "預估活動營收",
                        f"{result.estimated_activity_revenue:,.0f}",
                    ),
                    (
                        "無活動預期營收",
                        (
                            "{:,.0f}".format(
                                result.expected_revenue_without_activity
                            )
                        ),
                    ),
                    (
                        "淨營收增益",
                        f"{result.net_revenue_gain:+,.0f}",
                    ),
                    (
                        "贈品成本",
                        f"{result.total_gift_cost:,.0f}",
                    ),
                    (
                        "簡化後淨效益",
                        f"{result.simplified_net_benefit:+,.0f}",
                    ),
                ]

                render_scenario_card(
                    title=title,
                    badge_text=badge_text,
                    badge_tone=badge_tone,
                    rows=rows,
                    is_best=is_best,
                )

                if result.platform_overlap:
                    st.caption(
                        "⚠ 同時搭配平台活動（未計入試算）"
                    )

        st.warning(
            "⚠ 此為情境試算，不是因果預測；銷量假設來自歷史相似活動"
            "中位數或您輸入的數值。簡化後淨效益 ＝ 淨營收增益－贈品成本，"
            "未納入實際成本、退貨與平台抽成，不能直接視為毛利或淨利潤。"
        )

        st.info(
            "已保存本次試算結果，"
            "可前往「行動生成」頁選擇其中一個方案，"
            "改寫成電話話術、LINE/簡訊、Email 或拜訪提綱。"
        )


st.divider()

st.caption(
    "情境模擬使用跟「活動洞察」「策略中心」相同的折扣率與淨營收效應"
    "計算方式，方便直接比較。若要看歷史活動的真實成效，"
    "請前往「活動洞察」查看。"
)
