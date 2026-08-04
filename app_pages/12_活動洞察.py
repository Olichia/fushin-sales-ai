from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.column_labels import default_column_config
from src.session_helpers import initialize_session_state
from src.unit_overview_helpers import (
    CATEGORY_COLOR_MAP,
    compute_risk_mask,
    prepare_unit_overview_for_display,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

MINIMUM_DAYS_FOR_CONFIDENCE = 2

CHART_MAX_HEIGHT = 460
CHART_ROW_HEIGHT = 22
CHART_MIN_HEIGHT = 280

# 雙軌配對拆解圖在疊加多個活動時會多顯示一個 st.selectbox，
# 這段高度差會讓左右兩欄圖表底部對不齊，縮小圖表容器高度
# 抵銷差距（估計值，抓 Streamlit selectbox 標準高度+上下間距）。
EXTRA_WIDGET_HEIGHT_OFFSET = 56


def resolve_bar_chart_sizing(
    row_count: int,
    normal_bar_width: float,
) -> tuple[int, float | None]:
    """
    回傳 (圖表高度, 柱條寬度)。

    資料筆數達到或超過 CHART_MAX_HEIGHT 時：圖表高度用自然
    高度（隨筆數增加，超出上限的部分交給外層
    st.container(height=CHART_MAX_HEIGHT) 捲動），柱寬固定為
    normal_bar_width 的一半。

    資料筆數不足時：圖表高度固定撐滿 CHART_MAX_HEIGHT，柱寬
    不寫死（回傳 None，呼叫端不呼叫 update_traces(width=...)，
    讓 Plotly 依可用高度自動計算）。
    """

    natural_height = max(
        CHART_MIN_HEIGHT, CHART_ROW_HEIGHT * row_count
    )

    if natural_height >= CHART_MAX_HEIGHT:
        return natural_height, normal_bar_width / 2

    return CHART_MAX_HEIGHT, None

header_col, badge_col = st.columns([3, 1])

with header_col:
    st.markdown(
        """
        <div class="step-label">銷售成效分析</div>

        <div class="product-page-title">
            <div class="product-page-title-bar"></div>
            <h1>活動洞察 Campaign Insights</h1>
        </div>

        <p class="product-page-description">
            以「活動單位」為顆粒度，比較各活動單位相對於同月安靜期
            基準的淨營收效應，並用瀑布法配對比較拆解疊加活動中
            各活動的個別貢獻。數字為觀察性分析，非隨機實驗結果。
        </p>
        """,
        unsafe_allow_html=True,
    )

with badge_col:
    st.markdown(
        """
        <div style="text-align:right; padding-top:1.2rem;
                    color:#6b7280; font-size:0.85rem;">
            ● 富信新零售決策支援系統
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 取得既有資料（新方法論：活動單位分析）
# =========================================================

unit_overview_raw = st.session_state.get(
    "activity_unit_overview_dataframe"
)

pairing_raw = st.session_state.get(
    "activity_waterfall_pairing_dataframe"
)

summary_raw = st.session_state.get(
    "activity_waterfall_summary_dataframe"
)


def _ready(dataframe: object) -> bool:
    return isinstance(dataframe, pd.DataFrame) and not dataframe.empty


if not (
    _ready(unit_overview_raw)
    and _ready(pairing_raw)
    and _ready(summary_raw)
):
    st.warning(
        "尚未產生活動單位分析結果。"
        "請先於「03 執行完整分析」頁面完成分析"
        "（需先完成銷量與活動資料確認）。"
    )
    st.stop()


unit_overview = unit_overview_raw.copy()
pairing_table = pairing_raw.copy()
summary_table = summary_raw.copy()

# 商品洞察需要贈品細節，額外讀取工作表4（商品售價表）。
# 這份資料是輔助性質，讀不到也不阻斷整頁。
unit_price_raw = st.session_state.get(
    "activity_unit_price_dataframe"
)

if isinstance(unit_price_raw, pd.DataFrame) and not unit_price_raw.empty:
    unit_price_table = unit_price_raw.copy()
    unit_price_table["product_id"] = (
        unit_price_table["product_id"].astype(str).str.strip()
    )
else:
    unit_price_table = pd.DataFrame(
        columns=[
            "unit_code",
            "product_id",
            "gift",
            "bonus_gift_text",
            "bonus_campaign_text",
        ]
    )

_gift_lookup = {}

for row in unit_price_table.itertuples():
    gift_parts = [
        str(part)
        for part in [
            getattr(row, "gift", None),
            getattr(row, "bonus_gift_text", None),
            getattr(row, "bonus_campaign_text", None),
        ]
        if part and pd.notna(part) and str(part).strip()
    ]

    if gift_parts:
        _gift_lookup[(row.product_id, row.unit_code)] = "、".join(
            dict.fromkeys(gift_parts)
        )


def lookup_gift_text(product_id: str, unit_code: str) -> str:
    return _gift_lookup.get((str(product_id), str(unit_code)), "")


def render_discount_rate_insight(
    dataframe: pd.DataFrame, show_product_name: bool = True
) -> None:
    """
    規則式描述傳入範圍內折扣率與淨增益的關係：
    哪個折扣率區間平均表現最好、有沒有「折扣不深但淨增益
    仍名列前茅」的案例。範圍可以是整體篩選結果，也可以是
    單一商品的子集合（有篩選商品時逐品項各自呼叫一次，這時
    show_product_name=False，因為品項名稱已經是該區塊標題，
    不需要在句子裡重複一次）。
    """

    discount_insight_data = dataframe.dropna(
        subset=["discount_rate", "net_revenue_effect_per_day"]
    )

    if discount_insight_data.empty:
        st.caption("目前範圍內沒有可分析折扣率的資料。")
        return

    discount_bins = [-1, 0, 0.05, 0.10, 0.15, 0.20, 1]
    discount_bin_labels = [
        "無折扣/漲價",
        "0-5%",
        "5-10%",
        "10-15%",
        "15-20%",
        "20%以上",
    ]

    binned = discount_insight_data.copy()
    binned["discount_bracket"] = pd.cut(
        binned["discount_rate"],
        bins=discount_bins,
        labels=discount_bin_labels,
    )

    bracket_stats = binned.groupby(
        "discount_bracket", observed=True
    ).agg(
        avg_net_effect=("net_revenue_effect_per_day", "mean"),
        unit_count=("unit_code", "count"),
    )
    bracket_stats = bracket_stats[bracket_stats["unit_count"] > 0]

    if not bracket_stats.empty:
        best_bracket = bracket_stats["avg_net_effect"].idxmax()
        best_bracket_row = bracket_stats.loc[best_bracket]

        st.markdown(
            f"折扣率落在「{best_bracket}」區間的活動單位"
            "平均淨營收效應最高，約 "
            f"\\${best_bracket_row['avg_net_effect']:,.0f}/日"
            f"（共{int(best_bracket_row['unit_count'])}檔）。"
        )

    positive_data = discount_insight_data[
        discount_insight_data["net_revenue_effect_per_day"] > 0
    ]

    if len(positive_data) >= 3:
        gain_threshold = positive_data[
            "net_revenue_effect_per_day"
        ].quantile(0.75)
        discount_median = positive_data["discount_rate"].median()

        shallow_high_performers = positive_data[
            (
                positive_data["net_revenue_effect_per_day"]
                >= gain_threshold
            )
            & (positive_data["discount_rate"] < discount_median)
        ].sort_values(
            "net_revenue_effect_per_day", ascending=False
        )

        if not shallow_high_performers.empty:
            example = shallow_high_performers.iloc[0]
            example_discount_text = (
                f"{example['discount_rate']:.0%}"
                if pd.notna(example["discount_rate"])
                else "折扣率不明"
            )

            product_name_prefix = (
                f"**{example['product_name']}** "
                if show_product_name
                else ""
            )

            st.markdown(
                f"值得留意：{product_name_prefix}活動單位 "
                f"**{example['unit_code']}** "
                f"折扣率僅 {example_discount_text}"
                "（低於範圍內中位數），"
                "淨增益仍達 "
                f"\\${example['net_revenue_effect_per_day']:,.0f}/日，"
                "排在前段班；這類案例代表不一定要打到很深的折扣"
                "才能維持不錯的營收表現，深折扣可能只是白白讓出"
                "存量降價的營收，可考慮嘗試較淺的折扣區間。"
            )


# =========================================================
# 欄位型別整理與衍生欄位
# =========================================================

unit_overview = prepare_unit_overview_for_display(unit_overview)

unit_overview["hint"] = unit_overview.apply(
    lambda row: "、".join(
        part
        for part in [
            str(row.get("sample_size_note") or ""),
            str(row.get("proxy_price_note") or ""),
        ]
        if part
    ),
    axis=1,
)

for column in [
    "target_unit_days",
    "target_unit_avg_sales",
    "target_unit_avg_price",
    "candidate_weighted_avg_daily_revenue",
    "actual_daily_revenue",
    "net_gain_per_day",
    "net_gain_total",
    "month",
]:
    if column in pairing_table.columns:
        pairing_table[column] = pd.to_numeric(
            pairing_table[column], errors="coerce"
        )

pairing_table["product_id"] = (
    pairing_table["product_id"].astype(str).str.strip()
)

for column in ["interval_count", "total_days", "total_gain"]:
    if column in summary_table.columns:
        summary_table[column] = pd.to_numeric(
            summary_table[column], errors="coerce"
        )

summary_table["product_id"] = (
    summary_table["product_id"].astype(str).str.strip()
)


# =========================================================
# 篩選工具列
# =========================================================

st.markdown("##### 🔽 篩選")

with st.container(border=True):
    filter_row1_col1, filter_row1_col2, filter_row1_col3 = st.columns(
        [1, 1, 1.4]
    )

    month_options = sorted(
        unit_overview["month"].dropna().unique().tolist()
    )

    with filter_row1_col1:
        selected_months = st.multiselect(
            "月份",
            options=month_options,
            default=month_options,
            format_func=lambda value: f"{int(value)}月",
        )

    category_options = sorted(
        unit_overview["product_category"]
        .dropna()
        .astype(str)
        .replace("", pd.NA)
        .dropna()
        .unique()
        .tolist()
    )

    with filter_row1_col2:
        selected_categories = st.multiselect(
            "品類",
            options=category_options,
            default=[],
            placeholder="未選擇時顯示全部品類",
        )

    activity_type_options = sorted(
        {
            token
            for label in unit_overview[
                "corresponding_activities_label"
            ]
            for token in label.split("、")
            if token
        }
    )

    with filter_row1_col3:
        selected_activity_types = st.multiselect(
            "活動類型",
            options=activity_type_options,
            default=[],
            placeholder="未選擇時顯示全部活動類型",
        )

    split_filter = st.radio(
        "拆分狀態",
        options=["全部", "僅看可拆分", "僅看不可拆分"],
        horizontal=True,
        key="campaign_insight_split_filter",
    )

    sku_options = (
        unit_overview[["product_id", "product_name"]]
        .drop_duplicates()
        .sort_values("product_id")
    )

    sku_label_map = {
        str(row.product_name): str(row.product_id)
        for row in sku_options.itertuples()
    }

    selected_sku_labels = st.multiselect(
        "商品（SKU）",
        options=list(sku_label_map.keys()),
        default=[],
        placeholder="未選擇時顯示全部商品",
        key="campaign_insight_sku_filter",
    )

    st.caption(
        f"⚠ 已標示樣本天數 < {MINIMUM_DAYS_FOR_CONFIDENCE} "
        "天的區間（見各表格「提示」欄位）"
    )


# =========================================================
# 套用篩選
# =========================================================

filtered_unit_overview = unit_overview.copy()
filtered_pairing = pairing_table.copy()
filtered_summary = summary_table.copy()

if selected_months:
    filtered_unit_overview = filtered_unit_overview[
        filtered_unit_overview["month"].isin(selected_months)
    ]
    filtered_pairing = filtered_pairing[
        filtered_pairing["month"].isin(selected_months)
    ]

if selected_categories:
    filtered_unit_overview = filtered_unit_overview[
        filtered_unit_overview["product_category"].isin(
            selected_categories
        )
    ]

if selected_activity_types:
    filtered_unit_overview = filtered_unit_overview[
        filtered_unit_overview[
            "corresponding_activities_label"
        ].apply(
            lambda label: any(
                token in label for token in selected_activity_types
            )
        )
    ]
    filtered_pairing = filtered_pairing[
        filtered_pairing["activity_type"].isin(
            selected_activity_types
        )
    ]
    # 無法拆分列的 corresponding_activities 現在是組合字串
    # （而非單一活動類型token），用「組合字串內是否包含被選
    # token」判斷，跟 filtered_unit_overview 的篩選邏輯一致，
    # 而不是對 activity_type 做精準比對（.isin()）。
    filtered_summary = filtered_summary[
        filtered_summary["corresponding_activities"].apply(
            lambda label: any(
                token in label for token in selected_activity_types
            )
        )
    ]

if split_filter == "僅看可拆分":
    filtered_unit_overview = filtered_unit_overview[
        filtered_unit_overview["classification"] == "可分離,單一活動"
    ]
    filtered_pairing = filtered_pairing[
        filtered_pairing["split_status"] == "可拆分"
    ]
    filtered_summary = filtered_summary[
        filtered_summary["split_status"] == "可拆分"
    ]
elif split_filter == "僅看不可拆分":
    filtered_unit_overview = filtered_unit_overview[
        filtered_unit_overview["classification"]
        == "多活動合併,不可分離"
    ]
    filtered_pairing = filtered_pairing[
        filtered_pairing["split_status"] != "可拆分"
    ]
    filtered_summary = filtered_summary[
        filtered_summary["split_status"] == "無法拆分"
    ]

selected_sku_ids = [
    sku_label_map[label] for label in selected_sku_labels
]

if selected_sku_labels:
    filtered_unit_overview = filtered_unit_overview[
        filtered_unit_overview["product_id"].isin(selected_sku_ids)
    ]
    filtered_pairing = filtered_pairing[
        filtered_pairing["product_id"].isin(selected_sku_ids)
    ]
    filtered_summary = filtered_summary[
        filtered_summary["product_id"].isin(selected_sku_ids)
    ]

if filtered_unit_overview.empty:
    st.warning("目前篩選條件下沒有活動單位資料。")
    st.stop()


# =========================================================
# 聯動篩選提示條（反映 SKU 篩選狀態）
# =========================================================

if len(selected_sku_labels) == 1:
    pill_col, _ = st.columns([1, 3])

    with pill_col:
        if st.button(
            f"🔶 聯動篩選中：{selected_sku_labels[0]}　✕",
            key="clear_sku_filter_pill",
            use_container_width=True,
        ):
            st.session_state["campaign_insight_sku_filter"] = []
            st.rerun()


# =========================================================
# KPI 卡片列
# =========================================================

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

total_incremental_gmv = filtered_unit_overview[
    "net_revenue_effect_total"
].sum()

multi_avg = filtered_unit_overview.loc[
    filtered_unit_overview["classification"] == "多活動合併,不可分離",
    "net_revenue_effect_per_day",
].mean()

single_avg = filtered_unit_overview.loc[
    filtered_unit_overview["classification"] == "可分離,單一活動",
    "net_revenue_effect_per_day",
].mean()

if (
    pd.notna(multi_avg)
    and pd.notna(single_avg)
    and single_avg != 0
):
    synergy_uplift = (multi_avg - single_avg) / abs(single_avg)
else:
    synergy_uplift = None

best_lever = None

if not filtered_summary.empty:
    lever_stats = filtered_summary.groupby(
        "activity_type", as_index=False
    ).agg(
        total_gain=("total_gain", "sum"),
        total_intervals=("interval_count", "sum"),
    )
    lever_stats = lever_stats[lever_stats["total_intervals"] > 0]

    if not lever_stats.empty:
        lever_stats["avg_gain"] = (
            lever_stats["total_gain"] / lever_stats["total_intervals"]
        )
        best_lever = lever_stats.sort_values(
            "avg_gain", ascending=False
        ).iloc[0]["activity_type"]

risk_mask = compute_risk_mask(filtered_unit_overview)
risk_rate_count = int(risk_mask.sum())

with kpi_col1:
    st.metric(
        "📈 累積淨增益 GMV",
        f"${total_incremental_gmv:,.0f}",
        help="篩選範圍內所有活動單位淨營收效應合計",
    )

with kpi_col2:
    st.metric(
        "✨ 疊加綜效提升率 Synergy Uplift",
        (
            f"{synergy_uplift:+.0%}"
            if synergy_uplift is not None
            else "-"
        ),
        help="多活動疊加單位 vs 可分離單一活動單位的平均淨增益差異",
    )

with kpi_col3:
    st.metric(
        "🏆 最佳槓桿 Best Lever",
        best_lever or "-",
        help="配對比對彙總中，平均淨增益貢獻最高的活動類型",
    )

with kpi_col4:
    st.metric(
        "⚠ 風險檔數 Risk Rate",
        f"{risk_rate_count} 檔",
        help="存量降價效應(絕對值) > 量增效應(絕對值) 的活動單位數",
    )


# =========================================================
# 商品視角 Product View
# =========================================================

st.markdown(
    """
    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h3>商品視角 Product View</h3>
    </div>
    """,
    unsafe_allow_html=True,
)

product_view_title_col, product_view_tag_col = st.columns([3, 2])

with product_view_title_col:
    st.caption(
        "回答：這款商品在哪個活動組合下增益最大？"
        "折扣要給到幾折？"
    )

with product_view_tag_col:
    st.markdown(
        """
        <div style="text-align:right;">
            <span style="background:#eef0ff; color:#4E56A6;
                         border-radius:999px; padding:0.3rem 0.8rem;
                         font-size:0.82rem; font-weight:600;">
                工作表5・活動單位總覽(vs基準)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

product_chart_col1, product_chart_col2 = st.columns(2)

with product_chart_col1:
    st.markdown("###### 活動單位淨增益排行")
    st.caption("點一下長條可切換下方「雙軌配對拆解圖」檢視對象；顏色＝分類")

    ranking_data = filtered_unit_overview.sort_values(
        "net_revenue_effect_per_day", ascending=True
    )

    # unit_code（如 M10）是「月份＋活動組合特徵」代碼，同一代碼
    # 常常同時對應多個活動組合完全相同的商品，只顯示 unit_code
    # 會讓不同商品的長條疊在同一個標籤下、點擊時也分不出點到
    # 哪個商品。改用 unit_code（商品名稱）複合標籤，確保每根
    # 長條、每次點擊都能唯一對應到一組(商品,活動組合)。
    ranking_data["unit_product_label"] = (
        ranking_data["unit_code"] + "（" + ranking_data["product_name"] + "）"
    )

    ranking_figure = px.bar(
        ranking_data,
        x="net_revenue_effect_per_day",
        y="unit_product_label",
        color="color_category",
        orientation="h",
        color_discrete_map=CATEGORY_COLOR_MAP,
        labels={
            "net_revenue_effect_per_day": "淨營收效應/日",
            "unit_product_label": "活動單位",
            "color_category": "分類",
        },
        hover_data={
            "product_name": True,
            "corresponding_activities_label": True,
            "days": True,
        },
    )

    ranking_row_count = len(ranking_data)

    # 這張圖不套用共用的 resolve_bar_chart_sizing()「筆數多寡
    # 二選一分支」（筆數一多就強制捲動）。使用者希望不論資料
    # 筆數多寡，都盡量在不捲動縱向捲軸的情況下看到「至少一半
    # 以上」的資料列，效果比照「活動類型淨增益彙總」——固定
    # 撐滿 CHART_MAX_HEIGHT，柱寬交給 Plotly 用 bargap 自動
    # 壓縮（不寫死），資料越多柱子越細但仍等比例撐滿同一個
    # 高度。只有筆數多到每格會薄於 MINIMUM_ROW_SLOT_PX（幾乎
    # 看不出長條）時，才退回「自然高度＋外層捲動＋固定半寬」，
    # 避免資料極端多時整張圖糊成一條色塊。
    MINIMUM_ROW_SLOT_PX = 3

    if (
        ranking_row_count > 0
        and CHART_MAX_HEIGHT / ranking_row_count
        >= MINIMUM_ROW_SLOT_PX
    ):
        ranking_height = CHART_MAX_HEIGHT
        ranking_bar_width = None
    else:
        ranking_height, ranking_bar_width = resolve_bar_chart_sizing(
            ranking_row_count, normal_bar_width=0.5
        )

    ranking_figure.update_traces(width=ranking_bar_width)

    ranking_figure.update_layout(
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        height=ranking_height,
    )

    with st.container(height=CHART_MAX_HEIGHT):
        bar_event = st.plotly_chart(
            ranking_figure,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            key="unit_ranking_chart",
        )

    if bar_event and bar_event.selection.points:
        clicked_unit_label = bar_event.selection.points[0].get("y")

        if clicked_unit_label:
            st.session_state[
                "campaign_insight_selected_unit"
            ] = clicked_unit_label

with product_chart_col2:
    st.markdown("###### 折扣與增益散佈矩陣")
    st.caption("X：折扣率　Y：淨營收效應/日　氣泡：活動天數")

    scatter_data = filtered_unit_overview.dropna(
        subset=["discount_rate", "net_revenue_effect_per_day"]
    )

    if scatter_data.empty:
        st.info("目前沒有可繪製折扣率的資料（可能缺少基準售價）。")
    else:
        scatter_figure = px.scatter(
            scatter_data,
            x="discount_rate",
            y="net_revenue_effect_per_day",
            size=scatter_data["days"].clip(lower=1),
            color="color_category",
            color_discrete_map=CATEGORY_COLOR_MAP,
            labels={
                "discount_rate": "折扣率",
                "net_revenue_effect_per_day": "淨營收效應/日",
                "color_category": "分類",
            },
            hover_data={
                "unit_code": True,
                "product_name": True,
                "days": True,
            },
        )

        scatter_figure.update_layout(
            xaxis_tickformat=".0%",
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            height=CHART_MAX_HEIGHT,
        )

        with st.container(height=CHART_MAX_HEIGHT):
            st.plotly_chart(
                scatter_figure, use_container_width=True
            )

st.markdown("###### 活動單位總覽明細")

unit_detail_columns = [
    "unit_code",
    "product_name",
    "corresponding_activities_label",
    "days",
    "baseline_price",
    "unit_avg_price",
    "volume_effect_per_day",
    "price_effect_per_day",
    "net_revenue_effect_per_day",
    "classification",
    "hint",
]

unit_detail_display = filtered_unit_overview[
    unit_detail_columns
].sort_values(
    "net_revenue_effect_per_day", ascending=False
).reset_index(drop=True)

unit_detail_column_config = {
    "baseline_price": st.column_config.NumberColumn(
        "基準售價", format="%.0f"
    ),
    "unit_avg_price": st.column_config.NumberColumn(
        "活動售價", format="%.0f"
    ),
    "volume_effect_per_day": st.column_config.NumberColumn(
        "量增效應/日", format="%.0f"
    ),
    "price_effect_per_day": st.column_config.NumberColumn(
        "存量降價/日", format="%.0f"
    ),
    "net_revenue_effect_per_day": st.column_config.NumberColumn(
        "淨增益/日", format="%.0f"
    ),
    "hint": st.column_config.Column("提示"),
}
unit_detail_column_config.update(
    default_column_config(
        unit_detail_display,
        exclude=unit_detail_column_config.keys(),
    )
)

table_event = st.dataframe(
    unit_detail_display,
    use_container_width=True,
    hide_index=True,
    column_config=unit_detail_column_config,
    on_select="rerun",
    selection_mode="single-row",
    key="unit_overview_detail_table",
)

if table_event and table_event.selection.rows:
    selected_row_index = table_event.selection.rows[0]
    st.session_state["campaign_insight_selected_unit"] = (
        unit_detail_display.iloc[selected_row_index][
            "unit_code"
        ]
    )

st.markdown("##### 💡 系統洞察")

with st.container(border=True):
    if selected_sku_ids:
        st.markdown("**💡 商品洞察**")
        st.caption("依目前篩選的商品逐一列出最佳與較差的活動組合。")

        for sku_index, sku_id in enumerate(selected_sku_ids):
            product_rows = filtered_unit_overview[
                filtered_unit_overview["product_id"] == sku_id
            ]

            if product_rows.empty:
                continue

            product_name = product_rows.iloc[0]["product_name"]

            if sku_index > 0:
                st.divider()

            st.markdown(f"**{product_name}（{sku_id}）**")

            best_row = product_rows.sort_values(
                "net_revenue_effect_per_day", ascending=False
            ).iloc[0]

            best_gift_text = lookup_gift_text(
                sku_id, best_row["unit_code"]
            )

            st.markdown(
                f"- ✅ 表現最佳：活動單位 **{best_row['unit_code']}**"
                f"（{best_row['corresponding_activities_label']}）"
                + (
                    f"，搭配「{best_gift_text}」"
                    if best_gift_text
                    else ""
                )
                + f"，淨增益達 "
                f"<span style='color:#009B73;font-weight:700;'>"
                f"+\\${best_row['net_revenue_effect_per_day']:,.0f}/日"
                f"</span>。",
                unsafe_allow_html=True,
            )

            worst_row = product_rows.sort_values(
                "net_revenue_effect_per_day", ascending=True
            ).iloc[0]

            worst_is_risky = (
                pd.notna(worst_row["price_effect_per_day"])
                and worst_row["price_effect_per_day"] < 0
                and abs(worst_row["price_effect_per_day"])
                > abs(worst_row["volume_effect_per_day"])
            )

            risk_note = (
                "，存量降價效應大於量增效應，屬於毛利侵蝕風險"
                if worst_is_risky
                else ""
            )

            st.markdown(
                f"- ⚠️ 表現較差：活動單位 **{worst_row['unit_code']}**"
                f"（{worst_row['corresponding_activities_label']}），"
                f"淨增益 \\${worst_row['net_revenue_effect_per_day']:,.0f}/日"
                f"{risk_note}。"
            )

            st.markdown("**📊 折扣率洞察**")
            render_discount_rate_insight(
                product_rows, show_product_name=False
            )

    else:
        st.markdown("**💡 最佳折扣區間**")

        discount_candidates = filtered_unit_overview[
            filtered_unit_overview["net_revenue_effect_per_day"] > 0
        ].sort_values("net_revenue_effect_per_day", ascending=False)

        if discount_candidates.empty:
            st.caption("目前篩選範圍內沒有淨增益為正的活動單位。")
        else:
            best_row = discount_candidates.iloc[0]
            discount_text = (
                f"{best_row['discount_rate']:.0%}折"
                if pd.notna(best_row["discount_rate"])
                else "折扣率不明"
            )

            st.markdown(
                f"【{best_row['product_name']}】活動單位 "
                f"**{best_row['unit_code']}**：{discount_text}"
                f"（\\${best_row['unit_avg_price']:,.0f}），"
                f"淨增益達 "
                f"<span style='color:#009B73;font-weight:700;'>"
                f"+\\${best_row['net_revenue_effect_per_day']:,.0f}/日"
                f"</span>，是目前篩選範圍內表現最佳的組合。",
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("**🚩 毛利侵蝕預警**")

        risk_rows = filtered_unit_overview[risk_mask].sort_values(
            "net_revenue_effect_per_day"
        )

        if risk_rows.empty:
            st.success("目前篩選範圍內未發現明顯的毛利侵蝕風險。")
        else:
            worst_risk = risk_rows.iloc[0]

            st.error(
                f"{worst_risk['unit_code']}"
                f"（{worst_risk['product_name']}）"
                f"售價降至 \\${worst_risk['unit_avg_price']:,.0f}，"
                "銷量未相應提升，"
                f"淨營收虧損 "
                f"\\${worst_risk['net_revenue_effect_per_day']:,.0f}/日。"
                "建議下檔縮減折幅，改以贈品吸引轉換。"
            )

        st.divider()
        st.markdown("**📊 折扣率洞察**")
        render_discount_rate_insight(
            filtered_unit_overview, show_product_name=True
        )


st.divider()


# =========================================================
# 活動視角 Activity View
# =========================================================

st.markdown(
    """
    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h3>活動視角 Activity View</h3>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "回答：哪些活動類型或搭配對淨營收貢獻最大？"
    "疊加效果能不能拆解成個別活動的貢獻？"
)

activity_chart_col1, activity_chart_col2 = st.columns(2)

with activity_chart_col1:
    st.markdown("###### 活動類型淨增益彙總")
    st.caption("加總各SKU的配對比對結果；黃色＝含不可拆分區間")

    if filtered_summary.empty:
        st.info("目前篩選條件下沒有配對比對彙總資料。")
    else:
        summary_by_type = filtered_summary.groupby(
            "activity_type", as_index=False
        ).agg(
            total_gain=("total_gain", "sum"),
            has_unsplit=(
                "split_status",
                lambda series: bool(
                    (series == "無法拆分").any()
                ),
            ),
        ).sort_values("total_gain")

        # px.bar 的 labels 參數只能改圖例「標題」文字，改不了
        # 圖例裡布林值本身顯示的文字，所以要先把 True/False
        # 轉成中文字串欄位，再拿這個字串欄位當 color。
        summary_by_type["拆分狀態"] = summary_by_type[
            "has_unsplit"
        ].map({True: "不可拆分", False: "可拆分"})

        summary_figure = px.bar(
            summary_by_type,
            x="total_gain",
            y="activity_type",
            orientation="h",
            color="拆分狀態",
            color_discrete_map={
                "不可拆分": "#F2C744",
                "可拆分": "#4E56A6",
            },
            labels={
                "total_gain": "增益合計",
                "activity_type": "活動類型",
                "拆分狀態": "拆分狀態",
            },
        )

        summary_height, summary_bar_width = resolve_bar_chart_sizing(
            len(summary_by_type), normal_bar_width=0.5
        )

        # 跟「活動單位淨增益排行」圖一致：資料量少時也固定補回
        # 相同柱寬，避免兩張圖因為分支不同而間距觀感不一致。
        if summary_bar_width is None:
            summary_bar_width = 0.5 / 2

        summary_figure.update_traces(width=summary_bar_width)

        summary_figure.update_layout(
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            height=summary_height,
        )

        with st.container(height=CHART_MAX_HEIGHT):
            st.plotly_chart(
                summary_figure, use_container_width=True
            )

with activity_chart_col2:
    st.markdown("###### 雙軌配對拆解圖 Paired Comparison Waterfall")

    if filtered_pairing.empty:
        st.info("目前篩選條件下沒有配對比對明細資料。")
    else:
        # unit_code（如 M10）常常同時對應多個活動組合完全相同的
        # 商品，只用 target_unit 篩選會把不同商品的配對列混在
        # 一起，下面的活動類型選單也會出現同名重複選項。改用
        # unit_code（商品名稱）複合標籤，確保每個選項、每次篩選
        # 都唯一對應到一組(商品,活動組合)。
        filtered_pairing["unit_product_label"] = (
            filtered_pairing["target_unit"]
            + "（"
            + filtered_pairing["product_name"]
            + "）"
        )

        available_units = (
            filtered_pairing["unit_product_label"]
            .drop_duplicates()
            .tolist()
        )

        stored_default_unit = st.session_state.get(
            "campaign_insight_selected_unit"
        )

        if stored_default_unit not in available_units:
            stored_default_unit = available_units[0]

        # 用下拉選單讓使用者可以直接選要看哪個活動單位，不用
        # 依賴「點長條」或「點下方表格列」這種容易被忽略的
        # 互動方式。key 用新的名稱，不直接沿用
        # campaign_insight_selected_unit 當 widget key，因為
        # 下方「配對比對-單一活動拆解」表格的點擊事件也會寫入
        # campaign_insight_selected_unit，兩者共用同一個 key
        # 會在同一次執行裡違反「widget 實例化後不能再改它的
        # session_state」規則而丟例外。
        default_unit = st.selectbox(
            "選擇要檢視的活動單位",
            options=available_units,
            index=available_units.index(stored_default_unit),
            key="campaign_insight_unit_direct_select",
        )

        st.session_state["campaign_insight_selected_unit"] = default_unit

        st.caption(
            f"目前檢視：{default_unit} "
            "— 可用上方下拉選單、點長條或點下方表格任一列切換"
        )

        unit_pairing_rows = filtered_pairing[
            filtered_pairing["unit_product_label"] == default_unit
        ].reset_index(drop=True)

        # 上面新增的活動單位下拉選單一定會顯示，一定要扣一次
        # 高度；如果這個單位還疊加了多個活動、多顯示第二個
        # selectbox，再扣一次，抵銷多出來的高度，讓標題
        # （頂部對齊）與圖表（底部）都能跟左欄切齊。
        extra_widget_count = 1

        if len(unit_pairing_rows) > 1:
            activity_type_choice = st.selectbox(
                f"「{default_unit}」疊加了多個活動，選擇要檢視的活動",
                options=unit_pairing_rows["activity_type"].tolist(),
                key="campaign_insight_waterfall_activity_type",
            )
            waterfall_row = unit_pairing_rows[
                unit_pairing_rows["activity_type"]
                == activity_type_choice
            ].iloc[0]
            extra_widget_count += 1
        else:
            waterfall_row = unit_pairing_rows.iloc[0]

        waterfall_container_height = (
            CHART_MAX_HEIGHT
            - EXTRA_WIDGET_HEIGHT_OFFSET * extra_widget_count
        )

        candidate_value = waterfall_row["candidate_weighted_avg_daily_revenue"]
        actual_value = waterfall_row["actual_daily_revenue"]
        net_value = waterfall_row["net_gain_per_day"]

        # 圖表本身的高度要跟外層 st.container(height=
        # waterfall_container_height) 完全一致，不能像之前用
        # resolve_bar_chart_sizing(3, ...) 固定回傳
        # CHART_MAX_HEIGHT(460)——因為外層容器已經依疊加活動
        # selectbox 是否顯示，扣掉對應的 EXTRA_WIDGET_HEIGHT_OFFSET
        # 縮小過，圖表高度若還是撐到完整的460，會比容器高，
        # 底部（X軸刻度文字）就會被容器裁掉、看不到。柱寬交給
        # Plotly 自動計算（bargap），效果比照頁面其他圖表「全螢幕
        # 撐滿、等比例縮放」的作法。
        waterfall_height = waterfall_container_height
        waterfall_bar_width = None

        waterfall_bar_kwargs = (
            {"width": waterfall_bar_width}
            if waterfall_bar_width is not None
            else {}
        )

        waterfall_figure = go.Figure(
            data=[
                go.Bar(
                    x=["目標單位 實際日營收", "對照候選單位 加權日營收", "淨增益/日"],
                    y=[
                        actual_value if pd.notna(actual_value) else 0,
                        candidate_value if pd.notna(candidate_value) else 0,
                        net_value if pd.notna(net_value) else 0,
                    ],
                    **waterfall_bar_kwargs,
                    marker_color=[
                        "#4E56A6",
                        "#9AA5B1",
                        (
                            "#009B73"
                            if pd.notna(net_value) and net_value >= 0
                            else "#C62828"
                        ),
                    ],
                    text=[
                        f"${actual_value:,.0f}" if pd.notna(actual_value) else "-",
                        f"${candidate_value:,.0f}" if pd.notna(candidate_value) else "-",
                        f"${net_value:,.0f}" if pd.notna(net_value) else "-",
                    ],
                    textposition="outside",
                )
            ]
        )

        waterfall_figure.update_layout(
            margin={"l": 10, "r": 10, "t": 20, "b": 10},
            yaxis_title="日營收",
            showlegend=False,
            height=waterfall_height,
        )

        with st.container(height=waterfall_container_height):
            st.plotly_chart(
                waterfall_figure, use_container_width=True
            )

if not filtered_pairing.empty:
    pairing_tab1, pairing_tab2 = st.tabs(
        ["單一活動拆解", "彙總"]
    )

    with pairing_tab1:
        pairing_display_columns = [
            "activity_type",
            "product_name",
            "target_unit",
            "target_unit_days",
            "candidate_units",
            "candidate_weighted_avg_daily_revenue",
            "actual_daily_revenue",
            "net_gain_per_day",
            "split_status",
        ]

        pairing_display = filtered_pairing[
            pairing_display_columns
        ].reset_index(drop=True)

        pairing_column_config = {
            "candidate_weighted_avg_daily_revenue": (
                st.column_config.NumberColumn(
                    "對照組日營收", format="%.0f"
                )
            ),
            "actual_daily_revenue": st.column_config.NumberColumn(
                "實際日營收", format="%.0f"
            ),
            "net_gain_per_day": st.column_config.NumberColumn(
                "淨增益/日", format="%.0f"
            ),
        }
        pairing_column_config.update(
            default_column_config(
                pairing_display,
                exclude=pairing_column_config.keys(),
            )
        )

        pairing_table_event = st.dataframe(
            pairing_display,
            use_container_width=True,
            hide_index=True,
            column_config=pairing_column_config,
            on_select="rerun",
            selection_mode="single-row",
            key="pairing_detail_table",
        )

        if pairing_table_event and pairing_table_event.selection.rows:
            selected_pairing_index = (
                pairing_table_event.selection.rows[0]
            )
            selected_pairing_row = pairing_display.iloc[
                selected_pairing_index
            ]
            st.session_state["campaign_insight_selected_unit"] = (
                f"{selected_pairing_row['target_unit']}"
                f"（{selected_pairing_row['product_name']}）"
            )

    with pairing_tab2:
        st.caption(
            "各活動組合的拆分狀態、涵蓋天數與總增益"
            "（對應參考報表工作表7）。"
        )

        summary_view_columns = [
            "corresponding_activities",
            "split_status",
            "total_days",
            "total_gain",
        ]

        summary_view_display = filtered_summary[
            summary_view_columns
        ].reset_index(drop=True)

        summary_view_column_config = {
            "corresponding_activities": st.column_config.Column(
                "活動組合"
            ),
            "split_status": st.column_config.Column("拆分狀態"),
            "total_days": st.column_config.NumberColumn(
                "涵蓋天數", format="%d"
            ),
            "total_gain": st.column_config.NumberColumn(
                "總增益", format="%.0f"
            ),
        }

        st.dataframe(
            summary_view_display,
            use_container_width=True,
            hide_index=True,
            column_config=summary_view_column_config,
        )

st.markdown("##### 💡 系統洞察")

with st.container(border=True):
    st.markdown("**💡 最佳活動搭檔**")

    combo_candidates = filtered_summary[
        filtered_summary["split_status"] == "無法拆分"
    ].copy()

    if combo_candidates.empty:
        st.caption("目前篩選範圍內沒有可比較的疊加活動組合。")
    else:
        combo_candidates["avg_gain"] = (
            combo_candidates["total_gain"]
            / combo_candidates["interval_count"].replace(0, pd.NA)
        )
        combo_best = combo_candidates.sort_values(
            "avg_gain", ascending=False
        ).iloc[0]

        combo_worst = combo_candidates.sort_values(
            "avg_gain", ascending=True
        ).iloc[0]

        st.markdown(
            f"「{combo_best['corresponding_activities']}」"
            f"平均淨增益 "
            f"<span style='color:#009B73;font-weight:700;'>"
            f"+\\${combo_best['avg_gain']:,.0f}/單位</span>，"
            f"為目前篩選範圍內最佳疊加組合；"
            f"相較之下「{combo_worst['corresponding_activities']}」"
            f"平均淨增益僅 \\${combo_worst['avg_gain']:,.0f}/單位，"
            "建議優先安排前者的活動搭配。",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("**⚠ 統計信賴度警示**")

    low_confidence_rows = filtered_pairing[
        (filtered_pairing["target_unit_days"] < MINIMUM_DAYS_FOR_CONFIDENCE)
        & (filtered_pairing["split_status"] != "可拆分")
    ]

    if low_confidence_rows.empty:
        st.info("目前篩選範圍內未發現明顯的統計信賴度風險。")
    else:
        example_row = low_confidence_rows.iloc[0]

        st.warning(
            f"{example_row['target_unit']}"
            f"（{example_row['product_id']}）"
            f"涵蓋天數僅 {int(example_row['target_unit_days'])} 天"
            "且無同月同組合對照期，已退回安靜期基準估算，"
            "建議僅作輔助參考。"
        )
