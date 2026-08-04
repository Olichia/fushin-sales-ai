from pathlib import Path
import sys

import pandas as pd
import streamlit as st


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.session_helpers import initialize_session_state


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()


# =========================================================
# 小工具函式
# =========================================================

def dataframe_exists(value: object) -> bool:
    return isinstance(value, pd.DataFrame) and not value.empty


def dataframe_row_count(value: object) -> int:
    if isinstance(value, pd.DataFrame):
        return len(value)
    return 0


# =========================================================
# 🌟 原色頂部 Hero Banner + 大字體與多彩卡片 CSS 注入
# =========================================================

st.markdown(
    """
    <style>
    /* 1. 全局背景與字體基礎 */
    .stApp {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-size: 1.15rem !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, .stMarkdown {
        color: #0F172A !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stSubheader {
        font-size: 1.6rem !important;
        font-weight: 800 !important;
        color: #0F172A !important;
        margin-top: 24px !important;
        margin-bottom: 14px !important;
    }

    /* 2. 主視覺 Hero Banner：保留原本柔和漸層顏色 */
    .hero-banner-vibrant {
        background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 50%, #F3E8FF 100%);
        border: 2px solid #C7D2FE;
        border-radius: 20px;
        padding: 32px 36px;
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.06);
        margin-bottom: 24px;
    }
    .hero-badge-vibrant {
        background: linear-gradient(90deg, #38BDF8, #2563EB);
        color: #FFFFFF !important;
        font-size: 0.95rem !important;
        font-weight: 900;
        padding: 6px 16px;
        border-radius: 20px;
        letter-spacing: 1px;
        display: inline-block;
        margin-bottom: 12px;
    }
    .hero-title-main {
        font-size: 2.5rem !important;
        font-weight: 900 !important;
        color: #1E1B4B !important;
        margin: 0 0 10px 0 !important;
        line-height: 1.25;
    }
    .hero-sub-highlight {
        font-size: 1.25rem !important;
        font-weight: 800 !important;
        color: #2563EB !important;
        margin-bottom: 12px !important;
    }
    .hero-desc-main {
        color: #475569 !important;
        font-size: 1.15rem !important;
        line-height: 1.6;
        margin: 0;
    }

    /* 3. 三大功能亮點卡片 (多彩高吸睛) */
    .feature-card-1 {
        background: #EFF6FF; border: 1.5px solid #BFDBFE; border-radius: 16px;
        padding: 20px 18px; text-align: center; height: 100%; margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.05);
    }
    .feature-card-2 {
        background: #ECFDF5; border: 1.5px solid #A7F3D0; border-radius: 16px;
        padding: 20px 18px; text-align: center; height: 100%; margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.05);
    }
    .feature-card-3 {
        background: #FFF7ED; border: 1.5px solid #FFEDD5; border-radius: 16px;
        padding: 20px 18px; text-align: center; height: 100%; margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.05);
    }
    .feature-icon { font-size: 2.2rem; margin-bottom: 8px; }
    .feature-title { font-size: 1.25rem !important; font-weight: 800; color: #0F172A !important; margin-bottom: 6px; }
    .feature-desc { font-size: 1.05rem !important; color: #475569 !important; line-height: 1.4; }

    /* 4. AI 導覽指引框 */
    .ai-guide-box {
        background: linear-gradient(135deg, #FEF3C7 0%, #FFFBEB 100%);
        border: 2px solid #F59E0B;
        border-left: 8px solid #D97706;
        border-radius: 16px;
        padding: 24px 28px;
        margin: 22px 0;
        box-shadow: 0 6px 16px rgba(217, 119, 6, 0.08);
    }
    .ai-guide-tag { color: #B45309 !important; font-weight: 900; font-size: 1.05rem !important; margin-bottom: 6px; }
    .ai-guide-h2 { color: #78350F !important; font-size: 1.45rem !important; font-weight: 900; margin-bottom: 8px; }
    .ai-guide-txt { color: #92400E !important; font-size: 1.15rem !important; line-height: 1.5; }
    .ai-guide-btn { color: #D97706 !important; font-weight: 900; font-size: 1.25rem !important; margin-top: 10px; display: inline-block; }

    /* 5. 輕量卡片指標 */
    .custom-metric-card {
        background: #FFFFFF;
        border: 1.5px solid #E2E8F0;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        height: 100%;
        margin-bottom: 12px;
    }
    .custom-metric-label { font-size: 1rem !important; font-weight: 800; color: #64748B !important; margin-bottom: 6px; }
    .custom-metric-value { font-size: 1.85rem !important; font-weight: 900; color: #0284C7 !important; line-height: 1.2; }
    .custom-metric-delta { font-size: 0.95rem !important; font-weight: 800; color: #16A34A !important; margin-top: 6px; }

    /* 6. 三大操作步驟卡片 */
    .phase-card-1 {
        background: linear-gradient(145deg, #ECFDF5 0%, #D1FAE5 100%);
        border: 2px solid #34D399;
        border-radius: 16px; padding: 20px; min-height: 220px;
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.08);
        display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 12px;
    }
    .phase-card-2 {
        background: linear-gradient(145deg, #F0F9FF 0%, #E0F2FE 100%);
        border: 2px solid #38BDF8;
        border-radius: 16px; padding: 20px; min-height: 220px;
        box-shadow: 0 6px 16px rgba(14, 165, 233, 0.08);
        display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 12px;
    }
    .phase-card-3 {
        background: linear-gradient(145deg, #FFF7ED 0%, #FFEDD5 100%);
        border: 2px solid #FB923C;
        border-radius: 16px; padding: 20px; min-height: 220px;
        box-shadow: 0 6px 16px rgba(249, 115, 22, 0.08);
        display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 12px;
    }
    
    .phase-header { display: flex; align-items: center; gap: 12px; }
    .phase-badge-1 { font-size: 0.95rem !important; font-weight: 900; color: #059669 !important; }
    .phase-badge-2 { font-size: 0.95rem !important; font-weight: 900; color: #0284C7 !important; }
    .phase-badge-3 { font-size: 0.95rem !important; font-weight: 900; color: #EA580C !important; }
    
    .phase-title { font-size: 1.3rem !important; font-weight: 900; color: #0F172A !important; }
    .phase-desc { font-size: 1.05rem !important; color: #334155 !important; line-height: 1.5; margin-top: 10px; }
    .phase-footer { font-size: 0.95rem !important; color: #64748B !important; font-weight: 700; margin-top: 10px; }

    .status-pill-done {
        background: #10B981; color: #FFFFFF !important;
        padding: 4px 14px; border-radius: 12px; font-size: 0.95rem !important; font-weight: 800; display: inline-block;
    }
    .status-pill-todo {
        background: #F59E0B; color: #FFFFFF !important;
        padding: 4px 14px; border-radius: 12px; font-size: 0.95rem !important; font-weight: 800; display: inline-block;
    }

    /* RWD 手機彈性調整 */
    @media (max-width: 768px) {
        .hero-title-main { font-size: 1.8rem !important; }
        .hero-banner-vibrant { padding: 22px 20px; }
        .phase-card-1, .phase-card-2, .phase-card-3 { min-height: auto; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 讀取 Session State
# =========================================================

uploaded_file_name = st.session_state.get("uploaded_file_name")
uploaded_dataframe = st.session_state.get("uploaded_dataframe")
column_mapping = st.session_state.get("column_mapping", {})
standardized_dataframe = st.session_state.get("standardized_dataframe")
sales_data_confirmed = bool(st.session_state.get("sales_data_confirmed", False))

activity_uploaded_files = st.session_state.get("activity_uploaded_files", {})
activity_standardized_dataframe = st.session_state.get("activity_standardized_dataframe")
activity_calendar_dataframe = st.session_state.get("activity_calendar_dataframe")
promotion_benefits_dataframe = st.session_state.get("promotion_benefits_dataframe")
activity_issues_dataframe = st.session_state.get("activity_issues_dataframe")
activity_data_confirmed = bool(st.session_state.get("activity_data_confirmed", False))

integrated_dataframe = st.session_state.get("integrated_sales_activity_dataframe")
integration_issues_dataframe = st.session_state.get("integration_issues_dataframe")
performance_dataframe = st.session_state.get("activity_performance_dataframe")
strategy_dataframe = st.session_state.get("strategy_report_dataframe")
strategy_report_text = str(st.session_state.get("strategy_report_text", ""))
full_analysis_completed = bool(st.session_state.get("full_analysis_completed", False))


# =========================================================
# 判斷流程狀態
# =========================================================

sales_ready = sales_data_confirmed and dataframe_exists(standardized_dataframe)
activity_ready = activity_data_confirmed and dataframe_exists(activity_standardized_dataframe)
analysis_outputs_ready = (
    dataframe_exists(integrated_dataframe)
    and dataframe_exists(performance_dataframe)
    and (dataframe_exists(strategy_dataframe) or bool(strategy_report_text.strip()))
)
analysis_ready = full_analysis_completed and analysis_outputs_ready


workflow_steps = [
    {
        "編號": "01",
        "名稱": "銷量資料處理",
        "完成": sales_ready,
        "圖示": "📊",
        "說明": "上傳銷量 Excel、選擇工作表、確認必要欄位，完成資料標準化與品質檢查。",
        "頁面": "01 銷量資料處理",
        "card_class": "phase-card-1",
        "badge_class": "phase-badge-1",
    },
    {
        "編號": "02",
        "名稱": "活動資料處理",
        "完成": activity_ready,
        "圖示": "🏷️",
        "說明": "上傳月份活動 Excel，確認月份對應，建立活動價格、活動日曆、優惠與問題清單。",
        "頁面": "02 活動資料處理",
        "card_class": "phase-card-2",
        "badge_class": "phase-badge-2",
    },
    {
        "編號": "03",
        "名稱": "執行完整分析",
        "完成": analysis_ready,
        "圖示": "⚡",
        "說明": "一次完成資料整合、活動成效分析與策略報告產生。",
        "頁面": "03 執行完整分析",
        "card_class": "phase-card-3",
        "badge_class": "phase-badge-3",
    },
]

completed_step_count = sum(int(step["完成"]) for step in workflow_steps)
total_step_count = len(workflow_steps)
completion_rate = completed_step_count / total_step_count


# =========================================================
# 1. 主視覺 Hero Banner (原本色彩 + 截圖指定文字)
# =========================================================

st.markdown(
    """
    <div class="hero-banner-vibrant">
        <div class="hero-badge-vibrant">✨ AI-POWERED RETAIL ENGINE</div>
        <h1 class="hero-title-main">富信驅動 AI ｜ 精準行銷創造新零售</h1>
        <div class="hero-sub-highlight">從「經驗直覺」轉向「AI 數據驅動」的精準品牌行銷</div>
        <p class="hero-desc-main">
            歡迎使用 AI 電商活動策略決策助手。依序完成銷量與活動數據注入，系統將自動構建高維度成效歸因模型，釋放主管報表與 AI 策略顧問之商業價值。
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 2. 核心亮點卡片
# =========================================================

feat_col1, feat_col2, feat_col3 = st.columns(3)

with feat_col1:
    st.markdown(
        """
        <div class="feature-card-1">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">全自動資料對接</div>
            <div class="feature-desc">自動整合並清洗銷量與月份活動檔期</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with feat_col2:
    st.markdown(
        """
        <div class="feature-card-2">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">活動成效分析</div>
            <div class="feature-desc">清楚計算促銷拉動效益與優惠成效</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with feat_col3:
    st.markdown(
        """
        <div class="feature-card-3">
            <div class="feature-icon">🤖</div>
            <div class="feature-title">AI 策略建議</div>
            <div class="feature-desc">自動為您生成活動建議與主管決策報表</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 3. AI 策略顧問動態指引
# =========================================================

next_incomplete_step = next(
    (step for step in workflow_steps if not step["完成"]),
    None,
)

if next_incomplete_step is None:
    st.balloons()
    st.success(
        "🎉 **三大步驟已全數完成！** "
        "您現在可以點選左側選單進入「分析總覽」、「活動洞察」、「策略中心」，或直接諮詢「AI 策略顧問」。"
    )
else:
    st.markdown(
        f"""
        <div class="ai-guide-box">
            <div class="ai-guide-tag">💡 建議下一步</div>
            <div class="ai-guide-h2">STEP {next_incomplete_step['編號']} ｜ {next_incomplete_step['名稱']}</div>
            <div class="ai-guide-txt">{next_incomplete_step['說明']}</div>
            <div class="ai-guide-btn">👉 請從左側導覽進入「{next_incomplete_step['頁面']}」</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 4. 目前進度
# =========================================================

st.subheader("目前進度")

progress_col1, progress_col2, progress_col3 = st.columns([1, 1, 2])

with progress_col1:
    st.markdown(
        f"""
        <div class="custom-metric-card">
            <div class="custom-metric-label">已完成步驟</div>
            <div class="custom-metric-value">{completed_step_count} / {total_step_count}</div>
            <div class="custom-metric-delta">● {'進行中' if completed_step_count < total_step_count else '全數就緒'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with progress_col2:
    st.markdown(
        f"""
        <div class="custom-metric-card">
            <div class="custom-metric-label">完成度</div>
            <div class="custom-metric-value">{completion_rate:.0%}</div>
            <div class="custom-metric-delta" style="color:#0284C7 !important;">● 即時更新</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with progress_col3:
    st.markdown(
        f"""
        <div class="custom-metric-card">
            <div class="custom-metric-label" style="color:#6366F1 !important; font-weight:900;">完整分析流程</div>
            <div style="font-size: 1.05rem; font-weight:700; color:#334155; margin-top:6px;">
                已完成 {completed_step_count} 個步驟，尚有 {total_step_count - completed_step_count} 個步驟
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(completion_rate)


# =========================================================
# 5. 操作流程
# =========================================================

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("操作流程")

step_columns = st.columns(3)

for column, step in zip(step_columns, workflow_steps):
    status_html = (
        '<div class="status-pill-done">✓ 已完成</div>'
        if step["完成"]
        else '<div class="status-pill-todo">⏳ 待處理</div>'
    )
    with column:
        st.markdown(
            f"""
            <div class="{step['card_class']}">
                <div>
                    <div class="phase-header">
                        <span style="font-size: 1.8rem;">{step['圖示']}</span>
                        <div>
                            <div class="{step['badge_class']}">STEP {step['編號']}</div>
                            <div class="phase-title">{step['名稱']}</div>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">{status_html}</div>
                    <div class="phase-desc">{step['說明']}</div>
                </div>
                <div class="phase-footer">導覽位置：{step['頁面']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# 6. 資料準備與完整分析輸出區塊
# =========================================================

st.divider()
st.subheader("資料準備與完整分析輸出")

out_col1, out_col2, out_col3 = st.columns(3)

with out_col1:
    st_text = "已建立" if dataframe_exists(integrated_dataframe) else "尚未建立"
    st_class = "status-pill-done" if dataframe_exists(integrated_dataframe) else "status-pill-todo"
    st.markdown(
        f"""
        <div class="custom-metric-card">
            <div style="font-weight:800; font-size:1.15rem; margin-bottom:6px; color:#0F172A;">1. 資料整合</div>
            <div class="custom-metric-label">整合資料筆數</div>
            <div class="custom-metric-value" style="font-size:1.6rem; margin-bottom:8px;">{dataframe_row_count(integrated_dataframe):,}</div>
            <div class="{st_class}">{st_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with out_col2:
    st_text = "已完成" if dataframe_exists(performance_dataframe) else "尚未完成"
    st_class = "status-pill-done" if dataframe_exists(performance_dataframe) else "status-pill-todo"
    st.markdown(
        f"""
        <div class="custom-metric-card">
            <div style="font-weight:800; font-size:1.15rem; margin-bottom:6px; color:#0F172A;">2. 活動成效</div>
            <div class="custom-metric-label">成效分析筆數</div>
            <div class="custom-metric-value" style="font-size:1.6rem; margin-bottom:8px;">{dataframe_row_count(performance_dataframe):,}</div>
            <div class="{st_class}">{st_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with out_col3:
    # 修正邏輯：必須是 DataFrame 真實有資料，或是全流程已分析完成且報告非空
    has_strat = dataframe_exists(strategy_dataframe) or (full_analysis_completed and bool(strategy_report_text.strip()))
    st_text = "已產生" if has_strat else "尚未產生"
    st_class = "status-pill-done" if has_strat else "status-pill-todo"
    st.markdown(
        f"""
        <div class="custom-metric-card">
            <div style="font-weight:800; font-size:1.15rem; margin-bottom:6px; color:#0F172A;">3. 策略建議</div>
            <div class="custom-metric-label">策略資料筆數</div>
            <div class="custom-metric-value" style="font-size:1.6rem; margin-bottom:8px;">{dataframe_row_count(strategy_dataframe):,}</div>
            <div class="{st_class}">{st_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()
st.info("💡 系統提示：完成資料上傳與分析後，即可點選左側選單「策略中心」查看 AI 建議與分析總覽。")
