from pathlib import Path
import sys
from datetime import datetime

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
    build_whatif_summary_short,
    compute_whatif_scenarios,
    estimate_avg_discount_rate_from_history,
    estimate_baseline_price_from_history,
    estimate_daily_sales_from_history,
    estimate_sales_uplift_rate_from_history,
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


def build_scenario_identity(
    product_id: str,
    label: str,
    scenario_input: WhatIfScenarioInput,
) -> str:
    """
    依商品＋方案格＋這次試算實際用的設定值組出識別碼。

    設定值完全相同時識別碼也相同，用來讓「重複按同一顆採用
    按鈕」去重成一筆；只要有任何一個設定不同（換方案、換商品、
    或改了輸入後重新模擬採用），識別碼就會不同，各自成為報告
    上獨立的一筆，彼此並存不覆蓋。
    """

    fields = (
        str(product_id),
        label,
        round(scenario_input.baseline_price, 2),
        round(scenario_input.activity_price, 2),
        int(scenario_input.days),
        round(scenario_input.estimated_daily_sales, 2),
        bool(scenario_input.has_gift),
        round(scenario_input.gift_cost_per_unit, 2),
        bool(scenario_input.platform_overlap),
    )

    return "|".join(str(field) for field in fields)


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

        default_avg_discount_rate = (
            estimate_avg_discount_rate_from_history(
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
                round(
                    default_baseline_price
                    * (1 - default_avg_discount_rate),
                    0,
                )
                if default_baseline_price
                else 0.0
            ),
            step=10.0,
            help=(
                "預設取「安靜期基準價 ×（1－同商品過往活動平均折扣率）」，"
                "可自行調整。"
            ),
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
            "預估日均銷量（無活動基準）",
            min_value=0.0,
            value=float(round(default_daily_sales, 1)),
            step=1.0,
            help=(
                "指您認為『即使不辦活動』也應達到的日均銷量目標，"
                "用來算「無活動預期營收」。活動期間的實際預估銷量"
                "會依歷史同折扣區間的平均提升率另外換算，"
                "顯示在模擬結果的「預估活動銷量」。"
                "預設取同商品過往活動單位的日均銷量中位數，可自行調整。"
            ),
        )

        run_simulation = st.button(
            "執行模擬",
            type="primary",
            use_container_width=True,
        )

    if run_simulation:
        # 把這次按下「執行模擬」當下的設定值存成快照；下方模擬
        # 結果只讀這份快照，不會因為使用者之後繼續調整左側欄位
        # 就跟著即時變動，要再按一次「執行模擬」才會更新。
        st.session_state["whatif_has_run"] = True
        st.session_state["whatif_snapshot"] = {
            "product_label": selected_product_label,
            "product_id": selected_product_id,
            "baseline_price": baseline_price,
            "activity_price": activity_price,
            "has_gift": has_gift,
            "gift_cost_per_unit": gift_cost_per_unit,
            "platform_overlap": platform_overlap,
            "days": int(days),
            "estimated_daily_sales": estimated_daily_sales,
        }


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
        snapshot = st.session_state["whatif_snapshot"]

        selected_product_label = snapshot["product_label"]
        selected_product_id = snapshot["product_id"]
        baseline_price = snapshot["baseline_price"]
        activity_price = snapshot["activity_price"]
        has_gift = snapshot["has_gift"]
        gift_cost_per_unit = snapshot["gift_cost_per_unit"]
        platform_overlap = snapshot["platform_overlap"]
        days = snapshot["days"]
        estimated_daily_sales = snapshot["estimated_daily_sales"]

        deeper_discount_price = round(activity_price * 0.9, 0)

        scenario_price_plan = [
            ("方案 A・無贈品", activity_price, False, 0.0),
            (
                "方案 B・您的方案",
                activity_price,
                has_gift,
                gift_cost_per_unit,
            ),
            (
                "方案 C・再降價 10%",
                deeper_discount_price,
                False,
                0.0,
            ),
        ]

        scenario_inputs = []
        uplift_notes: dict[str, str] = {}

        for label, price, gift_flag, gift_cost in scenario_price_plan:
            scenario_discount_rate = (
                1 - (price / baseline_price) if baseline_price else None
            )

            uplift_rate, uplift_note = (
                estimate_sales_uplift_rate_from_history(
                    unit_overview,
                    selected_product_id,
                    scenario_discount_rate,
                )
            )

            estimated_activity_sales = (
                estimated_daily_sales * (1 + uplift_rate)
            )

            uplift_notes[label] = uplift_note

            scenario_inputs.append(
                WhatIfScenarioInput(
                    label=label,
                    activity_price=price,
                    baseline_price=baseline_price,
                    estimated_daily_sales=estimated_daily_sales,
                    estimated_activity_sales=(
                        estimated_activity_sales
                    ),
                    days=int(days),
                    has_gift=gift_flag,
                    gift_cost_per_unit=gift_cost,
                    platform_overlap=platform_overlap,
                )
            )

        scenario_results = compute_whatif_scenarios(
            scenario_inputs
        )
        best_scenario = select_best_scenario(scenario_results)

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

        adopted_scenarios = st.session_state.get(
            "adopted_whatif_scenarios", []
        )

        scenario_columns = st.columns(3)

        for column, scenario_input, result, (
            title,
            badge_text,
            badge_tone,
        ) in zip(
            scenario_columns,
            scenario_inputs,
            scenario_results,
            scenario_card_meta,
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
                        "預估活動銷量",
                        f"{result.estimated_activity_sales:,.1f}",
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

                scenario_identity = build_scenario_identity(
                    selected_product_id, result.label, scenario_input
                )

                is_adopted = any(
                    entry.get("entry_id") == scenario_identity
                    for entry in adopted_scenarios
                )

                render_scenario_card(
                    title=title,
                    badge_text=badge_text,
                    badge_tone=badge_tone,
                    rows=rows,
                    is_best=is_best,
                    is_adopted=is_adopted,
                )

                adopt_clicked = st.button(
                    "📌 已採用，點擊更新採用時間"
                    if is_adopted
                    else "採用此方案",
                    key=f"adopt_scenario_{scenario_identity}",
                    type="secondary" if is_adopted else "primary",
                    use_container_width=True,
                )

                if adopt_clicked:
                    setting_rows = [
                        ("商品", selected_product_label),
                        (
                            "安靜期基準價",
                            f"{scenario_input.baseline_price:,.0f} 元",
                        ),
                        (
                            "活動價",
                            f"{scenario_input.activity_price:,.0f} 元",
                        ),
                        ("活動天數", f"{scenario_input.days} 天"),
                        (
                            "預估日均銷量（無活動基準）",
                            f"{scenario_input.estimated_daily_sales:,.1f}",
                        ),
                        (
                            "搭配贈品",
                            (
                                f"是（{scenario_input.gift_cost_per_unit:,.0f} 元／件）"
                                if scenario_input.has_gift
                                else "否"
                            ),
                        ),
                        (
                            "同時搭配平台活動",
                            "是" if scenario_input.platform_overlap else "否",
                        ),
                    ]

                    pdf_rows = setting_rows + rows

                    new_entry = {
                        "entry_id": scenario_identity,
                        "product_id": selected_product_id,
                        "product_name": (
                            selected_product_label.rsplit("（", 1)[0]
                        ),
                        "title": title,
                        "badge_text": badge_text,
                        "rows": pdf_rows,
                        "ai_summary": summary_insight,
                        "ai_summary_short": build_whatif_summary_short(
                            scenario_results
                        ),
                        "adopted_at": datetime.now().strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                    }

                    # 同識別碼（商品＋方案＋全部設定值都相同）視為重複
                    # 點擊，覆蓋成一筆；識別碼不同（換商品、換方案、或
                    # 改了設定重新模擬）則並存，各自成為報告上獨立一筆。
                    # 只存在本次瀏覽器 session，不寫入資料庫，重新整理
                    # 後會清空。
                    st.session_state["adopted_whatif_scenarios"] = [
                        entry
                        for entry in adopted_scenarios
                        if entry.get("entry_id") != scenario_identity
                    ] + [new_entry]

                    st.toast(
                        f"已採用「{title}・{badge_text}」，"
                        "將加入主管報表匯出區塊。",
                        icon="✅",
                    )

                    st.rerun()

        st.write("")

        uplift_note_text = "；".join(
            f"{label}：{note}" for label, note in uplift_notes.items()
        )

        with st.expander("計算邏輯與方案說明", expanded=False):
            st.caption(
                "**計算邏輯**　折扣率＝1－活動價÷安靜期基準價；"
                "預估活動銷量＝預估日均銷量×（1＋歷史同折扣區間平均銷量提升率）；"
                "活動營收＝活動價×預估活動銷量×天數；"
                "無活動預期營收＝安靜期基準價×預估日均銷量×天數；"
                "淨營收增益＝活動營收－無活動預期營收；"
                "簡化後淨效益＝淨營收增益－贈品成本"
                "（贈品成本＝贈品成本/件×預估活動銷量×天數）。"
            )

            st.caption(
                "**A／B／C 如何產出**　方案 B 為您輸入的條件；"
                "方案 A 在 B 的基礎上拿掉贈品；"
                "方案 C 在 B 的活動價再降 10% 且不含贈品；"
                "三者共用安靜期基準價、預估日均銷量與活動天數，"
                "只差折扣深度與是否贈品，方便同時比較"
                "「要不要送贈品」與「乾脆降更多價」。"
            )

            if uplift_note_text:
                st.caption(f"**本次換算依據**　{uplift_note_text}")

        if platform_overlap:
            st.caption(
                "⚠ 已勾選「同時搭配平台活動」，"
                "其疊加貢獻未計入以上試算。"
            )

        st.caption(
            "⚠ 此為情境試算，不是因果預測，非對這檔活動的預測；"
            "簡化後淨效益未納入實際成本、退貨與平台抽成，"
            "不能直接視為毛利或淨利潤。"
        )


adopted_scenarios_display = st.session_state.get(
    "adopted_whatif_scenarios", []
)

if adopted_scenarios_display:
    st.divider()

    with st.expander(
        f"📌 已採用方案（{len(adopted_scenarios_display)}）"
        "－將加入主管報表匯出",
        expanded=False,
    ):
        for entry in adopted_scenarios_display:
            entry_col, remove_col = st.columns([5, 1])

            with entry_col:
                st.markdown(
                    f"**{entry['product_name']}（{entry['product_id']}）** "
                    f"－ {entry['title']}・{entry['badge_text']}　"
                    f"採用於 {entry['adopted_at']}"
                )

            with remove_col:
                if st.button(
                    "移除",
                    key=f"remove_adopted_{entry['entry_id']}",
                    use_container_width=True,
                ):
                    st.session_state["adopted_whatif_scenarios"] = [
                        item
                        for item in adopted_scenarios_display
                        if item["entry_id"] != entry["entry_id"]
                    ]

                    st.rerun()


st.divider()

st.caption(
    "情境模擬使用跟「活動洞察」「策略中心」相同的折扣率與淨營收效應"
    "計算方式，方便直接比較。若要看歷史活動的真實成效，"
    "請前往「活動洞察」查看。"
)
