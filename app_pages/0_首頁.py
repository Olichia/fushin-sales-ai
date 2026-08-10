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
