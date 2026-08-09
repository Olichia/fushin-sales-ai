from pathlib import Path
import base64
import sys

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
# HERO_STATS 大部分仍是示意佔位數字（500+／1,000+／24/7），
# 等使用者提供更多真實數據再替換。「合作門市」已改用富信企業
# 介紹檔案（台灣大哥大簡介 PDF）裡的實際數字：約 600 間實體
# 門市，不是本系統自己算出來的資料。
# =========================================================

HERO_FEATURES = [
    (
        "search",
        "orange",
        "AI 主動洞察",
        "揪出高低成效與風險",
    ),
    (
        "show_chart",
        "blue",
        "情境模擬",
        "方案比較找出最佳解",
    ),
    (
        "lightbulb",
        "magenta",
        "策略建議",
        "AI 顧問即時問答",
    ),
    (
        "picture_as_pdf",
        "green",
        "主管報表",
        "一鍵匯出 PDF 報告",
    ),
]

HERO_STATS = [
    ("📊", "orange", "20+", "活動單位拆解案例"),
    ("🧮", "blue", "10000+", "SKU規模"),
    ("🤖", "magenta", "24/7", "AI 洞察待命"),
    ("🏬", "green", "600+", "合作門市"),
]


def _encode_logo() -> str | None:
    if not LOGO_PATH.exists():
        return None

    return base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")


def _get_home_benefit_stats() -> tuple[int, int]:
    """
    取得下方效益卡要顯示的示範資料規模數字。

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

with st.container(key="hero_cta_button"):
    start_exploring = st.button(
        "開始探索 →",
        type="primary",
        use_container_width=True,
    )

if start_exploring:
    # 「開始探索」預設套入示範資料（銷量、活動與完整分析結果
    # 一次備妥），直接跳到 AI 策略中心，不用再走一次上傳流程。
    apply_full_demo_data_to_session()

    st.switch_page("app_pages/13_策略中心.py")


# =========================================================
# 平台核心效益與決策流程
#
# 內容與版面沿用 feature/ui-landind-page-v3 分支已經做好的
# 設計，但效益卡數字改接現有的示範資料快取
# （get_demo_sales_result／get_demo_analysis_result，見
# src/demo_data.py），不是該分支舊版的
# load_demo_data_to_session／get_home_stats；顏色全部改走
# 專案既有的 CSS 變數，深色模式才會正確換色（原設計是寫死
# 色碼、只考慮淺色）。
# =========================================================

st.markdown(
    """
    <style>
    .spec-benefit-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 26px 20px;
        text-align: center;
        box-shadow: var(--shadow-sm);
    }
    .spec-benefit-lbl {
        margin-bottom: 10px;
        color: var(--text-secondary);
        font-size: 0.98rem;
        font-weight: 800;
    }
    .spec-benefit-val {
        margin: 8px 0;
        color: var(--brand-orange-dark);
        font-size: 1.9rem;
        font-weight: 900;
        line-height: 1.1;
    }
    .spec-benefit-sub {
        color: var(--text-muted);
        font-size: 0.85rem;
        font-weight: 700;
    }

    .spec-flow-wrapper {
        display: flex;
        align-items: center;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 28px 0;
        padding: 24px 30px;
        background: var(--ai-accent-soft);
        border: 1px solid var(--ai-accent-border);
        border-radius: 16px;
        text-align: center;
    }
    .spec-flow-step {
        color: var(--ai-accent-deep);
        font-size: 1.02rem;
        font-weight: 900;
    }
    .spec-flow-arrow {
        color: var(--ai-accent);
        font-size: 1.4rem;
        font-weight: 900;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("##### ⚡ 平台核心效益與決策流程")

home_benefit_total_records, home_benefit_total_units = (
    _get_home_benefit_stats()
)

benefit_col1, benefit_col2, benefit_col3 = st.columns(3)

with benefit_col1:
    st.markdown(
        f"""<div class="spec-benefit-card">
            <div class="spec-benefit-lbl">📊 資料追蹤規模</div>
            <div class="spec-benefit-val">{home_benefit_total_records} 筆</div>
            <div class="spec-benefit-sub">涵蓋完整活動週期的銷量紀錄</div>
        </div>""",
        unsafe_allow_html=True,
    )

with benefit_col2:
    st.markdown(
        f"""<div class="spec-benefit-card">
            <div class="spec-benefit-lbl">🎯 檔期與品項辨識</div>
            <div class="spec-benefit-val">100%</div>
            <div class="spec-benefit-sub">自動對比 {home_benefit_total_units} 筆歷史檔期基準</div>
        </div>""",
        unsafe_allow_html=True,
    )

with benefit_col3:
    st.markdown(
        """<div class="spec-benefit-card">
            <div class="spec-benefit-lbl">⚡ AI 洞察產出速度</div>
            <div class="spec-benefit-val">&lt; 3 秒</div>
            <div class="spec-benefit-sub">一鍵自動生成結構化決策建議</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown(
    """<div class="spec-flow-wrapper">
        <div class="spec-flow-step">📄 銷量活動資料</div>
        <div class="spec-flow-arrow">➔</div>
        <div class="spec-flow-step">🤖 AI 結構化洞察</div>
        <div class="spec-flow-arrow">➔</div>
        <div class="spec-flow-step">💡 可執行行動建議</div>
        <div class="spec-flow-arrow">➔</div>
        <div class="spec-flow-step">📈 效益與成效追蹤</div>
    </div>""",
    unsafe_allow_html=True,
)
