from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st


# 確保 pages 內的程式可以讀取專案根目錄的 src
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.session_helpers import initialize_session_state


initialize_session_state()

st.title("銷售總覽")

st.write(
    "本頁根據標準化後的銷量資料，"
    "顯示整體銷量、商品排行及每日銷量趨勢。"
)


# =========================================================
# 取得標準化資料
# =========================================================

standardized_dataframe = st.session_state.get(
    "standardized_dataframe"
)

if standardized_dataframe is None:
    st.warning(
        "尚未產生標準化資料。"
        "請先依序完成「資料上傳」、「欄位對應」"
        "與「資料品質」。"
    )
    st.stop()


sales = standardized_dataframe.copy()


# =========================================================
# 基本欄位檢查
# =========================================================

required_columns = {
    "sale_date",
    "product_id",
    "product_name",
    "quantity",
}

missing_columns = required_columns - set(
    sales.columns
)

if missing_columns:
    st.error(
        "標準化資料缺少必要欄位："
        + ", ".join(sorted(missing_columns))
    )
    st.stop()


# 再次確保欄位型別正確
sales["sale_date"] = pd.to_datetime(
    sales["sale_date"],
    errors="coerce",
)

sales["quantity"] = pd.to_numeric(
    sales["quantity"],
    errors="coerce",
)

sales["product_id"] = (
    sales["product_id"]
    .astype("string")
    .str.strip()
)

sales["product_name"] = (
    sales["product_name"]
    .astype("string")
    .str.strip()
)


# 分析時先排除日期或銷量無法辨識的資料
analysis_sales = sales.dropna(
    subset=[
        "sale_date",
        "product_id",
        "quantity",
    ]
).copy()

if analysis_sales.empty:
    st.error(
        "目前沒有可供分析的有效銷量資料。"
    )
    st.stop()


# =========================================================
# 側邊欄篩選
# =========================================================

st.sidebar.header("銷售資料篩選")

minimum_date = (
    analysis_sales["sale_date"]
    .min()
    .date()
)

maximum_date = (
    analysis_sales["sale_date"]
    .max()
    .date()
)

selected_date_range = st.sidebar.date_input(
    "選擇分析日期範圍",
    value=(
        minimum_date,
        maximum_date,
    ),
    min_value=minimum_date,
    max_value=maximum_date,
)


if isinstance(
    selected_date_range,
    (tuple, list),
) and len(selected_date_range) == 2:
    selected_start_date = pd.Timestamp(
        selected_date_range[0]
    )

    selected_end_date = pd.Timestamp(
        selected_date_range[1]
    )

else:
    selected_start_date = pd.Timestamp(
        minimum_date
    )

    selected_end_date = pd.Timestamp(
        maximum_date
    )


filtered_sales = analysis_sales[
    analysis_sales["sale_date"].between(
        selected_start_date,
        selected_end_date,
    )
].copy()


product_options = (
    filtered_sales[
        ["product_id", "product_name"]
    ]
    .drop_duplicates(
        subset=["product_id"]
    )
    .sort_values("product_id")
)


product_label_mapping = {
    f"{row.product_id}｜{row.product_name}": (
        row.product_id
    )
    for row in product_options.itertuples()
}


selected_product_labels = (
    st.sidebar.multiselect(
        "選擇商品（可複選）",
        options=list(
            product_label_mapping.keys()
        ),
        default=[],
    )
)


if selected_product_labels:
    selected_product_ids = [
        product_label_mapping[label]
        for label in selected_product_labels
    ]

    filtered_sales = filtered_sales[
        filtered_sales[
            "product_id"
        ].isin(selected_product_ids)
    ].copy()


st.sidebar.caption(
    "未選擇商品時，顯示全部商品。"
)


if filtered_sales.empty:
    st.warning(
        "目前篩選條件下沒有銷量資料。"
    )
    st.stop()


# =========================================================
# KPI 指標
# =========================================================

total_quantity = (
    filtered_sales["quantity"].sum()
)

product_count = (
    filtered_sales["product_id"].nunique()
)

active_days = (
    filtered_sales["sale_date"].nunique()
)

average_daily_quantity = (
    total_quantity / active_days
    if active_days > 0
    else 0
)


daily_sales = (
    filtered_sales
    .groupby(
        "sale_date",
        as_index=False,
    )["quantity"]
    .sum()
    .sort_values("sale_date")
)


if daily_sales.empty:
    highest_sales_date = "-"
    highest_daily_quantity = 0

else:
    highest_daily_row = daily_sales.loc[
        daily_sales["quantity"].idxmax()
    ]

    highest_sales_date = (
        highest_daily_row["sale_date"]
        .strftime("%Y-%m-%d")
    )

    highest_daily_quantity = (
        highest_daily_row["quantity"]
    )


st.subheader("核心指標")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "總銷量",
    f"{total_quantity:,.0f}",
)

col2.metric(
    "商品數",
    f"{product_count:,}",
)

col3.metric(
    "平均每日銷量",
    f"{average_daily_quantity:,.1f}",
)

