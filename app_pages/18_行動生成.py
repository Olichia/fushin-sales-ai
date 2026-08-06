from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.action_generator import (
    AUDIENCE_OPTIONS,
    CHANNEL_OPTIONS,
    LENGTH_OPTIONS,
    TONE_OPTIONS,
    build_unit_action_evidence,
    build_whatif_action_evidence,
    generate_action_content,
)
from src.insight_cards import render_evidence_sections
from src.session_helpers import (
    get_action_generation_history,
    initialize_session_state,
    record_action_feedback,
)
from src.unit_overview_helpers import (
    compute_confidence_label,
    compute_strategy_category,
    prepare_unit_overview_for_display,
)

initialize_session_state()

st.markdown(
    """
    <div class="step-label">ACTION GENERATOR</div>
    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>行動生成</h1>
    </div>
    <p class="product-page-description">
        同一份策略洞察可切換成 B2C 消費者行銷或 B2B 商務溝通。
        B2C 只使用可公開的商品優惠；B2B 才能引用完整試算與內部證據。
    </p>
    """,
    unsafe_allow_html=True,
)


def dataframe_ready(dataframe) -> bool:
    return isinstance(dataframe, pd.DataFrame) and not dataframe.empty


unit_overview_raw = st.session_state.get("activity_unit_overview_dataframe")
unit_source_ready = bool(
    st.session_state.get("unit_analysis_completed", False)
) and dataframe_ready(unit_overview_raw)

whatif_scenario_results = st.session_state.get("whatif_last_scenario_results")
whatif_scenario_inputs = st.session_state.get("whatif_last_scenario_inputs")
whatif_source_ready = bool(whatif_scenario_results)

if not unit_source_ready and not whatif_source_ready:
    st.warning(
        "目前沒有可用資料。請先完成活動單位分析，或到情境模擬執行一次試算。"
    )
    st.stop()

st.subheader("選擇生成依據")
source_options = []
if unit_source_ready:
    source_options.append("已完成活動（活動單位分析）")
if whatif_source_ready:
    source_options.append("情境模擬方案（尚未執行的假設情境）")

selected_source = (
    st.radio("資料來源", source_options, horizontal=True)
    if len(source_options) > 1
    else source_options[0]
)

evidence = None

if selected_source == "已完成活動（活動單位分析）":
    unit_overview = prepare_unit_overview_for_display(unit_overview_raw)
    unit_overview["策略分類"] = compute_strategy_category(unit_overview)
    unit_overview["資料信心"] = compute_confidence_label(unit_overview)

    def format_unit_option(row_index: int) -> str:
        row = unit_overview.loc[row_index]
        activities_text = row["corresponding_activities_label"] or "安靜期"
        return f"{row['product_name']}｜{row['unit_code']}（{activities_text}）"

    selected_unit_index = st.selectbox(
        "選擇活動單位",
        options=list(unit_overview.index),
        format_func=format_unit_option,
    )
    selected_unit_row = unit_overview.loc[selected_unit_index]

    pairing_raw = st.session_state.get("activity_waterfall_pairing_dataframe")
    unit_price_raw = st.session_state.get("activity_unit_price_dataframe")
    activity_calendar_dataframe = st.session_state.get("activity_calendar_dataframe")

    pairing_columns = [
        "activity_type", "product_id", "target_unit", "split_status",
        "candidate_units", "net_gain_per_day", "net_gain_total",
        "target_unit_days", "remainder_corresponding_activities",
    ]
    pairing_table = pairing_raw.copy() if dataframe_ready(pairing_raw) else pd.DataFrame(columns=pairing_columns)
    if not pairing_table.empty:
        pairing_table["product_id"] = pairing_table["product_id"].astype(str).str.strip()

    if dataframe_ready(unit_price_raw):
        unit_price_table = unit_price_raw.copy()
        unit_price_table["product_id"] = unit_price_table["product_id"].astype(str).str.strip()
    else:
        unit_price_table = pd.DataFrame(columns=["unit_code", "product_id", "activity_tag", "gift", "bonus_campaign_text"])

    mechanism_text_lookup = {}
    for row in unit_price_table.itertuples():
        text_parts = [
            str(part) for part in [
                getattr(row, "activity_tag", None),
                getattr(row, "gift", None),
                getattr(row, "bonus_campaign_text", None),
            ]
            if part and pd.notna(part) and str(part).strip()
        ]
        if text_parts:
            mechanism_text_lookup[(row.product_id, row.unit_code)] = "、".join(dict.fromkeys(text_parts))

    unit_pairing_rows = pairing_table[
        (pairing_table["product_id"] == selected_unit_row["product_id"])
        & (pairing_table["target_unit"] == selected_unit_row["unit_code"])
    ]
    mechanism_text = mechanism_text_lookup.get(
        (selected_unit_row["product_id"], selected_unit_row["unit_code"]), ""
    )
    strategy_category = unit_overview.loc[selected_unit_index, "策略分類"]

    evidence = build_unit_action_evidence(
        unit_row=selected_unit_row,
        pairing_rows=unit_pairing_rows,
        unit_overview=unit_overview,
        mechanism_text=mechanism_text,
        strategy_category=strategy_category,
        activity_calendar_dataframe=activity_calendar_dataframe,
    )

