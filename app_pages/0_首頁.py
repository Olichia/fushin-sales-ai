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
# 1. Hero 視覺區塊
# =========================================================

HERO_FEATURES = [
    ("search", "orange", "AI 主動洞察", "揪出高低成效檔期與成效風險"),
    ("show_chart", "blue", "情境模擬", "促銷方案比較預估 ROI 與營收"),
    ("lightbulb", "magenta", "策略建議", "一鍵生成 LINE/Email 促銷文案"),
    ("picture_as_pdf", "green", "主管報表", "一鍵匯出 AI 策略與成效 PDF"),
]

HERO_STATS = [
    ("📊", "orange", "20+", "活動單位拆解案例"),
    ("🧮", "blue", "10,000+", "活動 SKU 規模"),
    ("🤖", "magenta", "24/7", "AI 洞察待命"),
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
# 2. 規格書指定：三張效益卡 + 四步驟流程圖 (明確出現在按鈕上方)
# =========================================================

st.markdown(
    """
<style>
    .spec-benefit-card {
        background: #F8FAFC;
        border: 1.5px solid #CBD5E1;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .spec-benefit-val { font-size: 26px; font-weight: 800; color: #EA580C; margin: 4px 0; }
    .spec-benefit-lbl { font-size: 15px; font-weight: 700; color: #1E293B; }
    .spec-benefit-sub { font-size: 12px; color: #64748B; font-weight: 600; }

    .spec-flow-wrapper {
        background: #EFF6FF;
        border: 1.5px solid #BFDBFE;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 20px 0;
        display: flex;
        align-items: center;
        justify-content: space-around;
        text-align: center;
    }
    .spec-flow-step { font-size: 16px; font-weight: 800; color: #1E40AF; }
    .spec-flow-arrow { font-size: 20px; color: #3B82F6; font-weight: 900; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("##### ⚡ 平台核心效益與決策閉環")

# 三張效益卡 (規格書明確規定)
ef1, ef2, spec_ef3 = st.columns(3)
with ef1:
    st.markdown('<div class="spec-benefit-card"><div class="spec-benefit-lbl">⏱️ 分析時間節省</div><div class="spec-benefit-val">12.4分 ➔ 4.1分</div><div class="spec-benefit-sub">效率提升 67% (n=8 實測)</div></div>', unsafe_allow_html=True)
with ef2:
    st.markdown('<div class="spec-benefit-card"><div class="spec-benefit-lbl">🎯 重點品項辨識</div><div class="spec-benefit-val">100%</div><div class="spec-benefit-sub">精準抓出虧損與爆款檔期</div></div>', unsafe_allow_html=True)
with spec_ef3:
    st.markdown('<div class="spec-benefit-card"><div class="spec-benefit-lbl">⚡ 策略建議產出</div><div class="spec-benefit-val">&lt; 3 秒</div><div class="spec-benefit-sub">一鍵自動生成執行內容</div></div>', unsafe_allow_html=True)

# 四步驟流程圖 (規格書明確規定)
st.markdown(
    """
<div class="spec-flow-wrapper">
    <div class="spec-flow-step">1. 銷量資料</div>
    <div class="spec-flow-arrow">➔</div>
    <div class="spec-flow-step">2. AI 結構化洞察</div>
    <div class="spec-flow-arrow">➔</div>
    <div class="spec-flow-step">3. 可執行行動建議</div>
    <div class="spec-flow-arrow">➔</div>
    <div class="spec-flow-step">4. 效益與成效追蹤</div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================================================
# 3. 首頁雙按鈕區
# =========================================================

cta_col1, cta_col2 = st.columns([1, 1])

with cta_col1:
    start_demo = st.button(
        "🚀 開始示範",
        type="primary",
        use_container_width=True,
        help="【Demo 極速通道】背景預載 3-4 月示範數據，直達 AI 活動洞察。"
    )

with cta_col2:
    goto_data_upload = st.button(
        "🔍 查看 AI 如何判斷",
        type="secondary",
        use_container_width=True,
        help="【合規檢查】查看數據檢核卡片與雙模式切換。"
    )

# 1. 主要按鈕：直達 AI 活動洞察
if start_demo:
    if load_demo_data_to_session():
        st.toast("🚀 3-4 月示範數據已載入！正在進入 AI 活動洞察...", icon="✅")
        try:
            st.switch_page("app_pages/12_活動洞察.py")
        except Exception:
            try:
                st.switch_page("app_pages/活動洞察.py")
            except Exception as e:
                st.error(f"跳轉失敗：{e}")

# 2. 次要按鈕：跳轉至資料處理與檢核頁面
if goto_data_upload:
    st.toast("🔍 前往資料處理與品質檢核頁面...", icon="ℹ️")
    try:
        st.switch_page("app_pages/01_銷量資料處理.py")
    except Exception:
        try:
            st.switch_page("app_pages/15_資料管理中心.py")
        except Exception as e:
            st.error(f"跳轉失敗：{e}")

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# 4. Executive Brief & Decision Queue
# =========================================================

st.markdown(
    """
<style>
    .exec-brief-wrapper {
        background: #FFFFFF;
        border: 2px solid #E2E8F0;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06);
        margin-bottom: 24px;
    }
    .brief-title {
        font-size: 24px;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .brief-subtitle-badge {
        background: #EFF6FF;
        color: #2563EB;
        font-size: 13px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        margin-left: 8px;
    }
    .kpi-mini-card {
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 14px;
        padding: 18px 12px;
        text-align: center;
    }
    .kpi-mini-title { font-size: 15px; color: #475569; font-weight: 700; }
    .kpi-mini-val { font-size: 36px; font-weight: 900; margin: 8px 0; line-height: 1.1; }
    .kpi-health { color: #059669; }
    .kpi-risk { color: #DC2626; }
    .kpi-pending { color: #D97706; }
    .kpi-forecast { color: #2563EB; }
    .kpi-subtext { font-size: 13px; font-weight: 700; }

    .ai-rec-banner {
        background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%);
        border-left: 6px solid #EA580C;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 24px 0;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.08);
    }
    .ai-rec-head { color: #C2410C; font-weight: 800; font-size: 17px; }
    .ai-rec-body { font-size: 17px; color: #0F172A; font-weight: 700; margin-top: 8px; line-height: 1.5; }
    .ai-rec-evidence { font-size: 14px; color: #475569; margin-top: 10px; background: rgba(255,255,255,0.75); padding: 8px 12px; border-radius: 6px; border: 1px solid #FED7AA; }

    .decision-row {
        background: #FFFFFF;
        border: 1.5px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .badge-impact-high {
        background: #FEE2E2; color: #DC2626; font-size: 13px; font-weight: 800; padding: 4px 10px; border-radius: 6px;
    }
    .badge-impact-med {
        background: #FEF3C7; color: #D97706; font-size: 13px; font-weight: 800; padding: 4px 10px; border-radius: 6px;
    }
    .confidence-tag {
        font-size: 13px; color: #64748B; font-weight: 700; margin-left: 8px;
    }
    .decision-text {
        font-size: 16px; color: #0F172A; font-weight: 700; margin-left: 10px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Executive Brief 標題
st.markdown(
    """
<div class="exec-brief-wrapper">
    <div class="brief-title">
        <span>⚡ Executive Brief | 今日活動決策簡報 (AI 實時總覽)</span>
        <span class="brief-subtitle-badge">🤖 AI 主動診斷</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# 4 大活動監控指標
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
    <div class="ai-rec-body">優先調整 <span style="color: #EA580C;">【品牌】高速調理機</span> 之原價鋪底策略，改採品牌日專屬促銷價 <span style="color: #EA580C; font-size: 19px;">($7,999)</span>，預估可轉負為正改善營收 <span style="background: #FEF08A; padding: 2px 6px; border-radius: 4px;">+167.8 萬元</span>。</div>
    <div class="ai-rec-evidence">🔍 <b>數據證據</b>：Excel 顯示調理機在 M2/M7 原價 ($8,990) 淨增益為 <b>-$14.38 萬</b>，但在 A10 品牌日降至 $7,999 帶動單檔 <b>+$167.8 萬增益</b>。(AI 信心度: <b>92%</b>)</div>
</div>
""",
    unsafe_allow_html=True,
)

# 🎯 Decision Queue
st.markdown("#### 🎯 今日 AI 建議決策隊列 (Decision Queue)")
st.caption("📌 **使用說明**：AI 依影響力與緊急度排定的建議事項。請點擊右側按鈕進行**一鍵採納、查看圖表或情境試算**。")

# 決策卡 01
dq1, dq2 = st.columns([3.2, 1.2])
with dq1:
    st.markdown("""
    <div class="decision-row">
        <div>
            <span class="badge-impact-high">高影響力 High Impact</span>
            <span class="confidence-tag">AI 信心度: 92%</span>
            <div style="margin-top: 6px;">
                <strong class="decision-text">01 促銷折扣修正：高速調理機原價鋪底虧損，建議調降至促銷價 $7,999</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dq2:
    if st.button("👉 Approve 採納並生成文案", key="app_1", use_container_width=True, type="primary"):
        load_demo_data_to_session()
        st.toast("已帶入補貨與折扣建議！正在跳轉至行動生成頁面...", icon="✅")
        try:
            st.switch_page("app_pages/18_行動生成.py")
        except Exception:
            pass

# 決策卡 02
dq3, dq4 = st.columns([3.2, 1.2])
with dq3:
    st.markdown("""
    <div class="decision-row">
        <div>
            <span class="badge-impact-med">中影響力 Medium Impact</span>
            <span class="confidence-tag">AI 信心度: 90%</span>
            <div style="margin-top: 6px;">
                <strong class="decision-text">02 熱銷品項備貨：5L氣炸鍋 A10 淨增益達 +$132.3 萬，預估 5 天內補貨</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dq4:
    if st.button("👉 Review 檢視數據趨勢", key="rev_1", use_container_width=True):
        load_demo_data_to_session()
        try:
            st.switch_page("app_pages/12_活動洞察.py")
        except Exception:
            pass

# 決策卡 03
dq5, dq6 = st.columns([3.2, 1.2])
with dq5:
    st.markdown("""
    <div class="decision-row">
        <div>
            <span class="badge-impact-high">高影響力 High Impact</span>
            <span class="confidence-tag">AI 信心度: 87%</span>
            <div style="margin-top: 6px;">
                <strong class="decision-text">03 組合促銷模擬：IH 電子鍋搭配夜貓加碼，預估提高 10% 廣告可升營收 12.5%</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with dq6:
    if st.button("👉 Simulate 情境效益試算", key="sim_1", use_container_width=True):
        load_demo_data_to_session()
        try:
            st.switch_page("app_pages/17_情境模擬.py")
        except Exception:
            pass

# Prompt Chips
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("#### 💬 一鍵 AI 策略問答 (點擊即刻回答)")
st.caption("📌 點擊以下常用問題按鈕，即時觀看 AI 分析結論與 Excel 數據證據：")

p1, p2, p3, p4 = st.columns(4)
with p1:
    if st.button("❓ 調理機 3 月為何下滑？", use_container_width=True):
        st.info("🤖 **AI 原因分析**：主因 M2/M7 檔期維護代理牌價 $8,990 缺乏促銷誘因，每日淨營收效應為 -NT$14.38 萬。\n\n📌 **數據證據**：銷量原始資料顯示無活動折扣時每日銷量為 0，降價至 $7,999 後銷量提升至每日 8~10 台。")
with p2:
    if st.button("🏆 哪一檔成效最高？", use_container_width=True):
        st.info("🤖 **AI 機會點**：A10 品牌日（含夜貓加碼與平台折價券）為成效冠軍。\n\n📌 **數據證據**：單檔帶動高速調理機 +NT$167.8 萬增益、氣炸鍋 +NT$132.3 萬增益。")
with p3:
    if st.button("🔥 哪些品項最值得加碼？", use_container_width=True):
        st.info("🤖 **AI 風險與加碼提醒**：【品牌】5L氣炸鍋 與 IH8人份電子鍋為營收雙核心。\n\n📌 **數據證據**：歷史累積淨營收增益分別高達 +NT$689.8 萬與 +NT$401.9 萬。")
with p4:
    if st.button("📈 預估下檔品牌日 ROI", use_container_width=True):
        st.info("🤖 **AI 趨勢預測**：若在品牌日追加 10% 廣告行銷預算，預估整體營收成長 +15.2%。\n\n📌 **數據證據**：情境模擬模型信心度 89% (預期淨邊際收益 +5.4%)。")
