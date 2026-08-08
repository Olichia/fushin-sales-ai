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
# =========================================================

HERO_FEATURES = [
    (
        "search",
        "orange",
        "AI 主動洞察",
        "精準識別高低成效與風險",
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
# =========================================================

encoded_logo = _encode_logo()

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

# 拿掉可能引起版本相容問題的 key 參數
with st.container():
    start_exploring = st.button(
        "開始探索 →",
        type="primary",
        use_container_width=True,
    )

if start_exploring:
    try:
        st.switch_page("app_pages/15_資料管理中心.py")
    except Exception as e:
        st.error(f"頁面跳轉失敗，請確認該檔案路徑是否存在：{e}")
