from pathlib import Path
import html
import sys

import pandas as pd
import plotly.express as px
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
from src.chart_theme import apply_chart_theme
from src.executive_summary import build_activity_unit_strategy_text
from src.insight_cards import (
    render_evidence_sections,
    render_structured_advisor_card,
)
from src.session_helpers import initialize_session_state
from src.unit_recommendation_notes import (
    build_unit_personalized_recommendation_sections,
)


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


def dataframe_ready(dataframe: object) -> bool:
    return (
        isinstance(dataframe, pd.DataFrame)
        and not dataframe.empty
    )


def render_latest_ai_answer(
    latest_answer: dict,
) -> None:
    st.markdown("#### AI 解讀結果")
    st.caption(
        "來源："
        + str(latest_answer.get("source", "策略提問"))
        + "。結果同時保留在下方對話紀錄。"
    )
    render_structured_advisor_card(
        **latest_answer["structured"],
        is_fallback=latest_answer.get(
            "is_fallback", False
        ),
    )


initialize_session_state()
dark_mode = bool(st.session_state.get("dark_mode", False))


dark_mode = bool(st.session_state.get("dark_mode", False))

st.markdown(
    """
    <style>
    [data-testid="stMainBlockContainer"] h3 {
        font-size: 1.55rem;
    }

    [data-testid="stMainBlockContainer"] h4 {
        font-size: 1.22rem;
    }

    [data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] p {
        font-size: 0.9rem;
        line-height: 1.6;
    }

    [data-testid="stMainBlockContainer"] button p,
    [data-testid="stMainBlockContainer"] [data-baseweb="tab"] p {
        font-size: 0.94rem;
    }

    [data-testid="stMainBlockContainer"] .advisor-row-label,
    [data-testid="stMainBlockContainer"] .advisor-row-text {
        font-size: 0.94rem;
        line-height: 1.65;
    }

    [data-testid="stMainBlockContainer"] .advisor-tag,
    [data-testid="stMainBlockContainer"] .advisor-tag-fallback,
    [data-testid="stMainBlockContainer"] .badge {
        font-size: 0.8rem;
    }

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
        font-size: 0.86rem;
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
        font-size: 1.08rem;
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
        font-size: 0.82rem;
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
        font-size: 0.82rem;
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
        font-size: 0.82rem;
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
        font-size: 0.86rem;
        font-weight: 900;
        letter-spacing: 0.06em;
    }

    .ai-confidence {
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-size: 0.8rem;
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
        font-size: 1.16rem;
        font-weight: 850;
        line-height: 1.55;
    }

    .ai-brief-row {
        display: grid;
        grid-template-columns: 5rem 1fr;
        gap: 0.5rem;
        padding: 0.28rem 0;
        color: var(--text-secondary);
        font-size: 0.94rem;
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
        font-size: 0.78rem;
        font-weight: 850;
    }

    .decision-title {
        color: var(--text-primary);
        font-size: 1.08rem;
        font-weight: 850;
    }

    .decision-action {
        margin-top: 0.35rem;
        color: var(--text-secondary);
        font-size: 0.92rem;
        line-height: 1.55;
    }

    .decision-evidence {
        margin-top: 0.5rem;
        padding-top: 0.48rem;
        color: var(--text-muted);
        border-top: 1px dashed var(--border-soft);
        font-size: 0.84rem;
        line-height: 1.5;
    }

    .queue-balance-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.7rem;
        margin: 0.35rem 0 1.1rem;
    }

    .queue-balance-card {
        padding: 1rem 1.05rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        box-shadow: var(--shadow-sm);
    }

    .queue-balance-count {
        display: inline-block;
        margin-right: 0.45rem;
        color: var(--ai-accent-deep);
        font-size: 1.58rem;
        font-weight: 900;
    }

    .queue-balance-label {
        color: var(--text-primary);
        font-size: 1.1rem;
        font-weight: 850;
    }

    .queue-group-heading {
        margin: 1rem 0 0.55rem;
        padding: 0.78rem 0.9rem;
        color: var(--text-secondary);
        background: var(--surface-soft);
        border-left: 4px solid var(--ai-accent);
        border-radius: 0 10px 10px 0;
        font-size: 0.9rem;
        line-height: 1.55;
    }

    .queue-group-heading strong {
        display: block;
        color: var(--text-primary);
        font-size: 1.18rem;
    }

    .queue-group-risk {
        border-left-color: var(--danger);
    }

    .queue-group-opportunity {
        border-left-color: var(--success);
    }

    .queue-group-observe {
        border-left-color: var(--warning);
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
        font-size: 0.8rem;
        font-weight: 900;
        letter-spacing: 0.1em;
    }

    .plan-title {
        margin: 0.35rem 0 0.5rem;
        color: var(--text-primary);
        font-size: 1.06rem;
        font-weight: 850;
    }

    .plan-description,
    .plan-evidence {
        color: var(--text-secondary);
        font-size: 0.9rem;
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

        .queue-balance-grid {
            grid-template-columns: 1fr;
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
            將策略摘要、優先檢視活動與 AI 對話整合在同一頁。
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
waterfall_pairing_dataframe = st.session_state.get(
    "activity_waterfall_pairing_dataframe"
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
        "系統就會自動產生決策摘要、優先檢視活動與 AI 對話背景。"
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
question_source_label = None
latest_answer = st.session_state.get(
    "ai_center_latest_answer"
)

if st.button(
    "請 AI 進一步解釋這項建議",
    type="primary",
    key="ai_center_explain_primary",
):
    shortcut_question = (
        decision_queue[0]["prompt"]
        if decision_queue
        else (
            "請深入解釋目前的首要策略建議。"
            f"資料摘要：{executive_brief['evidence']}。"
            "請說明可能原因、下一期執行步驟、替代方案與資料限制。"
        )
    )
    question_source_label = "首要策略建議"


if (
    isinstance(latest_answer, dict)
    and latest_answer.get("source") == "首要策略建議"
):
    render_latest_ai_answer(latest_answer)


st.divider()
st.subheader("優先檢視活動")

queue_group_specs = [
    (
        "risk",
        "風險優先",
    ),
    (
        "opportunity",
        "成長機會",
    ),
    (
        "observe",
        "待補資料",
    ),
    (
        "other",
        "其他高影響",
    ),
]

queue_group_counts = {
    group: sum(
        decision["selection_group"] == group
        for decision in decision_queue
    )
    for group, _ in queue_group_specs
}

st.markdown(
    f"""
    <div class="queue-balance-grid">
        <div class="queue-balance-card">
            <span class="queue-balance-count">{queue_group_counts['risk']}</span>
            <span class="queue-balance-label">風險優先</span>
        </div>
        <div class="queue-balance-card">
            <span class="queue-balance-count">{queue_group_counts['opportunity']}</span>
            <span class="queue-balance-label">成長機會</span>
        </div>
        <div class="queue-balance-card">
            <span class="queue-balance-count">{queue_group_counts['observe']}</span>
            <span class="queue-balance-label">待補資料</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

queue_index = 0

for group, group_label in queue_group_specs:
    group_decisions = [
        decision
        for decision in decision_queue
        if decision["selection_group"] == group
    ]

    if not group_decisions:
        continue

    st.markdown(
        f"""
        <div class="queue-group-heading queue-group-{safe_html(group)}">
            <strong>{safe_html(group_label)} · {len(group_decisions)} 筆</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for decision in group_decisions:
        queue_index += 1

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
                    question_source_label = decision["title"]

        if (
            isinstance(latest_answer, dict)
            and latest_answer.get("source") == decision["title"]
        ):
            render_latest_ai_answer(latest_answer)


queue_sources = {
    decision["title"] for decision in decision_queue
}

if (
    isinstance(latest_answer, dict)
    and latest_answer.get("source") != "首要策略建議"
    and latest_answer.get("source") not in queue_sources
):
    render_latest_ai_answer(latest_answer)


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
st.subheader("原始策略分析")
st.caption(
    "保留原策略中心的重要資訊與圖表，重新收納為三個頁籤；"
    "大型策略表格已省略，但原始分析資料沒有刪除或改寫。"
    "月度銷量趨勢已搬到「分析總覽」的「銷量趨勢」區塊。"
)

(
    performance_tab,
    personalized_tab,
    manager_tab,
) = st.tabs(
    [
        "活動成效對照",
        "個別化建議",
        "主管策略摘要",
    ]
)


with performance_tab:
    performance_chart = strategy.copy()
    performance_chart["活動總銷量(估)"] = (
        performance_chart["unit_avg_sales"]
        * performance_chart["days"]
    )

    performance_chart = performance_chart.dropna(
        subset=[
            "活動總銷量(估)",
            "net_revenue_effect_per_day",
        ]
    )

    if performance_chart.empty:
        st.info("目前沒有足夠資料繪製活動成效對照圖。")
    else:
        median_net_effect = performance_chart[
            "net_revenue_effect_per_day"
        ].median()
        performance_figure = px.scatter(
            performance_chart,
            x="活動總銷量(估)",
            y="net_revenue_effect_per_day",
            color="strategy_category",
            hover_name="product_name",
            hover_data={
                "unit_code": True,
                "corresponding_activities_label": True,
                "discount_rate": ":.1%",
                "confidence_label": True,
                "net_revenue_effect_total": ":,.0f",
            },
            labels={
                "net_revenue_effect_per_day": "淨增益／日",
                "strategy_category": "策略分類",
                "unit_code": "活動單位",
                "corresponding_activities_label": "對應活動",
                "discount_rate": "折扣率",
                "confidence_label": "資料信心",
                "net_revenue_effect_total": "淨增益合計",
            },
            color_discrete_map={
                "建議延續": "#009B73",
                "持續觀察": "#F45B1B",
                "建議檢討": "#C62828",
            },
        )
        performance_figure.add_hline(
            y=median_net_effect,
            line_dash="dot",
            annotation_text="淨增益中位數",
        )
        performance_figure.update_traces(
            marker={
                "size": 10,
                "opacity": 0.68,
                "line": {
                    "width": 1,
                    "color": "rgba(0,0,0,0.28)",
                },
            }
        )
        performance_figure.update_layout(
            margin={"l": 10, "r": 10, "t": 24, "b": 10},
            height=430,
        )
        apply_chart_theme(performance_figure, dark_mode)
        st.plotly_chart(performance_figure, width="stretch")
        st.caption(
            "右上方通常代表估算銷量與淨增益都較高；"
            "淨增益不等於實際獲利。"
        )


with personalized_tab:
    st.caption(
        "選擇一個活動單位，查看原策略中心保留的績效診斷、"
        "檔期歸因、建議決策與下一檔執行方式。"
    )

    detail_options = list(strategy.index)

    def format_detail_option(row_index: object) -> str:
        row = strategy.loc[row_index]
        activities_value = row.get(
            "corresponding_activities_label"
        )
        activities = (
            str(activities_value)
            if pd.notna(activities_value)
            and str(activities_value).strip()
            else "安靜期"
        )
        return (
            f"{row.get('product_name', '未命名')}｜"
            f"{row.get('unit_code', '-')}（{activities}）"
        )

    selected_index = st.selectbox(
        "選擇活動單位",
        options=detail_options,
        format_func=format_detail_option,
        key="ai_center_detail_unit",
    )
    selected_unit = strategy.loc[selected_index]

    pairing_table = (
        waterfall_pairing_dataframe.copy()
        if dataframe_ready(waterfall_pairing_dataframe)
        else pd.DataFrame()
    )

    if not pairing_table.empty:
        pairing_table["product_id"] = (
            pairing_table["product_id"]
            .astype(str)
            .str.strip()
        )
        unit_pairing_rows = pairing_table[
            (
                pairing_table["product_id"]
                == selected_unit["product_id"]
            )
            & (
                pairing_table["target_unit"]
                == selected_unit["unit_code"]
            )
        ]
    else:
        unit_pairing_rows = pd.DataFrame()

    mechanism_text = str(
        selected_unit.get(
            "corresponding_activities_label", ""
        )
    )
    personalized_sections = (
        build_unit_personalized_recommendation_sections(
            unit_row=selected_unit,
            pairing_rows=unit_pairing_rows,
            unit_overview=strategy,
            mechanism_text=mechanism_text,
            strategy_category=selected_unit[
                "strategy_category"
            ],
        )
    )

    with st.container(border=True):
        render_evidence_sections(personalized_sections)


with manager_tab:
    management_strategy_text = (
        build_activity_unit_strategy_text(
            unit_overview_raw,
            waterfall_summary_raw,
        )
    )
    st.markdown(management_strategy_text)
    st.download_button(
        "下載主管策略摘要",
        data=management_strategy_text.encode("utf-8"),
        file_name="ai_strategy_management_summary.md",
        mime="text/markdown",
        key="ai_center_download_management_summary",
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
                question_source_label = label

        st.divider()

        if st.button(
            "清除對話紀錄",
            width="stretch",
            key="ai_center_clear_chat",
        ):
            st.session_state["ai_chat_messages"] = []
            st.session_state.pop(
                "ai_center_latest_answer", None
            )
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
    st.session_state["ai_center_latest_answer"] = {
        "source": question_source_label or "自由提問",
        "structured": structured_answer.model_dump(),
        "is_fallback": is_fallback,
    }
    st.rerun()


st.divider()

with st.expander("下載完整策略佐證資料"):
    st.caption(
        "畫面省略大型表格，但完整活動單位資料仍保留，"
        "可下載 CSV 進一步查閱。"
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