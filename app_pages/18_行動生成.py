from datetime import datetime
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


from src.action_generator import (
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


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.markdown(
    """
    <div class="step-label">ACTION GENERATOR</div>

    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>行動生成</h1>
    </div>

    <p class="product-page-description">
        選擇一個已完成的活動單位、或一個情境模擬方案，
        將既有分析結果改寫成可直接使用的電話話術、LINE/簡訊、
        Email 或拜訪提綱。生成內容只會引用畫面上顯示的真實資料，
        不會另外捏造商品、活動或數字。
    </p>
    """,
    unsafe_allow_html=True,
)


def dataframe_ready(dataframe) -> bool:
    """判斷 DataFrame 是否存在且有資料。"""

    return isinstance(dataframe, pd.DataFrame) and not dataframe.empty


# =========================================================
# 取得既有資料
# =========================================================

unit_overview_raw = st.session_state.get(
    "activity_unit_overview_dataframe"
)
unit_analysis_completed = bool(
    st.session_state.get("unit_analysis_completed", False)
)

unit_source_ready = (
    unit_analysis_completed and dataframe_ready(unit_overview_raw)
)

whatif_scenario_results = st.session_state.get(
    "whatif_last_scenario_results"
)
whatif_source_ready = bool(whatif_scenario_results)

if not unit_source_ready and not whatif_source_ready:
    st.warning(
        "目前沒有可用於生成行動內容的資料。"
        "請先完成「03 執行完整分析」產生活動單位分析結果，"
        "或前往「情境模擬」執行一次試算。"
    )
    st.stop()


# =========================================================
# 來源選擇
# =========================================================

st.subheader("選擇生成依據")

source_options = []

if unit_source_ready:
    source_options.append("已完成活動（活動單位分析）")

if whatif_source_ready:
    source_options.append("情境模擬方案（尚未執行的假設情境）")

if len(source_options) > 1:
    selected_source = st.radio(
        "資料來源",
        options=source_options,
        horizontal=True,
        help=(
            "「已完成活動」是已經發生、有真實銷量支持的活動單位分析結果；"
            "「情境模擬方案」是使用者輸入條件後的假設試算，"
            "尚未實際執行，兩者性質不同，生成內容會分別註明。"
        ),
    )
else:
    selected_source = source_options[0]
    st.caption(f"目前可用資料來源：{selected_source}")


evidence: dict[str, object] | None = None

# =========================================================
# 來源①：活動單位分析
# =========================================================

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

    pairing_raw = st.session_state.get(
        "activity_waterfall_pairing_dataframe"
    )
    unit_price_raw = st.session_state.get("activity_unit_price_dataframe")
    activity_calendar_dataframe = st.session_state.get(
        "activity_calendar_dataframe"
    )

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

    mechanism_text_lookup: dict[tuple, str] = {}

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
            mechanism_text_lookup[(row.product_id, row.unit_code)] = (
                "、".join(dict.fromkeys(text_parts))
            )

    unit_pairing_rows = pairing_table[
        (pairing_table["product_id"] == selected_unit_row["product_id"])
        & (pairing_table["target_unit"] == selected_unit_row["unit_code"])
    ]

    mechanism_text = mechanism_text_lookup.get(
        (
            selected_unit_row["product_id"],
            selected_unit_row["unit_code"],
        ),
        "",
    )

    strategy_category = unit_overview.loc[
        selected_unit_index, "策略分類"
    ]

    evidence = build_unit_action_evidence(
        unit_row=selected_unit_row,
        pairing_rows=unit_pairing_rows,
        unit_overview=unit_overview,
        mechanism_text=mechanism_text,
        strategy_category=strategy_category,
        activity_calendar_dataframe=activity_calendar_dataframe,
    )


# =========================================================
# 來源②：情境模擬
# =========================================================

elif selected_source == "情境模擬方案（尚未執行的假設情境）":
    product_name = (
        st.session_state.get("whatif_last_product_name") or "此商品"
    )

    scenario_label_map = {
        result.label: result for result in whatif_scenario_results
    }

    selected_scenario_label = st.selectbox(
        "選擇情境模擬方案",
        options=list(scenario_label_map.keys()),
    )

    selected_scenario_result = scenario_label_map[selected_scenario_label]

    evidence = build_whatif_action_evidence(
        scenario_result=selected_scenario_result,
        product_name=product_name,
    )


# =========================================================
# 顯示生成依據（證據鏈）
# =========================================================

if evidence is not None:
    st.divider()
    st.subheader("本次行動生成依據")

    st.caption(
        "以下內容全部來自系統既有分析結果，"
        "生成的行動內容只能引用這裡出現的商品、活動與數字。"
    )

    with st.container(border=True):
        render_evidence_sections(evidence["sections"])

    # =====================================================
    # 生成設定
    # =====================================================

    st.divider()
    st.subheader("生成設定")

    setting_col1, setting_col2, setting_col3 = st.columns(3)

    with setting_col1:
        selected_channel = st.segmented_control(
            "管道",
            options=CHANNEL_OPTIONS,
            default=CHANNEL_OPTIONS[0],
        )

    with setting_col2:
        selected_tone = st.segmented_control(
            "語氣",
            options=TONE_OPTIONS,
            default=TONE_OPTIONS[0],
        )

    with setting_col3:
        selected_length = st.segmented_control(
            "長度",
            options=LENGTH_OPTIONS,
            default=LENGTH_OPTIONS[1],
        )

    generate_clicked = st.button(
        "生成行動內容",
        type="primary",
        use_container_width=True,
        disabled=not (
            selected_channel and selected_tone and selected_length
        ),
    )

    if generate_clicked:
        with st.spinner("正在生成內容……"):
            content, is_fallback = generate_action_content(
                evidence_text=evidence["evidence_text"],
                sections=evidence["sections"],
                channel=selected_channel,
                tone=selected_tone,
                length=selected_length,
            )

        st.session_state["action_generation_last_result"] = {
            "source_type": evidence["source_type"],
            "source_label": evidence["source_label"],
            "channel": selected_channel,
            "tone": selected_tone,
            "content": content,
            "is_fallback": is_fallback,
        }

    # =====================================================
    # 顯示生成結果
    # =====================================================

    last_result = st.session_state.get("action_generation_last_result")

    if (
        last_result
        and last_result.get("source_label") == evidence["source_label"]
    ):
        st.divider()
        st.subheader("生成內容")

        if last_result.get("is_fallback"):
            st.caption("⚙ 示範備援內容（AI 服務暫時無法回應）")
        else:
            st.caption("✨ AI 生成內容")

        st.code(last_result["content"], language=None, wrap_lines=True)

        st.caption("點擊上方內容右上角圖示即可複製。")

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
                    "channel": last_result["channel"],
                    "tone": last_result["tone"],
                    "content": last_result["content"],
                    "is_fallback": last_result["is_fallback"],
                    "outcome": outcome_clicked,
                }
            )

            st.success(f"已記錄本次採用結果：{outcome_clicked}")


# =========================================================
# 生成紀錄
# =========================================================

st.divider()
st.subheader("生成紀錄")

history = get_action_generation_history()

if not history:
    st.info("尚無生成紀錄。生成內容並點選採用結果後會出現在這裡。")

else:
    history_dataframe = pd.DataFrame(history)[
        [
            "generated_at",
            "source_type",
            "source_label",
            "channel",
            "tone",
            "outcome",
            "is_fallback",
        ]
    ].rename(
        columns={
            "generated_at": "時間",
            "source_type": "來源類型",
            "source_label": "來源",
            "channel": "管道",
            "tone": "語氣",
            "outcome": "採用結果",
            "is_fallback": "為備援內容",
        }
    )

    st.dataframe(
        history_dataframe,
        use_container_width=True,
        hide_index=True,
    )

    history_csv = pd.DataFrame(history).to_csv(
        index=False, encoding="utf-8-sig"
    ).encode("utf-8-sig")

    st.download_button(
        "下載生成紀錄",
        data=history_csv,
        file_name="action_generation_history.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption(
    "生成內容屬於決策輔助，實際發送前仍建議人工檢查。"
)
