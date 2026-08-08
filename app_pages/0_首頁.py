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
# 數據預載邏輯函式 (解析 3-4 月活動成效 Excel 數據)
# =========================================================

def load_demo_data_to_session():
    """將 3-4 月銷量活動數據預先讀取並存入 Streamlit Session State"""
    st.session_state["is_demo_mode"] = True
    st.session_state["demo_file_path"] = str(DEMO_FILE_PATH)
    
    # 優先尋找預載路徑或專案根目錄的 Excel 備援檔
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
        st.error(f"找不到數據檔案，請確認 `assets/demo_sales_data.xlsx` 或 `3-4月活動成效表_v2.xlsx` 是否存在。")
        return False


# =========================================================
# 1. Hero 視覺區塊 (對應 Excel 實測背景數據)
# =========================================================

HERO_FEATURES = [
    ("search", "orange", "AI 主動洞察", "揪出高低成效檔期與成效風險"),
    ("show_chart", "blue", "情境模擬", "促銷方案比較預估 ROI 與營收"),
    ("lightbulb", "magenta", "策略建議", "一鍵生成 LINE/Email 促銷文案"),
    ("picture_as_pdf", "green", "主管報表", "一鍵匯出 AI 策略與成效 PDF"),
]

HERO_STATS = [
    ("📊", "orange", "28 檔", "3-4月活動單位拆解"),
    ("🧮", "blue", "305 筆", "每日銷量追蹤規模"),
    ("🤖", "magenta", "2,093 萬", "NT$ 累積淨營收增益"),
    ("🏬", "green", "600+", "合作實體與線上門市"),
]

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

# =========================================================
# 2. CTA 按鈕區 (預載 3-4 月數據並連動跳轉)
# =========================================================

cta_col1, cta_col2 = st.columns([1, 1])

with cta_col1:
    start_exploring = st.button(
        "開始探索活動策略 →",
        type="primary",
        use_container_width=True,
    )

with cta_col2:
    start_demo = st.button(
        "🚀 載入 3-4 月數據並進行活動洞察",
        type="secondary",
        use_container_width=True,
    )

