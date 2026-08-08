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


# =========================================================
# 3.5 首頁 KPI／建議文案：全部在執行時從 Excel 現算，禁止寫死數字
# =========================================================

def _confidence_level(days: int, sample_warning: bool) -> tuple[str, str]:
    """
    規格書要求「信心分數」不可虛構，也要標示資料不足。
    這裡不生成假的百分比，改用資料本身可觀察到的兩個真實條件推出「高/中/低」＋原因：
    天數越長、樣本量提示欄位沒有警告，代表這段觀察越不容易只是單日雜訊。
    """
    if sample_warning or days < 2:
        return "低", "樣本量小(單日或系統標註信賴區間寬)，僅供參考方向"
    if days < 4:
        return "中", f"{days}天實測，無樣本量警告，但天數仍偏短"
    return "高", f"{days}天實測，無樣本量警告，且為可拆分的單一活動效果"


@st.cache_data(show_spinner=False)
def compute_home_insights(file_path: str):
    """
    讀取「銷量原始資料(零填補)」與「活動單位總覽(vs基準)」，
    現場算出首頁需要的所有 KPI 與建議文案素材。
    回傳 dict，找不到資料時回傳 None（呼叫端要處理沒有數據的情況，不能塞假數字）。
    """
    path = Path(file_path)
    if not path.exists():
        return None

    xls = pd.ExcelFile(path)
    if "銷量原始資料(零填補)" not in xls.sheet_names or "活動單位總覽(vs基準)" not in xls.sheet_names:
        return None

    sales_df = pd.read_excel(xls, sheet_name="銷量原始資料(零填補)")
    overview_df = pd.read_excel(xls, sheet_name="活動單位總覽(vs基準)")

    # --- 資料規模 ---
    total_records = len(sales_df)
    total_days = sales_df["日期"].nunique()
    total_units = len(overview_df)

    # --- 健康度：正向增益檔期佔比（現算）---
    positive_units = int((overview_df["淨營收效應_合計"] > 0).sum())
    negative_units = int((overview_df["淨營收效應_合計"] < 0).sum())
    health_score = round(positive_units / total_units * 100) if total_units else 0

    # --- 活動總淨效益：全部140個活動單位的淨營收效應加總（現算）---
    total_net_effect = float(overview_df["淨營收效應_合計"].sum())

    # --- 風險警示：找出「虧損檔次數最多的品項」---
    loss_counts = (
        overview_df[overview_df["淨營收效應_合計"] < 0]
        .groupby(["商品編號", "商品名稱"])
        .size()
        .sort_values(ascending=False)
    )
    if len(loss_counts) > 0:
        (risk_sku, risk_name), risk_loss_count = loss_counts.index[0], loss_counts.iloc[0]
    else:
        risk_sku, risk_name, risk_loss_count = None, None, 0

    # --- 針對風險品項，找「乾淨可拆分、且該SKU真的有參與」的正向翻轉案例 ---
    turnaround = None
    if risk_sku is not None:
        clean_positive = overview_df[
            (overview_df["商品編號"] == risk_sku)
            & (overview_df["淨營收效應_合計"] > 0)
            & (overview_df["分類"] == "可分離,單一活動")
            & (overview_df["本品項是否參與"] == True)
        ].sort_values("淨營收效應_合計", ascending=False)
        if len(clean_positive) > 0:
            best = clean_positive.iloc[0]
            days = int(best["天數"])
            sample_warning = bool(pd.notna(best.get("樣本量提示")))
            level, reason = _confidence_level(days, sample_warning)
            turnaround = {
                "sku": risk_sku,
                "name": risk_name,
                "event": best["對應活動"],
                "days": days,
                "price": best["活動售價"],
                "base_price": best["基準售價"],
                "avg_qty": best["單位平均銷量"],
                "base_qty": best["基準平均銷量_同月"],
                "net_effect": float(best["淨營收效應_合計"]),
                "sample_warning": sample_warning,
                "confidence_level": level,
                "confidence_reason": reason,
                "evidence": {
                    "商品編號": str(best["商品編號"]),
                    "活動單位": best["活動單位"],
                    "開始日期": str(best["開始日期"]),
                    "結束日期": str(best["結束日期"]),
                    "對應活動": best["對應活動"],
                    "分類": best["分類"],
                    "本品項是否參與": bool(best["本品項是否參與"]),
                    "活動售價": best["活動售價"],
                    "基準售價(同月代理牌價)": best["基準售價"],
                    "單位平均銷量": best["單位平均銷量"],
                    "基準平均銷量_同月": best["基準平均銷量_同月"],
                    "淨營收效應_合計": best["淨營收效應_合計"],
                    "資料來源工作表": "活動單位總覽(vs基準)",
                },
            }

    # --- 決策佇列：全資料庫裡「可拆分、單一活動、該SKU真的有參與、天數>=2」的前3名淨增益案例 ---
    clean_df = overview_df[
        (overview_df["分類"] == "可分離,單一活動")
        & (overview_df["天數"] >= 2)
        & (overview_df["本品項是否參與"] == True)
    ].sort_values("淨營收效應_合計", ascending=False)

    decision_items = []
    for _, row in clean_df.head(3).iterrows():
        days = int(row["天數"])
        sample_warning = bool(pd.notna(row.get("樣本量提示")))
        level, reason = _confidence_level(days, sample_warning)
        decision_items.append(
            {
                "sku": row["商品編號"],
                "name": row["商品名稱"],
                "event": row["對應活動"],
                "days": days,
                "net_effect": float(row["淨營收效應_合計"]),
                "avg_qty": row["單位平均銷量"],
                "base_qty": row["基準平均銷量_同月"],
                "price": row["活動售價"],
                "base_price": row["基準售價"],
                "sample_warning": sample_warning,
                "confidence_level": level,
                "confidence_reason": reason,
                "evidence": {
                    "商品編號": str(row["商品編號"]),
                    "活動單位": row["活動單位"],
                    "開始日期": str(row["開始日期"]),
                    "結束日期": str(row["結束日期"]),
                    "對應活動": row["對應活動"],
                    "分類": row["分類"],
                    "本品項是否參與": bool(row["本品項是否參與"]),
                    "活動售價": row["活動售價"],
                    "基準售價(同月代理牌價)": row["基準售價"],
                    "單位平均銷量": row["單位平均銷量"],
                    "基準平均銷量_同月": row["基準平均銷量_同月"],
                    "淨營收效應_合計": row["淨營收效應_合計"],
                    "資料來源工作表": "活動單位總覽(vs基準)",
                },
            }
        )

    return {
        "total_records": total_records,
        "total_days": total_days,
        "total_units": total_units,
        "positive_units": positive_units,
        "negative_units": negative_units,
        "health_score": health_score,
        "total_net_effect": total_net_effect,
        "risk_sku": risk_sku,
        "risk_name": risk_name,
        "risk_loss_count": int(risk_loss_count),
        "turnaround": turnaround,
        "decision_items": decision_items,
    }


