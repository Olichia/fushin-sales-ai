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

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.session_helpers import initialize_session_state

initialize_session_state()

# ---------------------------------------------------------
# 全域 Demo 資料預載 (確保首頁開啟時即擁有數據)
# ---------------------------------------------------------
DEMO_FILE_PATH = PROJECT_ROOT / "assets" / "3-4月活動成效表_v2.xlsx"

if "is_demo_mode" not in st.session_state:
    st.session_state["is_demo_mode"] = True
    st.session_state["demo_file_path"] = str(DEMO_FILE_PATH)

if "sales_data" not in st.session_state and DEMO_FILE_PATH.exists():
    try:
        xls = pd.ExcelFile(DEMO_FILE_PATH)
        st.session_state["sales_data"] = pd.read_excel(
            xls, sheet_name="銷量原始資料(零填補)"
        )
        if "活動單位清單(依時間)" in xls.sheet_names:
            st.session_state["events_data"] = pd.read_excel(
                xls, sheet_name="活動單位清單(依時間)"
            )
    except Exception:
        pass

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


# 側邊欄自動收合
st.markdown(
    _render_template("sidebar_collapse.html"),
    unsafe_allow_html=True,
)

# =========================================================
# 首頁重點功能與統計數字 (已更新 SKU 規模為 10,000+)
# =========================================================

HERO_FEATURES = [
    (
        "search",
        "orange",
        "AI 活動洞察",
        "揪出高低成效檔期與成效風險",
    ),
    (
        "show_chart",
        "blue",
        "活動情境模擬",
        "促銷方案比較預估 ROI 與營收",
    ),
    (
        "lightbulb",
        "magenta",
        "策略行動建議",
        "一鍵生成 LINE/Email 促銷文案",
    ),
    (
        "picture_as_pdf",
        "green",
        "電商主管報表",
        "一鍵匯出 AI 策略與成效 PDF",
    ),
]

HERO_STATS = [
    ("📊", "orange", "20+", "電商活動拆解案例"),
    ("🧮", "blue", "10,000+", "活動 SKU 規模"),  # 已更新為 10,000+
    ("🤖", "magenta", "24/7", "AI 活動洞察待命"),
    ("🏬", "green", "600+", "合作實體與線上門市"),
]

# =========================================================
# 1. 保留原本完整 Hero 視覺與 HTML 樣板渲染
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

# 渲染 HTML Hero 主視覺
st.markdown(
    _render_template(
        "home_hero.html",
        FEATURE_CARDS_HTML=feature_cards_html,
        STAT_ITEMS_HTML=stat_items_html,
        ORB_HTML=orb_html,
    ),
    unsafe_allow_html=True,
)

# CTA 按鈕區塊 (一鍵 Demo 資料觸發)
cta_col1, cta_col2 = st.columns([1, 1])
with cta_col1:
    start_exploring = st.button(
        "開始探索活動策略 →",
        type="primary",
        use_container_width=True,
    )
with cta_col2:
    start_demo = st.button(
        "🚀 載入活動 Demo 示範資料",
        type="secondary",
        use_container_width=True,
    )

if start_exploring or start_demo:
    if start_demo:
        st.session_state["is_demo_mode"] = True
        st.session_state["demo_file_path"] = str(DEMO_FILE_PATH)
    st.switch_page("app_pages/15_資料管理中心.py")

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# 2. Executive Brief (競賽簡報核心區)
# =========================================================