col4.metric(
    "最高銷量日",
    highest_sales_date,
    delta=f"{highest_daily_quantity:,.0f}",
    delta_color="off",
)


st.caption(
    f"分析期間："
    f"{selected_start_date.strftime('%Y-%m-%d')}"
    f" 至 "
    f"{selected_end_date.strftime('%Y-%m-%d')}，"
    f"共 {active_days} 個有銷量紀錄的日期。"
)


# =========================================================
# 每日銷量趨勢
# =========================================================

st.subheader("每日銷量趨勢")

daily_figure = px.line(
    daily_sales,
    x="sale_date",
    y="quantity",
    markers=True,
    labels={
        "sale_date": "日期",
        "quantity": "銷量",
    },
)

daily_figure.update_layout(
    xaxis_title="日期",
    yaxis_title="銷量",
    hovermode="x unified",
)

st.plotly_chart(
    daily_figure,
    use_container_width=True,
)


# =========================================================
# 商品銷量排行
# =========================================================

st.subheader("商品銷量排行")

product_sales = (
    filtered_sales
    .groupby(
        [
            "product_id",
            "product_name",
        ],
        as_index=False,
    )["quantity"]
    .sum()
    .sort_values(
        "quantity",
        ascending=False,
    )
)


top_n_maximum = min(
    20,
    len(product_sales),
)

top_n = st.slider(
    "顯示前幾名商品",
    min_value=1,
    max_value=max(
        1,
        top_n_maximum,
    ),
    value=min(
        10,
        max(1, top_n_maximum),
    ),
)


top_product_sales = (
    product_sales
    .head(top_n)
    .copy()
)

top_product_sales["product_label"] = (
    top_product_sales["product_id"]
    + "｜"
    + top_product_sales["product_name"]
)


ranking_figure = px.bar(
    top_product_sales.sort_values(
        "quantity",
        ascending=True,
    ),
    x="quantity",
    y="product_label",
    orientation="h",
    labels={
        "quantity": "總銷量",
        "product_label": "商品",
    },
)

ranking_figure.update_layout(
    xaxis_title="總銷量",
    yaxis_title="商品",
)

st.plotly_chart(
    ranking_figure,
    use_container_width=True,
)


# =========================================================
# 月份銷量比較
# =========================================================

st.subheader("月份銷量比較")

monthly_sales = (
    filtered_sales.assign(
        sale_month=filtered_sales[
            "sale_date"
        ].dt.to_period("M").astype(str)
    )
    .groupby(
        "sale_month",
        as_index=False,
    )["quantity"]
    .sum()
)


monthly_figure = px.bar(
    monthly_sales,
    x="sale_month",
    y="quantity",
    labels={
        "sale_month": "月份",
        "quantity": "總銷量",
    },
    text_auto=True,
)

monthly_figure.update_layout(
    xaxis_title="月份",
    yaxis_title="總銷量",
)

st.plotly_chart(
    monthly_figure,
    use_container_width=True,
)


# =========================================================
# 商品每日趨勢
# =========================================================

st.subheader("商品每日銷量趨勢")

product_daily_sales = (
    filtered_sales
    .groupby(
        [
            "sale_date",
            "product_id",
            "product_name",
        ],
        as_index=False,
    )["quantity"]
    .sum()
)

product_daily_sales["product_label"] = (
    product_daily_sales["product_id"]
    + "｜"
    + product_daily_sales["product_name"]
)


product_trend_figure = px.line(
    product_daily_sales,
    x="sale_date",
    y="quantity",
    color="product_label",
    markers=True,
    labels={
        "sale_date": "日期",
        "quantity": "銷量",
        "product_label": "商品",
    },
)

product_trend_figure.update_layout(
    xaxis_title="日期",
    yaxis_title="銷量",
    hovermode="x unified",
)

st.plotly_chart(
    product_trend_figure,
    use_container_width=True,
)


# =========================================================
# 明細表
# =========================================================

st.subheader("商品銷量明細")

display_product_sales = (
    product_sales.rename(
        columns={
            "product_id": "商品編號",
            "product_name": "商品名稱",
            "quantity": "總銷量",
        }
    )
)

st.dataframe(
    display_product_sales,
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# 下載目前分析結果
# =========================================================

download_dataframe = filtered_sales[
    [
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
    ]
].copy()


download_csv = download_dataframe.to_csv(
    index=False,
    encoding="utf-8-sig",
    date_format="%Y-%m-%d",
).encode("utf-8-sig")


st.download_button(
    label="下載目前篩選後的銷量資料",
    data=download_csv,
    file_name="filtered_sales_data.csv",
    mime="text/csv",
)
st.write(
    "本頁根據標準化後的銷量資料，"
    "顯示整體銷量、商品排行及每日銷量趨勢。"
)
st.warning(
    "目前分析保留所有原始銷量資料，"
    "同日同商品多筆紀錄會加總；"
    "在企業確認重複資料定義前，結果應視為初步分析。"
)