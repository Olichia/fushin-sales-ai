from pathlib import Path
import base64
import html
import sys

import pandas as pd
import streamlit as st


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.demo_data import (
    apply_full_demo_data_to_session,
    get_demo_analysis_result,
    get_demo_sales_result,
)
from src.session_helpers import initialize_session_state
from src.ai_advisor import (
    build_advisor_context,
    get_structured_advisor_answer,
)
from src.ai_strategy_center import (
    build_decision_queue,
    prepare_ai_strategy_data,
)


def _render_template(filename: str, **replacements: str) -> str:
    """
    讀取 templates/ 下的 HTML／CSS 樣板，代入 {{PLACEHOLDER}}
    後回傳給 st.markdown(unsafe_allow_html=True) 使用。

    CommonMark 解析器只要在內嵌 HTML 中間看到空白行，就會提早
    結束「原始 HTML 區塊」，讓後面的標籤變成純文字顯示出來
    （見 src/insight_cards.py 的同一段說明）。樣板檔案本身可以
    正常留空行方便閱讀，這裡讀檔時統一濾掉空白行，確保傳給
    st.markdown 的字串裡沒有任何一行是空的，避免踩到這個雷；
    HTML 標籤之間的換行本身不影響渲染結果（瀏覽器一律當成一個
    空白字元），所以濾掉空行不影響版面。
    """

    content = (TEMPLATES_DIR / filename).read_text(encoding="utf-8")

    for key, value in replacements.items():
        content = content.replace("{{" + key + "}}", value)

    non_blank_lines = [
        line for line in content.splitlines() if line.strip()
    ]

    return "\n".join(non_blank_lines)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

LOGO_PATH = PROJECT_ROOT / "assets" / "logo-white.png"


# =========================================================
# 首頁重點功能與統計數字
#
# HERO_STATS 的「資料追蹤規模」「檔期與品項辨識」兩項數字改接
# src/demo_data.py 的示範資料快取（跟 01/02 上傳頁示範模式、
# 「開始探索」按鈕同一套），原本獨立放在頁面下方的「平台核心
# 效益與決策流程」區塊（白色卡＋藍色流程圖）內容已併入這裡，
# 不再重複顯示。「SKU規模」「AI 洞察產出速度」仍是示意佔位數字，
# 等使用者提供更多真實數據再替換。
# =========================================================

HERO_FEATURES = [
    (
        "merge_type",
        "orange",
        "資料整合",
        "銷量與活動資料自動整合",
    ),
    (
        "query_stats",
        "blue",
        "活動洞察",
        "揪出高低成效與毛利風險",
    ),
    (
        "lightbulb",
        "magenta",
        "AI 策略中心",
        "AI 顧問即時問答與建議",
    ),
    (
        "show_chart",
        "green",
        "情境模擬",
        "方案比較找出最佳解",
    ),
    (
        "rocket_launch",
        "indigo",
        "行動生成",
        "一鍵生成可執行行動清單",
    ),
]


def _encode_logo() -> str | None:
    if not LOGO_PATH.exists():
        return None

    return base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")


def _get_home_benefit_stats() -> tuple[int, int]:
    """
    取得 Hero 統計列「資料追蹤規模」要顯示的示範資料規模數字。

    直接讀 src/demo_data.py 已經在用的示範資料快取（跟 01/02
    上傳頁示範模式、「開始探索」按鈕同一套），資料庫查詢失敗時
    才退回固定的示意數字，不影響首頁正常顯示。
    """

    try:
        sales_result = get_demo_sales_result()
        analysis_result = get_demo_analysis_result()

        total_records = len(
            sales_result["standardized_dataframe"]
        )
        total_units = len(
            analysis_result["activity_unit_overview_dataframe"]
        )

        return total_records, total_units

    except Exception:
        return 305, 140


home_benefit_total_records, _home_benefit_total_units = (
    _get_home_benefit_stats()
)

HERO_STATS = [
    ("📊", "orange", f"{home_benefit_total_records} 筆", "資料追蹤規模"),
    ("🧮", "blue", "10000+", "SKU規模"),
    ("🎯", "magenta", "100%", "檔期與品項辨識"),
    ("⚡", "green", "< 3 秒", "AI 洞察產出速度"),
]


