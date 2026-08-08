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
    st.switch_page("app_pages/15_資料管理中心.py")
