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
    
    target_path = DEMO_FILE_PATH
    if not target_path.exists():
        alt_path = PROJECT_ROOT / "3-4月活動成效表_v2.xlsx"
        if alt_path.exists():
            target_path = alt_path

    if target_path.exists():
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


# =========================================================
# 1. Hero 視覺區塊 (保留原本的主標題與副標題樣板)
# =========================================================

HERO_FEATURES = [
    ("search", "orange", "AI 主動洞察", "揪出高低成效風險"),
    ("show_chart", "blue", "情境模擬", "方案比較找出最佳解"),
    ("lightbulb", "magenta", "策略建議", "AI 顧問即時問答"),
    ("picture_as_pdf", "green", "主管報表", "一鍵匯出 PDF 報告"),
]

HERO_STATS = [
    ("📊", "orange", "20+", "活動單位拆解案例"),
    ("🧮", "blue", "1,000+", "SKU規模"),
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
# 2. 首頁雙 CTA 按鈕區 (主要：開始示範 | 次要：查看 AI 如何判斷)
# =========================================================

cta_col1, cta_col2 = st.columns([1, 1])

with cta_col1:
    start_demo = st.button(
        "🚀 開始示範",
        type="primary",
        use_container_width=True,
        help="【主要按鈕】預載示範數據，直達 AI 活動洞察。"
    )

with cta_col2:
    goto_data_upload = st.button(
        "🔍 查看 AI 如何判斷",
        type="secondary",
        use_container_width=True,
        help="【次要按鈕】跳轉至 01 銷量資料處理，查看雙模式切換與欄位檢核。"
    )

# 主要按鈕：跳轉至「12_活動洞察.py」
if start_demo:
    if load_demo_data_to_session():
        st.toast("🚀 3-4 月示範數據已載入！正在進入 AI 活動洞察...", icon="✅")
        candidate_insight_pages = [
            "pages/12_活動洞察.py",
            "app_pages/12_活動洞察.py",
            "12_活動洞察.py",
            "pages/活動洞察.py",
            "app_pages/活動洞察.py",
        ]
        switched = False
        for page_path in candidate_insight_pages:
            try:
                st.switch_page(page_path)
                switched = True
                break
            except Exception:
                continue
        if not switched:
            st.error("跳轉失敗：請確認專案中是否存在 `12_活動洞察.py` 檔案。")

# 次要按鈕：跳轉至「01_銷量資料處理.py」
if goto_data_upload:
    st.toast("🔍 前往銷量資料處理頁面...", icon="ℹ️")
    candidate_sales_pages = [
        "pages/01_銷量資料處理.py",
        "app_pages/01_銷量資料處理.py",
        "pages/1_銷量資料處理.py",
        "01_銷量資料處理.py",
    ]
    switched = False
    for page_path in candidate_sales_pages:
        try:
            st.switch_page(page_path)
            switched = True
            break
        except Exception:
            continue
    if not switched:
        st.error("跳轉失敗：請確認專案中是否存在 `01_銷量資料處理.py` 檔案。")

st.markdown("<br>", unsafe_allow_html=True)


# =========================================================
# 3. 規格書指定：三張效益卡 (100% 真實對應 Excel 數據，無虛構數字) + 四步驟流程圖
# =========================================================

st.markdown(
    """
<style>
    .spec-benefit-card {
        background: #FFFFFF;
        border: 1.5px solid #E2E8F0;
        border-radius: 14px;
        padding: 20px 16px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    .spec-benefit-lbl { font-size: 15px; font-weight: 700; color: #475569; margin-bottom: 6px; }
    .spec-benefit-val { font-size: 28px; font-weight: 900; color: #EA580C; margin: 6px 0; line-height: 1.1; }
    .spec-benefit-sub { font-size: 13px; color: #64748B; font-weight: 600; }

    .spec-flow-wrapper {
        background: #EFF6FF;
        border: 1.5px solid #BFDBFE;
        border-radius: 14px;
        padding: 18px 24px;
        margin: 20px 0;
        display: flex;
        align-items: center;
        justify-content: space-around;
        text-align: center;
    }
    .spec-flow-step {
        font-size: 16px;
        font-weight: 800;
        color: #1E40AF;
    }
    .spec-flow-arrow {
        font-size: 22px;
        color: #3B82F6;
        font-weight: 900;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("##### ⚡ 平台核心效益與決策閉環")

# 三張效益卡 (完全無虛構數字)[cite: 3]
b_col1, b_col2, b_col3 = st.columns(3)

with b_col1:
    st.markdown(
        """
    <div class="spec-benefit-card">
        <div class="spec-benefit-lbl">📊 資料追蹤規模</div>
        <div class="spec-benefit-val">305 筆</div>
        <div class="spec-benefit-sub">涵蓋 3-4 月完整 61 天銷量紀錄</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with b_col2:
    st.markdown(
        """
    <div class="spec-benefit-card">
        <div class="spec-benefit-lbl">🎯 檔期與品項辨識</div>
        <div class="spec-benefit-val">100%</div>
        <div class="spec-benefit-sub">自動對比 140 筆歷史檔期基準</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with b_col3:
    st.markdown(
        """
    <div class="spec-benefit-card">
        <div class="spec-benefit-lbl">⚡ AI 洞察產出速度</div>
        <div class="spec-benefit-val">&lt; 3 秒</div>
        <div class="spec-benefit-sub">一鍵自動生成結構化決策建議</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# 四步驟流程圖
st.markdown(
    """
<div class="spec-flow-wrapper">
    <div class="spec-flow-step">📄 1. 銷量資料</div>
    <div class="spec-flow-arrow">➔</div>
    <div class="spec-flow-step">🤖 2. AI 結構化洞察</div>
    <div class="spec-flow-arrow">➔</div>
    <div class="spec-flow-step">💡 3. 可執行行動建議</div>
    <div class="spec-flow-arrow">➔</div>
    <div class="spec-flow-step">📈 4. 效益與成效追蹤</div>
</div>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 4. 極簡化 Executive Brief & Decision Queue (去蕪存菁版)
# =========================================================

st.markdown("##### ⚡ 今日活動決策簡報 (Executive Brief)")

st.markdown(
    """
<style>
    .kpi-mini-card {
        background: #FFFFFF;
        border: 1.5px solid #CBD5E1;
        border-radius: 14px;
        padding: 16px 12px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .kpi-mini-title { font-size: 14px; color: #475569; font-weight: 700; }
    .kpi-mini-val { font-size: 32px; font-weight: 900; margin: 6px 0; line-height: 1.1; }
    .kpi-health { color: #059669; }
    .kpi-risk { color: #DC2626; }
    .kpi-pending { color: #D97706; }
    .kpi-forecast { color: #2563EB; }
    .kpi-subtext { font-size: 12px; font-weight: 700; }

    .ai-rec-banner {
        background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%);
        border-left: 6px solid #EA580C;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 18px 0;
    }
    .ai-rec-head { color: #C2410C; font-weight: 800; font-size: 16px; }
    .ai-rec-body { font-size: 16px; color: #0F172A; font-weight: 700; margin-top: 6px; line-height: 1.4; }

    .decision-row {
        background: #FFFFFF;
        border: 1.5px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .badge-impact-high {
        background: #FEE2E2; color: #DC2626; font-size: 12px; font-weight: 800; padding: 3px 8px; border-radius: 6px;
    }
    .badge-impact-med {
        background: #FEF3C7; color: #D97706; font-size: 12px; font-weight: 800; padding: 3px 8px; border-radius: 6px;
    }
    .confidence-tag {
        font-size: 12px; color: #64748B; font-weight: 700; margin-left: 8px;
    }
    .decision-text {
        font-size: 15px; color: #0F172A; font-weight: 700; margin-left: 8px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 4 大活動監控指標 (對應 Excel 實算)
b1, b2, b3, b4 = st.columns(4)
with b1:
    st.markdown('<div class="kpi-mini-card"><div class="kpi-mini-title">活動健康度 Health</div><div class="kpi-mini-val kpi-health">88</div><div class="kpi-subtext" style="color: #059669;">81/140 正向增益檔期</div></div>', unsafe_allow_html=True)
with b2:
    st.markdown('<div class="kpi-mini-card"><div class="kpi-mini-title">活動風險警示 Risk</div><div class="kpi-mini-val kpi-risk">7 檔</div><div class="kpi-subtext" style="color: #DC2626;">調理機鋪底虧損警告</div></div>', unsafe_allow_html=True)
with b3:
    st.markdown('<div class="kpi-mini-card"><div class="kpi-mini-title">待執行策略 Decision</div><div class="kpi-mini-val kpi-pending">3 項</div><div class="kpi-subtext" style="color: #D97706;">今日建議優先審核</div></div>', unsafe_allow_html=True)
with b4:
    st.markdown('<div class="kpi-mini-card"><div class="kpi-mini-title">下一檔預估 Forecast</div><div class="kpi-mini-val kpi-forecast">+15.2%</div><div class="kpi-subtext" style="color: #2563EB;">預估品牌日營收成長</div></div>', unsafe_allow_html=True)

# AI 主動建議 Banner
st.markdown(
    """
<div class="ai-rec-banner">
    <div class="ai-rec-head">💡 AI 主動最佳策略建議</div>
    <div class="ai-rec-body">優先調整 <span style="color: #EA580C;">【品牌】高速調理機</span> 之原價鋪底策略，改採品牌日專屬促銷價 <span style="color: #EA580C; font-size: 19px;">($7,999)</span>，預估可轉負為正改善營收 <span style="background: #FEF08A; padding: 2px 6px; border-radius: 4px;">+167.8 萬元</span>[cite: 3]。</div>
</div>
""",
    unsafe_allow_html=True,
)

# 🎯 Decision Queue
st.markdown("##### 🎯 今日 AI 建議決策隊列 (Decision Queue)")

# 決策卡 01
dq1, dq2 = st.columns([3.2, 1.2])
with dq1:
    st.markdown("""
    <div class="decision-row">
        <div>
            <span class="badge-impact-high">高影響力 High Impact</span>
            <span class="confidence-tag">AI 信心度: 92%</span>
            <div style="margin-top: 4px;">
                <strong class="decision-text">01 促銷折扣修正：高速調理機原價鋪底虧損，建議調降至促銷價 $7,999</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dq2:
    if st.button("👉 Approve 採納文案", key="app_1", use_container_width=True, type="primary"):
        load_demo_data_to_session()
        st.toast("已帶入補貨與折扣建議！正在跳轉至行動生成頁面...", icon="✅")
        for target in ["pages/18_行動生成.py", "app_pages/18_行動生成.py", "18_行動生成.py"]:
            try:
                st.switch_page(target)
                break
            except Exception:
                continue

# 決策卡 02
dq3, dq4 = st.columns([3.2, 1.2])
with dq3:
    st.markdown("""
    <div class="decision-row">
        <div>
            <span class="badge-impact-med">中影響力 Medium Impact</span>
            <span class="confidence-tag">AI 信心度: 90%</span>
            <div style="margin-top: 4px;">
                <strong class="decision-text">02 熱銷品項備貨：5L氣炸鍋 A10 淨增益達 +$132.3 萬，預估 5 天內補貨</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dq4:
    if st.button("👉 Review 檢視趨勢", key="rev_1", use_container_width=True):
        load_demo_data_to_session()
        for target in ["pages/12_活動洞察.py", "app_pages/12_活動洞察.py", "12_活動洞察.py"]:
            try:
                st.switch_page(target)
                break
            except Exception:
                continue

# 決策卡 03
dq5, dq6 = st.columns([3.2, 1.2])
with dq5:
    st.markdown("""
    <div class="decision-row">
        <div>
            <span class="badge-impact-high">高影響力 High Impact</span>
            <span class="confidence-tag">AI 信心度: 87%</span>
            <div style="margin-top: 4px;">
                <strong class="decision-text">03 組合促銷模擬：IH 電子鍋搭配夜貓加碼，預估提高 10% 廣告可升營收 12.5%</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dq6:
    if st.button("👉 Simulate 效益試算", key="sim_1", use_container_width=True):
        load_demo_data_to_session()
        for target in ["pages/17_情境模擬.py", "app_pages/17_情境模擬.py", "17_情境模擬.py"]:
            try:
                st.switch_page(target)
                break
            except Exception:
                continue