# =========================================================
# Hero 內容
#
# CSS 與版面結構都在 templates/home_hero.html，這裡只負責
# 準備動態資料（圖示、統計數字）並代入樣板。
# =========================================================

encoded_logo = _encode_logo()

# 這幾段清單／emoji 內容用資料驅動產生，天生就是不含換行的
# 單行字串（見 _render_template 說明），可以安全地代入樣板。

feature_cards_html = "".join(
    '<div class="hero-feature-card">'
    f'<div class="hero-feature-icon-badge hero-feature-icon-{color_key}">'
    '<span class="hero-feature-icon-glyph" data-testid="stIconMaterial" '
    "style=\"font-family:'Material Symbols Rounded';\" translate=\"no\">"
    f"{icon_name}</span>"
    "</div>"
    f'<div class="hero-feature-title">{title}</div>'
    f'<div class="hero-feature-description">{description}</div>'
    "</div>"
    for icon_name, color_key, title, description in HERO_FEATURES
)

stat_items_html = "".join(
    '<div class="hero-stat-item">'
    f'<div class="hero-stat-icon">{icon}</div>'
    "<div>"
    f'<div class="hero-stat-value hero-stat-value-{color_key}">{value}</div>'
    f'<div class="hero-stat-label">{label}</div>'
    "</div>"
    "</div>"
    for icon, color_key, value, label in HERO_STATS
)

orb_html = (
    '<img class="hero-orb-logo" '
    f'src="data:image/png;base64,{encoded_logo}" alt="富信新零售 Logo">'
    if encoded_logo
    else ""
)

st.markdown(
    _render_template(
        "home_hero.html",
        FEATURE_CARDS_HTML=feature_cards_html,
        STAT_ITEMS_HTML=stat_items_html,
        ORB_HTML=orb_html,
    ),
    unsafe_allow_html=True,
)


# =========================================================
# AI 今日洞察
#
# 不新增資料表、不改分析公式：
# 1. Pandas 從既有活動單位分析結果挑出 3 個高影響異常／機會
# 2. Pandas 計算 KPI、歷史平均與相似活動證據
# 3. 只把這些結構化事實交給既有 Gemini 顧問
# 4. Gemini 只負責「可能原因」與「下一步行動」
#
# 結果會依目前資料內容快取在 session_state，避免每次 rerun
# 都重新呼叫 Gemini；資料一變更才會重新產生。
# =========================================================