if start_demo or start_exploring:
    if load_demo_data_to_session():
        st.toast("🚀 3-4 月銷量活動數據已就緒！正在進入活動洞察...", icon="✅")
        try:
            st.switch_page("app_pages/12_活動洞察.py")
        except Exception:
            try:
                st.switch_page("12_活動洞察.py")
            except Exception as e:
                st.error(f"跳轉失敗，請確認檔案路徑：{e}")

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# 3. Executive Brief (基於 3-4 月 Excel 實測之今日決策簡報)
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
    .kpi-mini-title { font-size: 13px; color: #64748B; font-weight: 500; }
    .kpi-mini-val { font-size: 26px; font-weight: 800; margin: 6px 0; }
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
    .ai-rec-head { color: #C2410C; font-weight: 700; font-size: 14px; }
    .ai-rec-body { font-size: 15px; color: #1F2937; font-weight: 600; margin-top: 4px; }
    .ai-rec-evidence { font-size: 12px; color: #6B7280; margin-top: 6px; }

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
    .badge-impact-high {
        background: #FEE2E2; color: #DC2626; font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px;
    }
    .badge-impact-med {
        background: #FEF3C7; color: #D97706; font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px;
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

# 4 大活動監控指標 (緊扣 Excel 的 28 檔與 140 個單位分析)
b1, b2, b3, b4 = st.columns(4)
with b1:
    st.markdown('<div class="kpi-mini-card"><div class="kpi-mini-title">活動健康度 Health</div><div class="kpi-mini-val kpi-health">88</div><div style="font-size: 11px; color: #10B981;">81/140 正向增益檔期</div></div>', unsafe_allow_html=True)
with b2:
    st.markdown('<div class="kpi-mini-card"><div class="kpi-mini-title">活動風險警示 Risk</div><div class="kpi-mini-val kpi-risk">7</div><div style="font-size: 11px; color: #EF4444;">調理機鋪底虧損檔期</div></div>', unsafe_allow_html=True)
with b3:
    st.markdown('<div class="kpi-mini-card"><div class="kpi-mini-title">待執行策略 Decision</div><div class="kpi-mini-val kpi-pending">3</div><div style="font-size: 11px; color: #F59E0B;">今日待審核</div></div>', unsafe_allow_html=True)
with b4:
    st.markdown('<div class="kpi-mini-card"><div class="kpi-mini-title">下一檔預估 Forecast</div><div class="kpi-mini-val kpi-forecast">+15.2%</div><div style="font-size: 11px; color: #3B82F6;">預估品牌日營收增益</div></div>', unsafe_allow_html=True)

# AI 主動建議 Banner
st.markdown(
    """
<div class="ai-rec-banner">
    <div class="ai-rec-head">💡 AI 主動活動策略建議</div>
    <div class="ai-rec-body">優先調整【品牌】高速調理機之原價鋪底策略，改採品牌日專屬促銷價 ($7,999)，預估可轉負為正改善營收 +167.8 萬元。</div>
    <div class="ai-rec-evidence">數據證據：Excel 顯示調理機在 M2/M7 原價 ($8,990) 淨增益為 -$14.38 萬，但在 A10 降至 $7,999 帶動單檔 +$167.8 萬增益。(AI 信心度: 92%)</div>
</div>
""",
    unsafe_allow_html=True,
)

# 🎯 Decision Queue (緊扣 3-4月活動成效表數據)
st.markdown("##### 🎯 待審核活動策略隊列 (Decision Queue)")

dq1, dq2 = st.columns([3.5, 1])
with dq1:
    st.markdown("""
    <div class="decision-row">
        <div>
            <span class="badge-impact-high">Impact: High</span>
            <span style="font-size: 11px; color: #64748B; margin-left: 6px;">Confidence: 92%</span>
            <strong style="margin-left:8px; font-size:14px; color:#1E293B;">01 促銷折扣修正：高速調理機原價鋪底虧損，建議調降至促銷價 $7,999</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dq2:
    if st.button("Approve 採納策略", key="app_1", use_container_width=True):
        load_demo_data_to_session()
        st.toast("已帶入補貨與折扣建議！正在跳轉至行動生成頁面...", icon="✅")
        try:
            st.switch_page("app_pages/18_行動生成.py")
        except Exception:
            pass

dq3, dq4 = st.columns([3.5, 1])
with dq3:
    st.markdown("""
    <div class="decision-row">
        <div>
            <span class="badge-impact-med">Impact: Medium</span>
            <span style="font-size: 11px; color: #64748B; margin-left: 6px;">Confidence: 90%</span>
            <strong style="margin-left:8px; font-size:14px; color:#1E293B;">02 熱銷品項備貨：5L氣炸鍋 A10 檔期淨增益高達 +$132.3 萬，預估 5 天內補貨</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dq4:
    if st.button("Review 檢視洞察", key="rev_1", use_container_width=True):
        load_demo_data_to_session()
        try:
            st.switch_page("app_pages/12_活動洞察.py")
        except Exception:
            pass

dq5, dq6 = st.columns([3.5, 1])
with dq5:
    st.markdown("""
    <div class="decision-row">
        <div>
            <span class="badge-impact-high">Impact: High</span>
            <span style="font-size: 11px; color: #64748B; margin-left: 6px;">Confidence: 87%</span>
            <strong style="margin-left:8px; font-size:14px; color:#1E293B;">03 組合促銷模擬：IH 電子鍋搭配廚電日夜貓加碼，預估提高 10% 廣告可提升營收 12.5%</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dq6:
    if st.button("Simulate 情境模擬", key="sim_1", use_container_width=True):
        load_demo_data_to_session()
        try:
            st.switch_page("app_pages/17_情境模擬.py")
        except Exception:
            pass

# Prompt Chips (緊扣 3-4 月真實數據問答)
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("##### 💬 一鍵 AI 活動策略查詢 (Prompt Chips)")
p1, p2, p3, p4 = st.columns(4)
with p1:
    if st.button("為什麼高速調理機在 3 月初營收下滑？", use_container_width=True):
        st.info("🤖 **AI 原因分析**：主因 M2/M7 檔期維護代理牌價 $8,990 缺乏促銷誘因，每日淨營收效應為 -NT$14.38 萬。\n\n📌 **數據證據**：銷量原始資料顯示無活動折扣時每日銷量為 0，降價至 $7,999 後銷量提升至每日 8~10 台。")
with p2:
    if st.button("3-4 月成效最高的活動是哪一檔？", use_container_width=True):
        st.info("🤖 **AI 機會點**：A10 品牌日（含夜貓加碼與平台折價券）為成效冠軍。\n\n📌 **數據證據**：單檔帶動高速調理機 +NT$167.8 萬增益、氣炸鍋 +NT$132.3 萬增益。")
with p3:
    if st.button("哪些品項最值得在下一檔加碼？", use_container_width=True):
        st.info("🤖 **AI 風險與加碼提醒**：【品牌】5L氣炸鍋 與 IH8人份電子鍋為營收雙核心。\n\n📌 **數據證據**：歷史累積淨營收增益分別高達 +NT$689.8 萬與 +NT$401.9 萬。")
with p4:
    if st.button("預估下檔品牌日 ROI", use_container_width=True):
        st.info("🤖 **AI 趨勢預測**：若在品牌日追加 10% 廣告行銷預算，預估整體營收成長 +15.2%。\n\n📌 **數據證據**：情境模擬模型信心度 89% (預期淨邊際收益 +5.4%)。")