else:
    product_name = st.session_state.get("whatif_last_product_name") or "此商品"
    scenario_label_map = {result.label: result for result in whatif_scenario_results}
    selected_scenario_label = st.selectbox(
        "選擇情境模擬方案",
        options=list(scenario_label_map.keys()),
    )
    selected_scenario_result = scenario_label_map[selected_scenario_label]

    scenario_input = None
    if whatif_scenario_inputs:
        input_map = {item.label: item for item in whatif_scenario_inputs}
        scenario_input = input_map.get(selected_scenario_label)

    evidence = build_whatif_action_evidence(
        scenario_result=selected_scenario_result,
        product_name=product_name,
        scenario_input=scenario_input,
    )

if evidence is not None:
    st.divider()
    st.subheader("本次生成依據")
    with st.container(border=True):
        render_evidence_sections(evidence["sections"])

    st.divider()
    st.subheader("生成設定")

    selected_audience = st.segmented_control(
        "溝通對象",
        options=AUDIENCE_OPTIONS,
        default=AUDIENCE_OPTIONS[0],
        help=(
            "B2C 只會使用可公開商品優惠；B2B 可引用完整試算、成本與限制。"
        ),
    )

    public_offer = dict(evidence.get("public_offer") or {})

    if selected_audience == "B2C 消費者行銷":
        st.info(
            "請確認下列資訊會公開給消費者。沒有提供的內容，AI 不會自行補充。"
        )
        c1, c2 = st.columns(2)
        with c1:
            public_offer["product_name"] = st.text_input(
                "商品名稱＊",
                value=str(public_offer.get("product_name") or ""),
            )
            public_offer["original_price"] = st.number_input(
                "原價（選填）",
                min_value=0.0,
                value=float(public_offer.get("original_price") or 0.0),
                step=10.0,
            )
            public_offer["activity_price"] = st.number_input(
                "活動價（選填）",
                min_value=0.0,
                value=float(public_offer.get("activity_price") or 0.0),
                step=10.0,
            )
            public_offer["gift_name"] = st.text_input(
                "商品贈品（選填）",
                value=str(public_offer.get("gift_name") or ""),
                placeholder="例如：雙耳湯鍋",
            )
        with c2:
            public_offer["activity_period"] = st.text_input(
                "活動期間（選填）",
                value=str(public_offer.get("activity_period") or ""),
                placeholder="例如：3/7–3/12",
            )
            public_offer["selling_point"] = st.text_area(
                "商品賣點（建議填寫）",
                value=str(public_offer.get("selling_point") or ""),
                placeholder="例如：8 人份容量、IH 加熱、操作簡單",
                height=90,
            )
            public_offer["platform_offer"] = st.text_input(
                "已確認平台優惠（選填）",
                value=str(public_offer.get("platform_offer") or ""),
                placeholder="僅填已確認規則，不推估效益",
            )
            public_offer["cta"] = st.text_input(
                "行動呼籲",
                value=str(public_offer.get("cta") or "立即查看活動詳情"),
            )

        st.caption(
            "B2C 最終文案不會出現預估營收、淨效益、贈品成本、平台抽成或內部試算限制。"
        )

    setting_col1, setting_col2, setting_col3 = st.columns(3)
    with setting_col1:
        selected_channel = st.segmented_control("管道", CHANNEL_OPTIONS, default=CHANNEL_OPTIONS[0])
    with setting_col2:
        selected_tone = st.segmented_control("語氣", TONE_OPTIONS, default=TONE_OPTIONS[0])
    with setting_col3:
        selected_length = st.segmented_control("長度", LENGTH_OPTIONS, default=LENGTH_OPTIONS[1])

    disabled = not (selected_audience and selected_channel and selected_tone and selected_length)
    if selected_audience == "B2C 消費者行銷" and not str(public_offer.get("product_name") or "").strip():
        disabled = True

    if st.button("生成行動內容", type="primary", use_container_width=True, disabled=disabled):
        with st.spinner("正在生成內容……"):
            content, is_fallback = generate_action_content(
                evidence_text=evidence["evidence_text"],
                sections=evidence["sections"],
                channel=selected_channel,
                tone=selected_tone,
                length=selected_length,
                audience_type=selected_audience,
                public_offer=public_offer,
            )

        st.session_state["action_generation_last_result"] = {
            "source_type": evidence["source_type"],
            "source_label": evidence["source_label"],
            "audience_type": selected_audience,
            "channel": selected_channel,
            "tone": selected_tone,
            "length": selected_length,
            "content": content,
            "is_fallback": is_fallback,
        }

    last_result = st.session_state.get("action_generation_last_result")
    if last_result and last_result.get("source_label") == evidence["source_label"]:
        st.divider()
        st.subheader("生成內容")
        st.caption("⚙ 示範備援內容" if last_result.get("is_fallback") else "✨ AI 生成內容")

        edited_content = st.text_area(
            "可直接修改後再採用",
            value=last_result["content"],
            height=280,
            key=f"action_content_editor_{last_result['source_label']}_{last_result.get('audience_type')}_{last_result.get('channel')}",
        )

        st.code(edited_content, language=None, wrap_lines=True)
        st.caption("可使用上方文字框編輯；下方程式框右上角可快速複製。")

        f1, f2, f3 = st.columns(3)
        outcome_clicked = None
        with f1:
            if st.button("採用", use_container_width=True):
                outcome_clicked = "採用"
        with f2:
            if st.button("修改後採用", use_container_width=True):
                outcome_clicked = "修改後採用"
        with f3:
            if st.button("不採用", use_container_width=True):
                outcome_clicked = "不採用"

        if outcome_clicked:
            record_action_feedback({
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "source_type": last_result["source_type"],
                "source_label": last_result["source_label"],
                "audience_type": last_result.get("audience_type", ""),
                "channel": last_result["channel"],
                "tone": last_result["tone"],
                "length": last_result.get("length", ""),
                "original_content": last_result["content"],
                "content": edited_content,
                "is_fallback": last_result["is_fallback"],
                "outcome": outcome_clicked,
            })
            st.success(f"已記錄：{outcome_clicked}")

st.divider()
st.subheader("生成紀錄")
history = get_action_generation_history()

if not history:
    st.info("尚無生成紀錄。")
else:
    history_dataframe = pd.DataFrame(history)
    display_columns = [
        col for col in [
            "generated_at", "source_type", "source_label", "audience_type",
            "channel", "tone", "outcome", "is_fallback",
        ] if col in history_dataframe.columns
    ]
    st.dataframe(
        history_dataframe[display_columns].rename(columns={
            "generated_at": "時間",
            "source_type": "來源類型",
            "source_label": "來源",
            "audience_type": "溝通對象",
            "channel": "管道",
            "tone": "語氣",
            "outcome": "採用結果",
            "is_fallback": "為備援內容",
        }),
        use_container_width=True,
        hide_index=True,
    )

    history_csv = history_dataframe.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "下載生成紀錄",
        data=history_csv,
        file_name="action_generation_history.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption("生成內容屬於決策輔助；實際發送前仍須人工確認價格、活動期間與優惠規則。")