def _fmt_money(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "無法計算"
    return f"${float(number):+,.0f}"


def _fmt_percent(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "無法計算"
    return f"{float(number):.1%}"


def _build_home_history_context(
    strategy: pd.DataFrame,
    row: pd.Series,
) -> tuple[str, str]:
    """
    所有比較數字都在 Pandas 先算完。
    Gemini 不參與任何平均數、差異或歷史案例數字的計算。
    """

    product_id = str(row.get("product_id", "")).strip()
    unit_code = str(row.get("unit_code", "")).strip()
    current_net = pd.to_numeric(
        row.get("net_revenue_effect_per_day"),
        errors="coerce",
    )

    other_product_rows = strategy[
        (strategy["product_id"].astype(str) == product_id)
        & (strategy["unit_code"].astype(str) != unit_code)
    ].copy()

    if not other_product_rows.empty:
        historical_mean = pd.to_numeric(
            other_product_rows["net_revenue_effect_per_day"],
            errors="coerce",
        ).mean()
        comparison_scope = "同商品其他活動單位平均"
    else:
        other_rows = strategy[
            ~(
                (strategy["product_id"].astype(str) == product_id)
                & (strategy["unit_code"].astype(str) == unit_code)
            )
        ].copy()
        historical_mean = pd.to_numeric(
            other_rows["net_revenue_effect_per_day"],
            errors="coerce",
        ).mean()
        comparison_scope = "其他活動單位平均"

    if pd.notna(current_net) and pd.notna(historical_mean):
        difference = float(current_net) - float(historical_mean)
        comparison_text = (
            f"目前淨增益/日 {_fmt_money(current_net)}，"
            f"相較{comparison_scope} {_fmt_money(historical_mean)}，"
            f"差異 {_fmt_money(difference)}。"
        )
    else:
        comparison_text = "目前資料不足以計算可比較的歷史平均。"

    activity_label = str(
        row.get("corresponding_activities_label", "")
    ).strip()

    similar_rows = strategy[
        (strategy["corresponding_activities_label"].astype(str) == activity_label)
        & ~(
            (strategy["product_id"].astype(str) == product_id)
            & (strategy["unit_code"].astype(str) == unit_code)
        )
    ].copy()

    if not similar_rows.empty:
        similar_rows["_net"] = pd.to_numeric(
            similar_rows["net_revenue_effect_per_day"],
            errors="coerce",
        )
        similar_rows = similar_rows.sort_values(
            "_net",
            ascending=False,
            na_position="last",
        )
        similar = similar_rows.iloc[0]
        similar_evidence = (
            f"相同活動組合的歷史案例："
            f"{similar.get('product_name', '未命名商品')}・"
            f"{similar.get('unit_code', '-')}，"
            f"淨增益/日 {_fmt_money(similar.get('net_revenue_effect_per_day'))}，"
            f"折扣率 {_fmt_percent(similar.get('discount_rate'))}。"
        )
    else:
        similar_evidence = (
            "目前資料中沒有其他完全相同的活動組合可直接比較，"
            "因此此項判斷以目前 KPI 與歷史平均為主要證據。"
        )

    return comparison_text, similar_evidence


def _build_home_ai_insights() -> list[dict[str, str]]:
    unit_overview = st.session_state.get(
        "activity_unit_overview_dataframe"
    )
    waterfall_summary = st.session_state.get(
        "activity_waterfall_summary_dataframe"
    )
    unit_price = st.session_state.get(
        "activity_unit_price_dataframe"
    )

    if (
        not isinstance(unit_overview, pd.DataFrame)
        or unit_overview.empty
        or not isinstance(waterfall_summary, pd.DataFrame)
        or waterfall_summary.empty
    ):
        return []

    strategy = prepare_ai_strategy_data(unit_overview)
    queue = build_decision_queue(strategy, limit=3)

    if not queue:
        return []

    advisor_context = build_advisor_context(
        unit_overview_dataframe=unit_overview,
        waterfall_summary_dataframe=waterfall_summary,
        unit_price_dataframe=unit_price,
    )

    insights: list[dict[str, str]] = []

    for item in queue:
        match = strategy[
            (strategy["product_id"].astype(str) == str(item["product_id"]))
            & (strategy["unit_code"].astype(str) == str(item["unit_code"]))
        ]

        if match.empty:
            continue

        row = match.iloc[0]
        comparison_text, similar_evidence = (
            _build_home_history_context(strategy, row)
        )

        kpi_text = (
            f"淨增益/日 {_fmt_money(row.get('net_revenue_effect_per_day'))}；"
            f"量增效應/日 {_fmt_money(row.get('volume_effect_per_day'))}；"
            f"降價效應/日 {_fmt_money(row.get('price_effect_per_day'))}；"
            f"折扣率 {_fmt_percent(row.get('discount_rate'))}。"
        )

        what_happened = (
            f"{item['selection_label']}｜{item['title']}："
            f"目前淨增益/日 "
            f"{_fmt_money(row.get('net_revenue_effect_per_day'))}。"
        )

        # Prompt 只提供 Pandas 已計算完成的數字。
        # Gemini 只被要求解釋原因與提出行動，不允許新增任何數值。
        question = (
            f"請針對 {item['title']} 產生首頁即時洞察。"
            f"已由 Pandas 計算的事實如下："
            f"發生事情：{what_happened} "
            f"KPI：{kpi_text} "
            f"歷史比較：{comparison_text} "
            f"歷史證據：{similar_evidence} "
            "請只根據上述資料與既有分析背景，"
            "解釋可能原因並提出下一步行銷行動。"
            "禁止創造任何新數字；若資料不足請直接說明。"
            f"商品編號 {item['product_id']}，活動單位 {item['unit_code']}。"
        )

        structured, is_fallback = get_structured_advisor_answer(
            user_question=question,
            advisor_context=advisor_context,
            chat_messages=[],
            unit_overview_dataframe=unit_overview,
        )

        confidence = str(structured.confidence)
        if confidence not in {"高", "中", "低"}:
            confidence = "低"

        insights.append(
            {
                "title": item["title"],
                "tag": item["selection_label"],
                "what_happened": what_happened,
                "kpi": kpi_text,
                "comparison": comparison_text,
                "reason": structured.reason,
                "evidence": similar_evidence,
                "base_evidence": str(item.get("evidence", "")),
                "action": structured.action,
                "confidence": confidence,
                "limitations": structured.limitations,
                "is_fallback": "1" if is_fallback else "0",
                "product_id": str(item["product_id"]),
                "unit_code": str(item["unit_code"]),
            }
        )

    return insights


def _home_ai_signature() -> str:
    unit_overview = st.session_state.get(
        "activity_unit_overview_dataframe"
    )

    if (
        not isinstance(unit_overview, pd.DataFrame)
        or unit_overview.empty
    ):
        return "no-data"

    columns = [
        column
        for column in [
            "product_id",
            "unit_code",
            "days",
            "discount_rate",
            "volume_effect_per_day",
            "price_effect_per_day",
            "net_revenue_effect_per_day",
            "corresponding_activities_label",
        ]
        if column in unit_overview.columns
    ]

    hashed = pd.util.hash_pandas_object(
        unit_overview[columns].fillna(""),
        index=True,
    )

    return str(int(hashed.sum()))


home_ai_signature = _home_ai_signature()

if (
    st.session_state.get("home_ai_insights_signature")
    != home_ai_signature
):
    with st.spinner("AI 正在整理今日最值得注意的 3 個訊號…"):
        st.session_state["home_ai_insights"] = (
            _build_home_ai_insights()
        )
        st.session_state["home_ai_insights_signature"] = (
            home_ai_signature
        )

home_ai_insights = st.session_state.get(
    "home_ai_insights",
    [],
)

if home_ai_insights:
    def _safe_home_text(value: object) -> str:
        return html.escape(str(value))

    st.markdown(
        """
        <style>
        .home-ai-title {
            margin-top: 1.4rem;
            margin-bottom: 0.25rem;
            font-size: 1.65rem;
            font-weight: 900;
            color: var(--text-primary);
        }
        .home-ai-subtitle {
            margin-bottom: 0.9rem;
            color: var(--text-secondary);
            font-size: 0.92rem;
        }
        .home-ai-card-head {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            flex-wrap: wrap;
            margin-bottom: 0.55rem;
        }
        .home-ai-tag {
            display: inline-block;
            padding: 0.2rem 0.58rem;
            border-radius: 999px;
            background: var(--ai-accent-soft);
            color: var(--ai-accent-deep);
            font-size: 0.78rem;
            font-weight: 850;
            white-space: nowrap;
        }
        .home-ai-card-title {
            color: var(--text-primary);
            font-size: 1.02rem;
            font-weight: 900;
        }
        .home-ai-section-label {
            margin-bottom: 0.2rem;
            color: var(--text-primary);
            font-size: 0.82rem;
            font-weight: 850;
        }
        .home-ai-section-text {
            color: var(--text-secondary);
            font-size: 0.84rem;
            line-height: 1.5;
        }
        .home-ai-kpi-box {
            margin-top: 0.55rem;
            padding: 0.6rem 0.7rem;
            border-radius: 10px;
            background: rgba(249, 115, 22, 0.06);
            border: 1px solid rgba(249, 115, 22, 0.16);
        }
        .home-ai-confidence {
            display: inline-block;
            margin-top: 0.55rem;
            padding: 0.18rem 0.5rem;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.05);
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 800;
        }
        .home-ai-divider {
            height: 1px;
            margin: 0.55rem 0;
            background: var(--border);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="home-ai-title">'
        f'AI 今日發現 {len(home_ai_insights)} 個值得注意的行銷機會'
        f'</div>'
        f'<div class="home-ai-subtitle">'
        f'由既有銷售與活動資料自動偵測；所有數字皆由 Pandas 計算，'
        f'AI 僅負責原因解釋與下一步建議。'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 每一筆洞察改成「一張卡一整列」的橫式版型，
    # 評審能由左到右快速讀完：發現 → 判斷 → 證據與行動。
    for index, insight in enumerate(home_ai_insights):
        with st.container(border=True):
            st.markdown(
                '<div class="home-ai-card-head">'
                f'<span class="home-ai-tag">{_safe_home_text(insight["tag"])}</span>'
                f'<span class="home-ai-card-title">{_safe_home_text(insight["title"])}</span>'
                '</div>',
                unsafe_allow_html=True,
            )

            left_col, middle_col, right_col = st.columns(
                [1.05, 1.35, 1.35],
                gap="large",
            )

            with left_col:
                st.markdown(
                    '<div class="home-ai-section-label">發生什麼</div>'
                    f'<div class="home-ai-section-text">'
                    f'{_safe_home_text(insight["what_happened"])}</div>'
                    '<div class="home-ai-kpi-box">'
                    '<div class="home-ai-section-label">KPI 異常</div>'
                    f'<div class="home-ai-section-text">'
                    f'{_safe_home_text(insight["kpi"])}</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

            with middle_col:
                st.markdown(
                    '<div class="home-ai-section-label">歷史比較</div>'
                    f'<div class="home-ai-section-text">'
                    f'{_safe_home_text(insight["comparison"])}</div>'
                    '<div class="home-ai-divider"></div>'
                    '<div class="home-ai-section-label">AI 推測原因</div>'
                    f'<div class="home-ai-section-text">'
                    f'{_safe_home_text(insight["reason"])}</div>',
                    unsafe_allow_html=True,
                )

            with right_col:
                st.markdown(
                    '<div class="home-ai-section-label">歷史證據</div>'
                    f'<div class="home-ai-section-text">'
                    f'{_safe_home_text(insight["evidence"])}</div>'
                    '<div class="home-ai-divider"></div>'
                    '<div class="home-ai-section-label">建議下一步</div>'
                    f'<div class="home-ai-section-text">'
                    f'{_safe_home_text(insight["action"])}</div>'
                    f'<span class="home-ai-confidence">'
                    f'AI 信心：{_safe_home_text(insight["confidence"])}</span>',
                    unsafe_allow_html=True,
                )

            evidence_col, action_col = st.columns([1, 1])

            with evidence_col:
                if st.button(
                    "查看判斷依據",
                    key=f"home_ai_evidence_btn_{index}",
                    use_container_width=True,
                ):
                    evidence_key = f"home_ai_evidence_{index}"
                    st.session_state[evidence_key] = not bool(
                        st.session_state.get(evidence_key, False)
                    )

            with action_col:
                if st.button(
                    "行動生成 →",
                    key=f"home_ai_action_btn_{index}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["home_ai_selected_insight"] = insight
                    st.switch_page("app_pages/18_行動生成.py")

            if st.session_state.get(
                f"home_ai_evidence_{index}",
                False,
            ):
                with st.expander(
                    "判斷依據與資料限制",
                    expanded=True,
                ):
                    st.markdown(
                        f"**目前活動證據**  \n{insight['base_evidence']}\n\n"
                        f"**歷史／類似活動**  \n{insight['evidence']}\n\n"
                        f"**資料限制**  \n{insight['limitations']}"
                    )

else:
    st.info(
        "AI 今日洞察正在等待完整分析資料；完成分析後，"
        "首頁會自動顯示 3 個最值得注意的異常或機會。"
    )



with st.container(key="hero_cta_button"):
    start_exploring = st.button(
        "開始探索 →",
        type="primary",
        use_container_width=True,
    )

if start_exploring:
    # 「開始探索」預設套入示範資料（銷量、活動與完整分析結果
    # 一次備妥），直接跳到分析總覽，不用再走一次上傳流程。
    apply_full_demo_data_to_session()

    st.switch_page("app_pages/11_產品首頁.py")