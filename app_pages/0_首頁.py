import base64
from pathlib import Path
import sys
import pandas as pd
import streamlit as st

# =========================================================
# 專案路徑與初始化
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = PROJECT_ROOT / "templates"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.session_helpers import initialize_session_state

initialize_session_state()

DEMO_FILE_PATH = PROJECT_ROOT / "assets" / "demo_sales_data.xlsx"
LOGO_PATH = PROJECT_ROOT / "assets" / "logo-white.png"


def _render_template(filename: str, **replacements: str) -> str:
    """讀取 templates/ 下的 HTML／CSS 樣板，代入 {{PLACEHOLDER}}"""
    template_path = TEMPLATES_DIR / filename
    if not template_path.exists():
        return ""
    content = template_path.read_text(encoding="utf-8")

    for key, value in replacements.items():
        content = content.replace("{{" + key + "}}", value)

    non_blank_lines = [line for line in content.splitlines() if line.strip()]

    return "\n".join(non_blank_lines)


def _encode_logo() -> str | None:
    if not LOGO_PATH.exists():
        return None
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")


def _resolve_demo_path() -> Path | None:
    if DEMO_FILE_PATH.exists():
        return DEMO_FILE_PATH
    alt_path = PROJECT_ROOT / "3-4月活動成效表_v2.xlsx"
    if alt_path.exists():
        return alt_path
    return None


# 側邊欄自動收合
st.markdown(
    _render_template("sidebar_collapse.html"),
    unsafe_allow_html=True,
)

# =========================================================
# 數據預載邏輯函式
# =========================================================

def load_demo_data_to_session():
    """將 3-4 月銷量活動數據預先讀取並存入 Streamlit Session State"""
    st.session_state["is_demo_mode"] = True
    st.session_state["demo_file_path"] = str(DEMO_FILE_PATH)

    target_path = _resolve_demo_path()

    if target_path is not None:
        try:
            xls = pd.ExcelFile(target_path)
            if "銷量原始資料(零填補)" in xls.sheet_names:
                st.session_state["sales_data"] = pd.read_excel(xls, sheet_name="銷量原始資料(零填補)")
            else:
                st.session_state["sales_data"] = pd.read_excel(xls, sheet_name=0)

            if "活動單位清單(依時間)" in xls.sheet_names:
                st.session_state["events_data"] = pd.read_excel(xls, sheet_name="活動單位清單(依時間)")

            if "活動單位總覽(vs基準)" in xls.sheet_names:
                st.session_state["overview_data"] = pd.read_excel(xls, sheet_name="活動單位總覽(vs基準)")

            st.session_state["data_loaded"] = True
            return True
        except Exception as e:
            st.error(f"數據讀取失敗：{e}")
            return False
    else:
        st.error("找不到數據檔案，請確認 assets/demo_sales_data.xlsx 是否存在。")
        return False


# 輕量讀取 305筆紀錄與 140筆總覽供效益卡動態顯示
@st.cache_data(show_spinner=False)
def get_home_stats(file_path: str):
    path = Path(file_path)
    if not path.exists():
        return 305, 61, 140
    try:
        xls = pd.ExcelFile(path)
        sales_df = pd.read_excel(xls, sheet_name="銷量原始資料(零填補)")
        overview_df = pd.read_excel(xls, sheet_name="活動單位總覽(vs基準)")
        return len(sales_df), sales_df["日期"].nunique(), len(overview_df)
    except Exception:
        return 305, 61, 140


_demo_path = _resolve_demo_path()
total_recs, total_days, total_units = get_home_stats(str(_demo_path)) if _demo_path else (305, 61, 140)


