from pathlib import Path
import html
import sys

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.ai_advisor import (
    build_advisor_context,
    condense_structured_response,
    get_structured_advisor_answer,
)
from src.ai_strategy_center import (
    build_decision_queue,
    build_executive_brief,
    build_next_period_plan,
    prepare_ai_strategy_data,
)
from src.insight_cards import render_structured_advisor_card
from src.session_helpers import initialize_session_state


def safe_html(value: object) -> str:
    """將動態文字安全放入頁面卡片。"""

    return html.escape(str(value))


def format_money(value: object, signed: bool = False) -> str:
    numeric = pd.to_numeric(value, errors="coerce")

    if pd.isna(numeric):
        return "-"

    if signed:
        return f"{float(numeric):+,.0f}"

    return f"{float(numeric):,.0f}"


def confidence_class(label: str) -> str:
    return (
        "confidence-high"
        if label in {"高", "較高"}
        else "confidence-low"
    )


initialize_session_state()


st.markdown(
    """
    <style>
    .ai-center-hero {
        position: relative;
        overflow: hidden;
        margin-bottom: 1.1rem;
        padding: 1.45rem 1.55rem;
        background:
            radial-gradient(circle at 92% 15%, rgba(93, 169, 255, 0.22), transparent 33%),
            linear-gradient(135deg, var(--surface) 0%, var(--ai-accent-soft) 100%);
        border: 1px solid var(--ai-accent-border);
        border-radius: 18px;
        box-shadow: var(--shadow-md);
    }

    .ai-center-hero::after {
        content: "";
        position: absolute;
        width: 130px;
        height: 130px;
        right: -48px;
        bottom: -65px;
        border: 1px solid rgba(93, 169, 255, 0.32);
        border-radius: 50%;
    }

    .ai-center-kicker {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        margin-bottom: 0.55rem;
        color: var(--ai-accent-deep);
        font-size: 0.78rem;
        font-weight: 900;
        letter-spacing: 0.12em;
    }

    .ai-center-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--success);
        box-shadow: 0 0 0 5px rgba(51, 209, 122, 0.12);
    }

    .ai-center-title {
        margin: 0 0 0.45rem;
        color: var(--text-primary);
        font-size: clamp(1.9rem, 3vw, 2.7rem);
        font-weight: 900;
        letter-spacing: -0.035em;
    }

    .ai-center-subtitle {
        max-width: 920px;
        margin: 0;
        color: var(--text-secondary);
        font-size: 0.98rem;
        font-weight: 540;
        line-height: 1.75;
    }

    .ai-flow {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 1rem;
    }

    .ai-flow span {
        padding: 0.28rem 0.62rem;
        background: var(--surface);
        color: var(--text-secondary);
        border: 1px solid var(--border);
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 750;
    }

    .ai-flow span strong {
        color: var(--ai-accent-deep);
    }

    .ai-kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.85rem 0 1.15rem;
    }

    .ai-kpi-card {
        min-height: 112px;
        padding: 0.9rem 1rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        box-shadow: var(--shadow-sm);
    }

    .ai-kpi-label {
        color: var(--text-muted);
        font-size: 0.73rem;
        font-weight: 800;
        letter-spacing: 0.04em;
    }

    .ai-kpi-value {
        margin: 0.28rem 0 0.16rem;
        color: var(--text-primary);
        font-size: 1.55rem;
        font-weight: 900;
        font-variant-numeric: tabular-nums;
    }

    .ai-kpi-note {
        color: var(--text-secondary);
        font-size: 0.72rem;
        line-height: 1.45;
    }

    .ai-brief {
        margin: 0.3rem 0 0.7rem;
        padding: 1.15rem 1.25rem;
        background:
            linear-gradient(135deg, var(--ai-accent-soft), var(--surface) 58%);
        border: 1px solid var(--ai-accent-border);
        border-radius: 15px;
    }

    .ai-brief-risk {
        border-left: 5px solid var(--danger);
    }

    .ai-brief-good {
        border-left: 5px solid var(--success);
    }

    .ai-brief-neutral {
        border-left: 5px solid var(--ai-accent);
    }

    .ai-brief-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.7rem;
        margin-bottom: 0.7rem;
    }

    .ai-brief-tag {
        color: var(--ai-accent-deep);
        font-size: 0.76rem;
        font-weight: 900;
        letter-spacing: 0.06em;
    }

    .ai-confidence {
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 850;
    }

    .confidence-high {
        color: var(--success);
        background: rgba(51, 209, 122, 0.11);
        border: 1px solid rgba(51, 209, 122, 0.32);
    }

    .confidence-low {
        color: var(--warning);
        background: rgba(251, 191, 36, 0.11);
        border: 1px solid rgba(251, 191, 36, 0.32);
    }

    .ai-brief-finding {
        margin-bottom: 0.7rem;
        color: var(--text-primary);
        font-size: 1.08rem;
        font-weight: 850;
        line-height: 1.55;
    }

    .ai-brief-row {
        display: grid;
        grid-template-columns: 5rem 1fr;
        gap: 0.5rem;
        padding: 0.28rem 0;
        color: var(--text-secondary);
        font-size: 0.84rem;
        line-height: 1.55;
    }

    .ai-brief-row strong {
        color: var(--ai-accent-deep);
        font-weight: 850;
    }

    .decision-status {
        display: inline-block;
        margin-bottom: 0.32rem;
        padding: 0.18rem 0.5rem;
        color: var(--ai-accent-deep);
        background: var(--ai-accent-soft);
        border: 1px solid var(--ai-accent-border);
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 850;
    }

    .decision-title {
        color: var(--text-primary);
        font-size: 0.98rem;
        font-weight: 850;
    }

    .decision-action {
        margin-top: 0.35rem;
        color: var(--text-secondary);
        font-size: 0.8rem;
        line-height: 1.55;
    }

    .decision-evidence {
        margin-top: 0.5rem;
        padding-top: 0.48rem;
        color: var(--text-muted);
        border-top: 1px dashed var(--border-soft);
        font-size: 0.72rem;
        line-height: 1.5;
    }

    .plan-card {
        min-height: 168px;
        padding: 1rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        box-shadow: var(--shadow-sm);
    }

    .plan-step {
        color: var(--brand-orange);
        font-size: 0.72rem;
        font-weight: 900;
        letter-spacing: 0.1em;
    }

    .plan-title {
        margin: 0.35rem 0 0.5rem;
        color: var(--text-primary);
        font-size: 0.96rem;
        font-weight: 850;
    }

    .plan-description,
    .plan-evidence {
        color: var(--text-secondary);
        font-size: 0.78rem;
        line-height: 1.55;
    }

    .plan-evidence {
        margin-top: 0.5rem;
        color: var(--text-muted);
    }

    @media (max-width: 900px) {
        .ai-kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 560px) {
        .ai-kpi-grid {
            grid-template-columns: 1fr;
        }

        .ai-brief-row {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="ai-center-hero">
        <div class="ai-center-kicker">
            <span class="ai-center-pulse"></span>
            AI DECISION ASSISTANT · READY
        </div>
        <h1 class="ai-center-title">AI 策略中心</h1>
        <p class="ai-center-subtitle">
            將策略摘要、決策佇列與 AI 對話整合在同一頁。
            系統先從既有活動單位分析找出機會與風險，再提供可執行、
            可驗證且附資料佐證的下一期規劃。
        </p>
        <div class="ai-flow">
            <span><strong>01</strong> 發現 Detect</span>
            <span><strong>02</strong> 解釋 Explain</span>
            <span><strong>03</strong> 建議 Recommend</span>
            <span><strong>04</strong> 決策 Decide</span>
            <span><strong>05</strong> 驗證 Learn</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


unit_overview_raw = st.session_state.get(
    "activity_unit_overview_dataframe"
)
waterfall_summary_raw = st.session_state.get(
    "activity_waterfall_summary_dataframe"
)
unit_price_dataframe = st.session_state.get(
    "activity_unit_price_dataframe"
)
unit_analysis_completed = bool(
    st.session_state.get("unit_analysis_completed", False)
)

analysis_ready = (
    unit_analysis_completed
    and isinstance(unit_overview_raw, pd.DataFrame)
    and not unit_overview_raw.empty
    and isinstance(waterfall_summary_raw, pd.DataFrame)
    and not waterfall_summary_raw.empty
)


if not analysis_ready:
    st.warning(
        "AI 策略中心正在等待分析資料。請先完成「03 執行完整分析」，"
        "系統就會自動產生決策摘要、Decision Queue 與 AI 對話背景。"
    )
    st.stop()


strategy = prepare_ai_strategy_data(unit_overview_raw)
executive_brief = build_executive_brief(strategy)
decision_queue = build_decision_queue(strategy, limit=5)
next_period_plan = build_next_period_plan(strategy)

advisor_context = build_advisor_context(
    unit_overview_dataframe=unit_overview_raw,
    waterfall_summary_dataframe=waterfall_summary_raw,
    unit_price_dataframe=unit_price_dataframe,
)
st.session_state["ai_last_context"] = advisor_context


if not st.session_state.get("ai_chat_messages"):
    st.session_state["ai_chat_messages"] = [
        {
            "role": "assistant",
            "content": (
                "你好，我是 AI 策略中心的決策助理。\n\n"
                "你可以直接點選決策卡或快捷問題；我會根據目前的"
                "活動單位分析，說明發現、原因、行動、影響、"
                "資料信心與限制。"
            ),
        }
    ]


total_units = len(strategy)
continue_count = int(
    (strategy["strategy_category"] == "建議延續").sum()
)
review_count = int(
    (strategy["strategy_category"] == "建議檢討").sum()
)
risk_count = int(strategy["is_risky"].sum())
total_net_effect = strategy["net_revenue_effect_total"].sum(
    min_count=1
)


st.markdown(
    f"""
    <div class="ai-kpi-grid">
        <div class="ai-kpi-card">
            <div class="ai-kpi-label">ANALYZED UNITS</div>
            <div class="ai-kpi-value">{total_units:,}</div>
            <div class="ai-kpi-note">已完成活動單位判讀</div>
        </div>
        <div class="ai-kpi-card">
            <div class="ai-kpi-label">OPPORTUNITIES</div>
            <div class="ai-kpi-value">{continue_count:,}</div>
            <div class="ai-kpi-note">建議延續並驗證放大的活動</div>
        </div>
        <div class="ai-kpi-card">
            <div class="ai-kpi-label">NEED REVIEW</div>
            <div class="ai-kpi-value">{review_count:,}</div>
            <div class="ai-kpi-note">其中 {risk_count:,} 個有降價侵蝕風險</div>
        </div>
        <div class="ai-kpi-card">
            <div class="ai-kpi-label">NET REVENUE EFFECT</div>
            <div class="ai-kpi-value">{format_money(total_net_effect, signed=True)}</div>
            <div class="ai-kpi-note">活動單位淨營收效應合計，非實際毛利</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.subheader("今日 AI 決策摘要")

brief_tone = executive_brief["tone"]
brief_confidence = str(executive_brief["confidence"])

st.markdown(
    f"""
    <div class="ai-brief ai-brief-{safe_html(brief_tone)}">
        <div class="ai-brief-head">
            <span class="ai-brief-tag">✦ PRIMARY RECOMMENDATION</span>
            <span class="ai-confidence {confidence_class(brief_confidence)}">
                資料信心：{safe_html(brief_confidence)}
            </span>
        </div>
        <div class="ai-brief-finding">{safe_html(executive_brief['finding'])}</div>
        <div class="ai-brief-row"><strong>判斷原因</strong><span>{safe_html(executive_brief['reason'])}</span></div>
        <div class="ai-brief-row"><strong>建議行動</strong><span>{safe_html(executive_brief['action'])}</span></div>
        <div class="ai-brief-row"><strong>資料佐證</strong><span>{safe_html(executive_brief['evidence'])}</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)


shortcut_question = None

if st.button(
    "請 AI 進一步解釋這項建議",
    type="primary",
    key="ai_center_explain_primary",
):
    shortcut_question = (
        "請深入解釋目前的首要策略建議。"
        f"資料摘要：{executive_brief['evidence']}。"
        "請說明可能原因、下一期執行步驟、替代方案與資料限制。"
    )


st.divider()
st.subheader("Decision Queue")
st.caption(
    "依負向風險、正向機會與待補樣本訊號排序；每張卡片都可直接交給 AI 深入解讀。"
)


for queue_index, decision in enumerate(decision_queue, start=1):
    with st.container(border=True):
        content_column, metric_column, action_column = st.columns(
            [3.4, 1.1, 1.15],
            gap="medium",
        )

        with content_column:
            st.markdown(
                f"""
                <span class="decision-status">{safe_html(decision['status'])}</span>
                <div class="decision-title">{queue_index:02d} · {safe_html(decision['title'])}</div>
                <div class="decision-action">{safe_html(decision['action'])}</div>
                <div class="decision-evidence">資料佐證：{safe_html(decision['evidence'])}</div>
                """,
                unsafe_allow_html=True,
            )

        with metric_column:
            st.metric(
                "淨增益／日",
                format_money(
                    decision["net_effect_per_day"],
                    signed=True,
                ),
            )
            st.caption(f"資料信心：{decision['confidence']}")

        with action_column:
            if st.button(
                "交給 AI 解讀",
                width="stretch",
                key=f"ai_center_queue_{queue_index}",
            ):
                shortcut_question = decision["prompt"]


st.divider()
st.subheader("下一期活動規劃")

plan_columns = st.columns(3, gap="medium")

for plan_column, plan in zip(plan_columns, next_period_plan):
    with plan_column:
        st.markdown(
            f"""
            <div class="plan-card">
                <div class="plan-step">STEP {safe_html(plan['step'])}</div>
                <div class="plan-title">{safe_html(plan['title'])}</div>
                <div class="plan-description">{safe_html(plan['description'])}</div>
                <div class="plan-evidence">{safe_html(plan['evidence'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.divider()
st.subheader("與 AI 討論下一步")
st.caption(
    "不需要輸入長句：可直接點快捷問題，或在右側延續策略對話。"
)


prompt_column, chat_column = st.columns(
    [1, 1.75],
    gap="large",
)


with prompt_column:
    with st.container(border=True):
        st.markdown("#### 快捷問題")
        st.caption("從目前分析結果直接開始，不會捏造未提供的成本或毛利資料。")

        prompt_specs = [
            (
                "下一期促銷怎麼規劃？",
                "請根據目前結果提出下一期促銷規劃，包含優先活動、測試設計、追蹤指標、資料佐證與風險控制。",
            ),
            (
                "低成效活動原因？",
                "請分析目前建議檢討的活動可能原因，區分可確認的觀察、合理推測與仍需補充的資料。",
            ),
            (
                "折扣率怎麼設定？",
                "請根據折扣深度洞察，整理表現較好的折扣區間與例外案例，並提出下一期可驗證的折扣測試。",
            ),
            (
                "贈品如何搭配？",
                "請根據建議延續活動的贈品與加碼組合，提出下一期贈品設計、替代方案與資料佐證。",
            ),
            (
                "整理成主管摘要",
                "請將目前分析整理成主管摘要，包含首要發現、原因、建議行動、預期影響、資料信心與限制。",
            ),
        ]

        for prompt_index, (label, question) in enumerate(prompt_specs):
            if st.button(
                label,
                width="stretch",
                key=f"ai_center_prompt_{prompt_index}",
            ):
                shortcut_question = question

        st.divider()

        if st.button(
            "清除對話紀錄",
            width="stretch",
            key="ai_center_clear_chat",
        ):
            st.session_state["ai_chat_messages"] = []
            st.rerun()

        st.caption("清除對話不會刪除銷量、活動或分析資料。")


with chat_column:
    chat_container = st.container(
        border=True,
        height=570,
    )

    with chat_container:
        for message in st.session_state["ai_chat_messages"]:
            role = message.get("role", "assistant")
            structured = message.get("structured")

            with st.chat_message(role):
                if structured:
                    render_structured_advisor_card(
                        **structured,
                        is_fallback=message.get(
                            "is_fallback", False
                        ),
                    )
                else:
                    st.markdown(message.get("content", ""))

    typed_question = st.chat_input(
        "輸入策略問題……",
        key="ai_center_chat_input",
    )


user_question = shortcut_question or typed_question


if user_question:
    st.session_state["ai_chat_messages"].append(
        {
            "role": "user",
            "content": user_question,
        }
    )

    with st.spinner("AI 正在比對活動資料與策略證據……"):
        structured_answer, is_fallback = (
            get_structured_advisor_answer(
                user_question=user_question,
                advisor_context=advisor_context,
                chat_messages=st.session_state[
                    "ai_chat_messages"
                ],
                unit_overview_dataframe=unit_overview_raw,
            )
        )

    st.session_state["ai_chat_messages"].append(
        {
            "role": "assistant",
            "content": condense_structured_response(
                structured_answer
            ),
            "structured": structured_answer.model_dump(),
            "is_fallback": is_fallback,
        }
    )
    st.rerun()


st.divider()

with st.expander("完整資料佐證與匯出"):
    st.caption(
        "下表保留策略判讀所使用的活動單位明細；畫面只顯示必要欄位，完整分析資料不會被改寫。"
    )

    evidence_columns = [
        "product_id",
        "product_name",
        "unit_code",
        "corresponding_activities_label",
        "strategy_category",
        "net_revenue_effect_per_day",
        "net_revenue_effect_total",
        "discount_rate",
        "confidence_label",
        "is_risky",
    ]
    evidence_dataframe = strategy[
        [
            column
            for column in evidence_columns
            if column in strategy.columns
        ]
    ].copy()
    evidence_dataframe = evidence_dataframe.rename(
        columns={
            "product_id": "商品編號",
            "product_name": "商品名稱",
            "unit_code": "活動單位",
            "corresponding_activities_label": "對應活動",
            "strategy_category": "策略分類",
            "net_revenue_effect_per_day": "淨增益/日",
            "net_revenue_effect_total": "淨增益合計",
            "discount_rate": "折扣率",
            "confidence_label": "資料信心",
            "is_risky": "降價侵蝕風險",
        }
    )

    st.dataframe(
        evidence_dataframe,
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        "下載 AI 策略佐證 CSV",
        data=evidence_dataframe.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name="ai_strategy_evidence.csv",
        mime="text/csv",
        key="ai_center_download_evidence",
    )


st.caption(
    "AI 建議屬決策輔助；淨營收效應不等於實際毛利或淨利潤。"
    "所有估計與限制均應搭配成本、庫存、退貨與商業目標再次確認。"
)