st.markdown(
    """
<style>
    .exec-brief-wrapper {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        margin-bottom: 24px;
    }
    .brief-title {
        font-size: 20px;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .kpi-mini-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .kpi-mini-title {
        font-size: 13px;
        color: #64748B;
        font-weight: 500;
    }
    .kpi-mini-val {
        font-size: 26px;
        font-weight: 800;
        margin: 6px 0;
    }
    .kpi-health { color: #10B981; }
    .kpi-risk { color: #EF4444; }
    .kpi-pending { color: #F59E0B; }
    .kpi-forecast { color: #3B82F6; }

    .ai-rec-banner {
        background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%);
        border-left: 5px solid #F97316;
        border-radius: 10px;
        padding: 16px 20px;
        margin: 20px 0;
    }
    .ai-rec-head {
        color: #C2410C;
        font-weight: 700;
        font-size: 14px;
    }
    .ai-rec-body {
        font-size: 15px;
        color: #1F2937;
        font-weight: 600;
        margin-top: 4px;
    }
    .ai-rec-evidence {
        font-size: 12px;
        color: #6B7280;
        margin-top: 6px;
    }

    .decision-row {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="exec-brief-wrapper">
    <div class="brief-title">
        <span>⚡ Executive Brief | 今日活動決策簡報 (AI Executive Brief)</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# 4 大活動監控指標
b1, b2, b3, b4 = st.columns(4)
with b1:
    st.markdown(
        """
    <div class="kpi-mini-card">
        <div class="kpi-mini-title">活動健康度 Health</div>
        <div class="kpi-mini-val kpi-health">92</div>
        <div style="font-size: 11px; color: #10B981;">+4 vs. 上一檔</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with b2:
    st.markdown(
        """
    <div class="kpi-mini-card">
        <div class="kpi-mini-title">活動風險警示 Risk</div>
        <div class="kpi-mini-val kpi-risk">2</div>
        <div style="font-size: 11px; color: #EF4444;">轉換率下滑/缺貨</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with b3:
    st.markdown(
        """
    <div class="kpi-mini-card">
        <div class="kpi-mini-title">待執行策略 Decision</div>
        <div class="kpi-mini-val kpi-pending">3</div>
        <div style="font-size: 11px; color: #F59E0B;">今日待審核</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with b4:
    st.markdown(
        """
    <div class="kpi-mini-card">
        <div class="kpi-mini-title">下一檔預估 Forecast</div>
        <div class="kpi-mini-val kpi-forecast">+8.2%</div>
        <div style="font-size: 11px; color: #3B82F6;">預估營收成長</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# AI 主動活動建議
st.markdown(
    """
<div class="ai-rec-banner">
    <div class="ai-rec-head">💡 AI 主動活動策略建議</div>
    <div class="ai-rec-body">優先處理轉換率連續下降之促銷品項，預估可改善檔期營收 6 – 9%。</div>
    <div class="ai-rec-evidence">數據證據：本週活動行動版結帳流失率高於桌機 18%，熱銷 SKU 預估 5 天後缺貨。(AI 信心度: 91%)</div>
</div>
""",
    unsafe_allow_html=True,
)

# 活動決策隊列
st.markdown("##### 🎯 待審核活動策略隊列 (Decision Queue)")

dq1, dq2 = st.columns([3, 1])
with dq1:
    st.markdown(
        """
    <div class="decision-row">
        <div>
            <span style="background:#FEE2E2; color:#DC2626; font-size:11px; font-weight:700; padding:2px 6px; border-radius:4px;">High Impact</span>
            <strong style="margin-left:8px; font-size:14px; color:#1E293B;">01 促銷商品補貨與加碼：高流量活動品項 5 天後缺貨</strong>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
with dq2:
    if st.button("Approve 採納策略", key="app_1", use_container_width=True):
        st.success("已自動帶入補貨清單並生成推播文案！")

dq3, dq4 = st.columns([3, 1])
with dq3:
    st.markdown(
        """
    <div class="decision-row">
        <div>
            <span style="background:#E0F2FE; color:#0369A1; font-size:11px; font-weight:700; padding:2px 6px; border-radius:4px;">Medium Impact</span>
            <strong style="margin-left:8px; font-size:14px; color:#1E293B;">02 活動頁面優化：行動端結帳漏鬥流失率調整</strong>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
with dq4:
    if st.button("Review 檢視洞察", key="rev_1", use_container_width=True):
        st.switch_page("app_pages/20_AI洞察與建議.py")

# Prompt Chips
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("##### 💬 一鍵 AI 活動策略查詢 (Prompt Chips)")
p1, p2, p3, p4 = st.columns(4)
with p1:
    if st.button("為什麼本檔期營收下降？", use_container_width=True):
        st.info(
            "🤖 **AI 原因分析**：主因非流量下滑，而是行動版付款頁面流失率上升 12%。"
        )
with p2:
    if st.button("潛在最大促銷機會？", use_container_width=True):
        st.info(
            "🤖 **AI 機會點**：組合銷售配件套裝可提升平均客單價 15%。"
        )
with p3:
    if st.button("活動庫存風險評估", use_container_width=True):
        st.info("🤖 **AI 風險提醒**：Top 3 熱銷活動 SKU 庫存僅剩 4 天可售。")
with p4:
    if st.button("預估下檔活動 ROI", use_container_width=True):
        st.info(
            "🤖 **AI 趨勢預測**：若提高 10% 廣告預算，預估整體營收成長 +8.2%。"
        )