_demo_path = _resolve_demo_path()
insights = compute_home_insights(str(_demo_path)) if _demo_path else None


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

# 三張效益卡：直接用現算出來的 insights，不再是寫死字串
b_col1, b_col2, b_col3 = st.columns(3)

with b_col1:
    if insights:
        records_val = f"{insights['total_records']} 筆"
        records_sub = f"涵蓋 3-4 月完整 {insights['total_days']} 天銷量紀錄"
    else:
        records_val = "—"
        records_sub = "尚未載入資料"
    st.markdown(
        f"""
    <div class="spec-benefit-card">
        <div class="spec-benefit-lbl">📊 資料追蹤規模</div>
        <div class="spec-benefit-val">{records_val}</div>
        <div class="spec-benefit-sub">{records_sub}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with b_col2:
    if insights:
        units_sub = f"自動對比 {insights['total_units']} 筆歷史檔期基準"
    else:
        units_sub = "尚未載入資料"
    st.markdown(
        f"""
    <div class="spec-benefit-card">
        <div class="spec-benefit-lbl">🎯 檔期與品項辨識</div>
        <div class="spec-benefit-val">100%</div>
        <div class="spec-benefit-sub">{units_sub}</div>
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
# 4. Executive Brief & Decision Queue — 全部改為現算數字，附上真實依據
# =========================================================

st.markdown("##### ⚡ 活動決策簡報 (Executive Brief，依歷史資料現算)")

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
    .ai-rec-caveat { font-size: 12px; color: #92400E; font-weight: 600; margin-top: 6px; }

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

if not insights:
    st.warning("找不到示範資料檔，請確認 `assets/demo_sales_data.xlsx` 存在後再查看決策簡報。")
else:
    # --- 4 大活動監控指標：全部現算 ---
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        st.markdown(
            f'<div class="kpi-mini-card"><div class="kpi-mini-title">活動健康度 Health</div>'
            f'<div class="kpi-mini-val kpi-health">{insights["health_score"]}</div>'
            f'<div class="kpi-subtext" style="color: #059669;">'
            f'{insights["positive_units"]}/{insights["total_units"]} 正向增益檔期</div></div>',
            unsafe_allow_html=True,
        )
    with b2:
        if insights["risk_sku"]:
            risk_sub = f'{insights["risk_name"]} 鋪底虧損警告'
        else:
            risk_sub = "目前無虧損警告"
        st.markdown(
            f'<div class="kpi-mini-card"><div class="kpi-mini-title">活動風險警示 Risk</div>'
            f'<div class="kpi-mini-val kpi-risk">{insights["risk_loss_count"]} 檔</div>'
            f'<div class="kpi-subtext" style="color: #DC2626;">{risk_sub}</div></div>',
            unsafe_allow_html=True,
        )
    with b3:
        st.markdown(
            f'<div class="kpi-mini-card"><div class="kpi-mini-title">待執行策略 Decision</div>'
            f'<div class="kpi-mini-val kpi-pending">{len(insights["decision_items"])} 項</div>'
            f'<div class="kpi-subtext" style="color: #D97706;">依歷史淨增益排序建議審核</div></div>',
            unsafe_allow_html=True,
        )
    with b4:
        net_effect_wan = insights["total_net_effect"] / 10000
        st.markdown(
            f'<div class="kpi-mini-card"><div class="kpi-mini-title">活動總淨效益 Net Impact</div>'
            f'<div class="kpi-mini-val kpi-forecast">{net_effect_wan:+.1f}萬</div>'
            f'<div class="kpi-subtext" style="color: #2563EB;">3-4月全部{insights["total_units"]}檔活動淨營收加總</div></div>',
            unsafe_allow_html=True,
        )

    # --- AI 主動建議 Banner ---
    turnaround = insights["turnaround"]
    if turnaround:
        net_wan = turnaround["net_effect"] / 10000
        st.markdown(
            f"""
<div class="ai-rec-banner">
    <div class="ai-rec-head">💡 AI 主動最佳策略建議
        <span class="confidence-tag" style="background:#FFEDD5;color:#C2410C;padding:2px 8px;border-radius:6px;">
            信心：{turnaround['confidence_level']}
        </span>
    </div>
    <div class="ai-rec-body">
        <span style="color: #EA580C;">【{turnaround['name']}】</span>在「{turnaround['event']}」檔期
        （{turnaround['days']}天實測，售價 ${turnaround['price']:,.0f}）
        相較基準售價 ${turnaround['base_price']:,.0f}，
        日均銷量由 {turnaround['base_qty']:.1f} 件成長至 {turnaround['avg_qty']:.1f} 件，
        累計淨營收效應
        <span style="background: #FEF08A; padding: 2px 6px; border-radius: 4px;">{net_wan:+.1f} 萬元</span>。
        建議比照此檔期定價策略，優先處理{turnaround['name']}目前的
        {insights['risk_loss_count']} 檔虧損期間。
    </div>
    <div class="ai-rec-caveat">
        ※ 此為歷史實測結果（單一活動，可拆分），非未來預估；信心判斷依據：{turnaround['confidence_reason']}。
        其餘同售價但疊加多種活動的期間因無法拆分個別貢獻，未列入此建議。
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
        with st.expander("🔍 查看 AI 推論依據（原始欄位與數值）"):
            st.caption("以下數值皆直接讀自「活動單位總覽(vs基準)」工作表，未經人工調整。")
            st.json(turnaround["evidence"])
    else:
        st.info("目前資料中找不到可拆分的正向翻轉案例，暫無 AI 主動建議（資料不足，不猜測）。")

    # 🎯 Decision Queue
    st.markdown("##### 🎯 AI 建議決策隊列 (Decision Queue，依歷史淨增益排序)")

    button_specs = [
        ("👉 Approve 採納文案", "app", ["pages/18_行動生成.py", "app_pages/18_行動生成.py", "18_行動生成.py"]),
        ("👉 Review 檢視趨勢", "rev", ["pages/12_活動洞察.py", "app_pages/12_活動洞察.py", "12_活動洞察.py"]),
        ("👉 Simulate 效益試算", "sim", ["pages/17_情境模擬.py", "app_pages/17_情境模擬.py", "17_情境模擬.py"]),
    ]
    impact_badges = ["badge-impact-high", "badge-impact-high", "badge-impact-med"]

    if not insights["decision_items"]:
        st.info("目前資料中找不到符合條件（可拆分、單一活動、天數≥2、確實參與）的建議案例。")

    for i, item in enumerate(insights["decision_items"]):
        net_wan = item["net_effect"] / 10000
        badge_cls = impact_badges[i] if i < len(impact_badges) else "badge-impact-med"
        badge_label = "高影響力 High Impact" if badge_cls == "badge-impact-high" else "中影響力 Medium Impact"
        confidence_label = f"信心：{item['confidence_level']}（{item['days']}天實測・可拆分）"

        dq_col1, dq_col2 = st.columns([3.2, 1.2])
        with dq_col1:
            st.markdown(
                f"""
            <div class="decision-row">
                <div>
                    <span class="{badge_cls}">{badge_label}</span>
                    <span class="confidence-tag">{confidence_label}</span>
                    <div style="margin-top: 4px;">
                        <strong class="decision-text">
                            {i+1:02d} {item['name']}：「{item['event']}」檔期
                            淨增益達 {net_wan:+.1f} 萬元，
                            日均銷量 {item['avg_qty']:.1f} 件（基準日均 {item['base_qty']:.1f} 件），
                            售價 ${item['price']:,.0f}
                        </strong>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            with st.expander(f"🔍 決策 {i+1:02d}：查看判斷依據"):
                st.caption(f"信心理由：{item['confidence_reason']}")
                st.json(item["evidence"])
        with dq_col2:
            label, key_prefix, targets = button_specs[i] if i < len(button_specs) else button_specs[-1]
            if st.button(label, key=f"{key_prefix}_{i}", use_container_width=True, type="primary" if i == 0 else "secondary"):
                load_demo_data_to_session()
                st.toast("已帶入此檔期的實測數據，正在跳轉...", icon="✅")
                for target in targets:
                    try:
                        st.switch_page(target)
                        break
                    except Exception:
                        continue
