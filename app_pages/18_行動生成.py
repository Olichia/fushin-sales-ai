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

# =========================================================
# Page-only UI styling
# =========================================================
# 只調整本頁視覺，不改動資料來源、生成函式、session state 或採用紀錄邏輯。
st.markdown(
    """
    <style>
    .action-page-shell {
        margin-bottom: 1rem;
    }

    .action-kicker {
        color: #B75D20;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        margin-bottom: 0.35rem;
    }

    .action-title-row {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        margin-bottom: 0.25rem;
    }

    .action-title-mark {
        width: 6px;
        height: 31px;
        border-radius: 4px;
        background: linear-gradient(
            180deg,
            #F97316 0%,
            #F04C64 52%,
            #6D4BD1 100%
        );
        flex: 0 0 auto;
    }

    .action-title-row h1 {
        color: #202124;
        font-size: 2rem;
        line-height: 1.2;
        margin: 0;
        font-weight: 750;
        letter-spacing: -0.02em;
    }

    .action-lead {
        color: #667085;
        font-size: 0.98rem;
        line-height: 1.7;
        max-width: 850px;
        margin: 0.2rem 0 0;
    }

    .action-section-heading {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        margin: 0 0 0.65rem;
    }

    .action-section-heading h2 {
        color: #292624;
        font-size: 1.05rem;
        margin: 0;
        font-weight: 720;
    }

    .action-section-heading span {
        color: #8A8580;
        font-size: 0.78rem;
    }

    .action-summary-card {
        border: 1px solid #E7E2DC;
        border-left: 4px solid #E87524;
        background: #FFFFFF;
        border-radius: 10px;
        padding: 0.95rem 1.05rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 2px rgba(32, 33, 36, 0.04);
    }

    .action-summary-eyebrow {
        color: #8B817A;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        margin-bottom: 0.22rem;
    }

    .action-summary-title {
        color: #272321;
        font-size: 1rem;
        font-weight: 720;
        margin-bottom: 0.25rem;
    }

    .action-summary-meta {
        color: #6F6A66;
        font-size: 0.83rem;
        line-height: 1.55;
    }

    .action-panel-label {
        color: #3F3A36;
        font-size: 0.9rem;
        font-weight: 720;
        margin-bottom: 0.2rem;
    }

    .action-panel-note {
        color: #87817C;
        font-size: 0.78rem;
        line-height: 1.55;
        margin-bottom: 0.8rem;
    }

    .action-preview-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        border-bottom: 1px solid #EEE9E4;
        padding-bottom: 0.75rem;
        margin-bottom: 0.7rem;
    }

    .action-preview-title {
        color: #292522;
        font-size: 1.03rem;
        font-weight: 730;
    }

    .action-preview-meta {
        color: #7D7772;
        font-size: 0.78rem;
        margin-top: 0.18rem;
    }

    .action-status-pill {
        display: inline-block;
        border: 1px solid #E8DED5;
        border-radius: 999px;
        padding: 0.24rem 0.58rem;
        color: #8E4A1D;
        background: #FFF8F3;
        font-size: 0.72rem;
        white-space: nowrap;
    }

    .action-empty-preview {
        border: 1px dashed #D9D3CD;
        border-radius: 10px;
        background: #FBFAF8;
        color: #7B7671;
        min-height: 290px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 2rem;
        line-height: 1.7;
        margin-bottom: 0.75rem;
    }

    .action-record-summary {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: 0.25rem 0 0.8rem;
    }

    .action-record-chip {
        border: 1px solid #E7E2DC;
        border-radius: 999px;
        padding: 0.3rem 0.65rem;
        color: #66615D;
        background: #FFFFFF;
        font-size: 0.76rem;
    }

    /* 保留 Streamlit 元件本身，僅做輕量一致化。 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #E7E2DC;
        border-radius: 10px;
        box-shadow: 0 1px 2px rgba(32, 33, 36, 0.035);
    }

    div[data-testid="stSegmentedControl"] button {
        border-radius: 7px !important;
    }

    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        border-radius: 7px;
    }

    </style>

    <div class="action-page-shell">
        <div class="action-kicker">ACTION WORKSPACE</div>
        <div class="action-title-row">
            <div class="action-title-mark"></div>
            <h1>行動生成</h1>
        </div>
        <p class="action-lead">
            將活動洞察或情境試算轉成可直接使用的溝通內容。
            B2C 僅採用可公開優惠資訊；B2B 才會引用完整試算與內部證據。
        </p>
    </div>
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

st.markdown(
    """
    <div class="action-section-heading">
        <h2>選擇生成依據</h2>
        <span>先決定這次內容要引用哪一筆分析</span>
    </div>
    """,
    unsafe_allow_html=True,
)

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
        "activity_type",
        "product_id",
        "target_unit",
        "split_status",
        "candidate_units",
        "net_gain_per_day",
        "net_gain_total",
        "target_unit_days",
        "remainder_corresponding_activities",
    ]
    pairing_table = (
        pairing_raw.copy()
        if dataframe_ready(pairing_raw)
        else pd.DataFrame(columns=pairing_columns)
    )
    if not pairing_table.empty:
        pairing_table["product_id"] = (
            pairing_table["product_id"].astype(str).str.strip()
        )

    if dataframe_ready(unit_price_raw):
        unit_price_table = unit_price_raw.copy()
        unit_price_table["product_id"] = (
            unit_price_table["product_id"].astype(str).str.strip()
        )
    else:
        unit_price_table = pd.DataFrame(
            columns=[
                "unit_code",
                "product_id",
                "activity_tag",
                "gift",
                "bonus_campaign_text",
            ]
        )

    mechanism_text_lookup = {}
    for row in unit_price_table.itertuples():
        text_parts = [
            str(part)
            for part in [
                getattr(row, "activity_tag", None),
                getattr(row, "gift", None),
                getattr(row, "bonus_campaign_text", None),
            ]
            if part and pd.notna(part) and str(part).strip()
        ]
        if text_parts:
            mechanism_text_lookup[(row.product_id, row.unit_code)] = "、".join(
                dict.fromkeys(text_parts)
            )

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
    scenario_label_map = {
        result.label: result for result in whatif_scenario_results
    }
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
    st.markdown(
        f"""
        <div class="action-summary-card">
            <div class="action-summary-eyebrow">CURRENT SOURCE</div>
            <div class="action-summary-title">{evidence['source_label']}</div>
            <div class="action-summary-meta">
                來源類型：{evidence['source_type']}　｜　完整資料證據可於下方展開查看
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("查看完整判斷依據", expanded=False):
        render_evidence_sections(evidence["sections"])

    st.markdown("<div style='height:0.45rem'></div>", unsafe_allow_html=True)

    settings_column, preview_column = st.columns([0.39, 0.61], gap="large")

    with settings_column:
        with st.container(border=True):
            st.markdown(
                """
                <div class="action-panel-label">生成設定</div>
                <div class="action-panel-note">
                    先設定溝通對象，再選擇管道、語氣與內容長度。
                </div>
                """,
                unsafe_allow_html=True,
            )

            selected_audience = st.segmented_control(
                "溝通對象",
                options=AUDIENCE_OPTIONS,
                default=AUDIENCE_OPTIONS[0],
                help=(
                    "B2C 只會使用可公開商品優惠；"
                    "B2B 可引用完整試算、成本與限制。"
                ),
            )

            public_offer = dict(evidence.get("public_offer") or {})

            if selected_audience == "B2C 消費者行銷":
                st.caption(
                    "僅下列欄位會公開給消費者；未提供的資訊不會由 AI 自行補充。"
                )

                public_offer["product_name"] = st.text_input(
                    "商品名稱＊",
                    value=str(public_offer.get("product_name") or ""),
                )

                price_col1, price_col2 = st.columns(2)
                with price_col1:
                    public_offer["original_price"] = st.number_input(
                        "原價",
                        min_value=0.0,
                        value=float(public_offer.get("original_price") or 0.0),
                        step=10.0,
                    )
                with price_col2:
                    public_offer["activity_price"] = st.number_input(
                        "活動價",
                        min_value=0.0,
                        value=float(public_offer.get("activity_price") or 0.0),
                        step=10.0,
                    )

                public_offer["gift_name"] = st.text_input(
                    "商品贈品",
                    value=str(public_offer.get("gift_name") or ""),
                    placeholder="例如：雙耳湯鍋",
                )
                public_offer["activity_period"] = st.text_input(
                    "活動期間",
                    value=str(public_offer.get("activity_period") or ""),
                    placeholder="例如：3/7–3/12",
                )
                public_offer["selling_point"] = st.text_area(
                    "商品賣點",
                    value=str(public_offer.get("selling_point") or ""),
                    placeholder="例如：8 人份容量、IH 加熱、操作簡單",
                    height=86,
                )
                public_offer["platform_offer"] = st.text_input(
                    "已確認平台優惠",
                    value=str(public_offer.get("platform_offer") or ""),
                    placeholder="僅填已確認規則，不推估效益",
                )
                public_offer["cta"] = st.text_input(
                    "行動呼籲",
                    value=str(public_offer.get("cta") or "立即查看活動詳情"),
                )

                st.caption(
                    "B2C 不會揭露預估營收、淨效益、贈品成本、平台抽成或內部試算限制。"
                )

            selected_channel = st.segmented_control(
                "管道",
                CHANNEL_OPTIONS,
                default=CHANNEL_OPTIONS[0],
            )
            selected_tone = st.segmented_control(
                "語氣",
                TONE_OPTIONS,
                default=TONE_OPTIONS[0],
            )
            selected_length = st.segmented_control(
                "長度",
                LENGTH_OPTIONS,
                default=LENGTH_OPTIONS[1],
            )

            disabled = not (
                selected_audience
                and selected_channel
                and selected_tone
                and selected_length
            )
            if (
                selected_audience == "B2C 消費者行銷"
                and not str(public_offer.get("product_name") or "").strip()
            ):
                disabled = True

            generate_clicked = st.button(
                "生成行動內容",
                type="primary",
                use_container_width=True,
                disabled=disabled,
            )

    if generate_clicked:
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

    with preview_column:
        with st.container(border=True):
            if (
                last_result
                and last_result.get("source_label") == evidence["source_label"]
            ):
                result_type_text = (
                    "規則式備援"
                    if last_result.get("is_fallback")
                    else "AI 生成"
                )
                st.markdown(
                    f"""
                    <div class="action-preview-header">
                        <div>
                            <div class="action-preview-title">{last_result['channel']} 預覽</div>
                            <div class="action-preview-meta">
                                {last_result.get('audience_type', '')}｜
                                {last_result.get('tone', '')}｜
                                {last_result.get('length', '')}
                            </div>
                        </div>
                        <div class="action-status-pill">{result_type_text}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                edited_content = st.text_area(
                    "內容編輯區",
                    value=last_result["content"],
                    height=330,
                    key=(
                        "action_content_editor_"
                        f"{last_result['source_label']}_"
                        f"{last_result.get('audience_type')}_"
                        f"{last_result.get('channel')}"
                    ),
                    help="可直接修改內容，再選擇採用或修改後採用。",
                )

                st.code(edited_content, language=None, wrap_lines=True)
                st.caption("程式框右上角可快速複製；正式發送前請再次確認優惠條件。")

                feedback_col1, feedback_col2, feedback_col3 = st.columns(3)
                outcome_clicked = None
                with feedback_col1:
                    if st.button("採用", use_container_width=True):
                        outcome_clicked = "採用"
                with feedback_col2:
                    if st.button("修改後採用", use_container_width=True):
                        outcome_clicked = "修改後採用"
                with feedback_col3:
                    if st.button("不採用", use_container_width=True):
                        outcome_clicked = "不採用"

                if outcome_clicked:
                    record_action_feedback(
                        {
                            "generated_at": datetime.now().strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                            "source_type": last_result["source_type"],
                            "source_label": last_result["source_label"],
                            "audience_type": last_result.get(
                                "audience_type", ""
                            ),
                            "channel": last_result["channel"],
                            "tone": last_result["tone"],
                            "length": last_result.get("length", ""),
                            "original_content": last_result["content"],
                            "content": edited_content,
                            "is_fallback": last_result["is_fallback"],
                            "outcome": outcome_clicked,
                        }
                    )
                    st.success(f"已記錄：{outcome_clicked}")
            else:
                st.markdown(
                    """
                    <div class="action-preview-header">
                        <div>
                            <div class="action-preview-title">內容預覽</div>
                            <div class="action-preview-meta">完成左側設定後即可生成</div>
                        </div>
                        <div class="action-status-pill">尚未生成</div>
                    </div>
                    <div class="action-empty-preview">
                        生成結果會顯示在這裡。<br>
                        內容可直接編輯、複製，並紀錄採用結果。
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

st.markdown("<div style='height:0.65rem'></div>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="action-section-heading">
        <h2>生成紀錄</h2>
        <span>保留使用者採用、修改或不採用的結果</span>
    </div>
    """,
    unsafe_allow_html=True,
)

history = get_action_generation_history()

if not history:
    st.info("尚無生成紀錄。")
else:
    history_dataframe = pd.DataFrame(history)

    outcome_count = (
        history_dataframe["outcome"].value_counts()
        if "outcome" in history_dataframe.columns
        else pd.Series(dtype=int)
    )
    fallback_count = (
        int(history_dataframe["is_fallback"].fillna(False).sum())
        if "is_fallback" in history_dataframe.columns
        else 0
    )

    st.markdown(
        f"""
        <div class="action-record-summary">
            <div class="action-record-chip">共 {len(history_dataframe)} 筆</div>
            <div class="action-record-chip">採用 {int(outcome_count.get('採用', 0))} 筆</div>
            <div class="action-record-chip">修改後採用 {int(outcome_count.get('修改後採用', 0))} 筆</div>
            <div class="action-record-chip">不採用 {int(outcome_count.get('不採用', 0))} 筆</div>
            <div class="action-record-chip">備援內容 {fallback_count} 筆</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    display_columns = [
        col
        for col in [
            "generated_at",
            "source_type",
            "source_label",
            "audience_type",
            "channel",
            "tone",
            "outcome",
            "is_fallback",
        ]
        if col in history_dataframe.columns
    ]

    with st.expander("查看完整生成紀錄", expanded=False):
        st.dataframe(
            history_dataframe[display_columns].rename(
                columns={
                    "generated_at": "時間",
                    "source_type": "來源類型",
                    "source_label": "來源",
                    "audience_type": "溝通對象",
                    "channel": "管道",
                    "tone": "語氣",
                    "outcome": "採用結果",
                    "is_fallback": "為備援內容",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    history_csv = history_dataframe.to_csv(
        index=False,
        encoding="utf-8-sig",
    ).encode("utf-8-sig")
    st.download_button(
        "下載生成紀錄",
        data=history_csv,
        file_name="action_generation_history.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption(
    "生成內容屬於決策輔助；實際發送前仍須人工確認價格、活動期間與優惠規則。"
)