# =========================================================
# 樣式設定 CSS
# =========================================================
st.markdown(
    """
<style>
    /* 全域文字放大 */
    html, body, [class*="css"] {
        font-size: 18px !important;
    }

    /* 特徵卡片字體放大 */
    .hero-feature-title {
        font-size: 20px !important;
        font-weight: 800 !important;
    }
    .hero-feature-description {
        font-size: 16px !important;
        line-height: 1.5 !important;
    }

    /* 下方效益卡字體放大 */
    .spec-benefit-card {
        background: #FFFFFF;
        border: 2px solid #E2E8F0;
        border-radius: 16px;
        padding: 26px 20px;
        text-align: center;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.04);
    }
    .spec-benefit-lbl { font-size: 19px !important; font-weight: 800; color: #475569; margin-bottom: 10px; }
    .spec-benefit-val { font-size: 36px !important; font-weight: 900; color: #EA580C; margin: 8px 0; line-height: 1.1; }
    .spec-benefit-sub { font-size: 16px !important; color: #64748B; font-weight: 700; }

    /* 四步驟流程圖字體放大 */
    .spec-flow-wrapper {
        background: #EFF6FF;
        border: 2px solid #BFDBFE;
        border-radius: 16px;
        padding: 24px 30px;
        margin: 28px 0;
        display: flex;
        align-items: center;
        justify-content: space-around;
        text-align: center;
    }
    .spec-flow-step {
        font-size: 20px !important;
        font-weight: 900;
        color: #1E40AF;
    }
    .spec-flow-arrow {
        font-size: 28px !important;
        color: #3B82F6;
        font-weight: 900;
    }
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 1. Hero 視覺區塊
# =========================================================

HERO_FEATURES = [
    ("search", "orange", "AI 主動洞察", "精準識別高低成效與風險"),
    ("show_chart", "blue", "情境模擬", "方案比較找出最佳解"),
    ("lightbulb", "magenta", "策略建議", "AI 顧問即時問答"),
    ("picture_as_pdf", "green", "主管報表", "一鍵匯出 PDF 報告"),
]

HERO_STATS = [
    ("📊", "orange", "20+", "活動單位拆解案例"),
    ("🧮", "blue", "10,000+", "SKU規模"),
    ("🤖", "magenta", "24/7", "AI 洞察待命"),
    ("🏬", "green", "600+", "合作門市"),
]

encoded_logo = _encode_logo()

feature_cards_html = "".join(
    f'<div class="hero-feature-card">'
    f'<div class="hero-feature-icon-badge hero-feature-icon-{color_key}">'
    f'<span class="hero-feature-icon-glyph" data-testid="stIconMaterial" style="font-family:\'Material Symbols Rounded\';" translate="no">{icon_name}</span>'
    f'</div>'
    f'<div class="hero-feature-title">{title}</div>'
    f'<div class="hero-feature-description">{description}</div>'
    f'</div>'
    for icon_name, color_key, title, description in HERO_FEATURES
)

stat_items_html = "".join(
    f'<div class="hero-stat-item">'
    f'<div class="hero-stat-icon">{icon}</div>'
    f'<div>'
    f'<div class="hero-stat-value hero-stat-value-{color_key}">{value}</div>'
    f'<div class="hero-stat-label">{label}</div>'
    f'</div>'
    f'</div>'
    for icon, color_key, value, label in HERO_STATS
)

orb_html = (
    f'<img class="hero-orb-logo" src="data:image/png;base64,{encoded_logo}" alt="富信新零售 Logo">'
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
# 2. 單一按鈕區 (精準對應 4_銷售總覽.py 跳轉)
# =========================================================

cta_col, _ = st.columns([1, 2])

with cta_col:
    start_demo = st.button(
        "🚀 開始示範",
        type="primary",
        use_container_width=True,
        help="【Demo 極速通道】預載示範數據，直達分析總覽頁面。"
    )

if start_demo:
    if load_demo_data_to_session():
        st.toast("🚀 3-4 月示範數據已載入！正在前往分析總覽...", icon="✅")
        candidate_pages = [
            "pages/4_銷售總覽.py",
            "app_pages/4_銷售總覽.py",
            "4_銷售總覽.py",
            "pages/分析總覽.py",
            "app_pages/分析總覽.py",
            "分析總覽.py",
        ]
        switched = False
        for target in candidate_pages:
            try:
                st.switch_page(target)
                switched = True
                break
            except Exception:
                continue

        if not switched:
            st.error("跳轉失敗：請確認專案中是否存在對應的 `4_銷售總覽.py` 頁面檔案。")

st.markdown("<br>", unsafe_allow_html=True)


# =========================================================
# 3. 三張效益卡 + 無編號的四步驟流程圖
# =========================================================

st.markdown("##### ⚡ 平台核心效益與決策閉環")

b_col1, b_col2, b_col3 = st.columns(3)

with b_col1:
    st.markdown(
        f"""<div class="spec-benefit-card">
            <div class="spec-benefit-lbl">📊 資料追蹤規模</div>
            <div class="spec-benefit-val">{total_recs} 筆</div>
            <div class="spec-benefit-sub">涵蓋 3-4 月完整 {total_days} 天銷量紀錄</div>
        </div>""",
        unsafe_allow_html=True,
    )

with b_col2:
    st.markdown(
        f"""<div class="spec-benefit-card">
            <div class="spec-benefit-lbl">🎯 檔期與品項辨識</div>
            <div class="spec-benefit-val">100%</div>
            <div class="spec-benefit-sub">自動對比 {total_units} 筆歷史檔期基準</div>
        </div>""",
        unsafe_allow_html=True,
    )

with b_col3:
    st.markdown(
        """<div class="spec-benefit-card">
            <div class="spec-benefit-lbl">⚡ AI 洞察產出速度</div>
            <div class="spec-benefit-val">&lt; 3 秒</div>
            <div class="spec-benefit-sub">一鍵自動生成結構化決策建議</div>
        </div>""",
        unsafe_allow_html=True,
    )

# 四步驟流程圖（已移除數字編號）
st.markdown(
    """<div class="spec-flow-wrapper">
        <div class="spec-flow-step">📄 銷量資料</div>
        <div class="spec-flow-arrow">➔</div>
        <div class="spec-flow-step">🤖 AI 結構化洞察</div>
        <div class="spec-flow-arrow">➔</div>
        <div class="spec-flow-step">💡 可執行行動建議</div>
        <div class="spec-flow-arrow">➔</div>
        <div class="spec-flow-step">📈 效益與成效追蹤</div>
    </div>""",
    unsafe_allow_html=True,
)
