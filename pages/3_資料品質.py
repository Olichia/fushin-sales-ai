import pandas as pd
import streamlit as st

from session_helpers import (
    get_uploaded_dataframe,
    initialize_session_state,
)


initialize_session_state()

st.title("資料品質與標準化")


raw_dataframe = get_uploaded_dataframe()

if raw_dataframe is None:
    st.warning(
        "尚未載入工作表，"
        "請先到「資料上傳」頁完成上傳。"
    )
    st.stop()


column_mapping = st.session_state.get(
    "column_mapping",
    {},
)

if not column_mapping:
    st.warning(
        "尚未儲存欄位對應，"
        "請先到「欄位對應」頁完成設定。"
    )
    st.stop()


st.success(
    "目前資料："
    f"{st.session_state.uploaded_file_name}"
    "／"
    f"{st.session_state.selected_sheet_name}"
)


def standardize_sales_data(
    dataframe: pd.DataFrame,
    mapping: dict[str, str],
) -> pd.DataFrame:
    """
    根據使用者確認的欄位對應，
    建立標準化銷量資料。
    """

    rename_mapping = {
        source: target
        for source, target in mapping.items()
        if target != "不使用"
    }

    standardized = dataframe.rename(
        columns=rename_mapping
    ).copy()

    required_columns = [
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
    ]

    standardized = standardized[
        required_columns
    ].copy()

    standardized.insert(
        0,
        "source_row_number",
        range(
            2,
            len(standardized) + 2,
        ),
    )

    standardized["original_sale_date"] = (
        standardized["sale_date"]
    )

    standardized["original_product_id"] = (
        standardized["product_id"]
    )

    standardized["original_quantity"] = (
        standardized["quantity"]
    )

    standardized["sale_date"] = pd.to_datetime(
        standardized["sale_date"],
        errors="coerce",
    )

    standardized["product_id"] = (
        standardized["product_id"]
        .astype("string")
        .str.strip()
        .str.replace(
            r"\.0$",
            "",
            regex=True,
        )
        .replace("", pd.NA)
    )

    standardized["product_name"] = (
        standardized["product_name"]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    standardized["quantity"] = pd.to_numeric(
        standardized["quantity"],
        errors="coerce",
    )

    standardized["missing_sale_date"] = (
        standardized["sale_date"].isna()
    )

    standardized["missing_product_id"] = (
        standardized["product_id"].isna()
    )

    standardized["missing_product_name"] = (
        standardized["product_name"].isna()
    )

    standardized["missing_quantity"] = (
        standardized["quantity"].isna()
    )

    standardized["negative_quantity"] = (
        standardized["quantity"].notna()
        & (standardized["quantity"] < 0)
    )

    standardized["zero_quantity"] = (
        standardized["quantity"].notna()
        & (standardized["quantity"] == 0)
    )

    standardized["exact_duplicate"] = (
        standardized.duplicated(
            subset=[
                "sale_date",
                "product_id",
                "product_name",
                "quantity",
            ],
            keep=False,
        )
    )

    standardized[
        "same_day_product_multiple"
    ] = standardized.duplicated(
        subset=[
            "sale_date",
            "product_id",
        ],
        keep=False,
    )

    issue_columns = [
        "missing_sale_date",
        "missing_product_id",
        "missing_product_name",
        "missing_quantity",
        "negative_quantity",
        "exact_duplicate",
        "same_day_product_multiple",
    ]

    standardized["has_quality_issue"] = (
        standardized[
            issue_columns
        ].any(axis=1)
    )

    return standardized


if st.button(
    "執行標準化與品質檢查",
    type="primary",
):
    try:
        standardized_dataframe = (
            standardize_sales_data(
                raw_dataframe,
                column_mapping,
            )
        )

        st.session_state[
            "standardized_dataframe"
        ] = standardized_dataframe

        st.success(
            "標準化與品質檢查完成。"
        )

    except Exception as error:
        st.error(
            f"標準化失敗：{error}"
        )


standardized_dataframe = (
    st.session_state.get(
        "standardized_dataframe"
    )
)

if standardized_dataframe is None:
    st.info(
        "按下「執行標準化與品質檢查」開始處理。"
    )
    st.stop()


summary_dataframe = pd.DataFrame(
    [
        {
            "問題": "總資料列數",
            "筆數": len(
                standardized_dataframe
            ),
        },
        {
            "問題": "日期缺漏或無法辨識",
            "筆數": int(
                standardized_dataframe[
                    "missing_sale_date"
                ].sum()
            ),
        },
        {
            "問題": "商品編號缺漏",
            "筆數": int(
                standardized_dataframe[
                    "missing_product_id"
                ].sum()
            ),
        },
        {
            "問題": "商品名稱缺漏",
            "筆數": int(
                standardized_dataframe[
                    "missing_product_name"
                ].sum()
            ),
        },
        {
            "問題": "銷量缺漏或無法辨識",
            "筆數": int(
                standardized_dataframe[
                    "missing_quantity"
                ].sum()
            ),
        },
        {
            "問題": "銷量為負數",
            "筆數": int(
                standardized_dataframe[
                    "negative_quantity"
                ].sum()
            ),
        },
        {
            "問題": "銷量為零",
            "筆數": int(
                standardized_dataframe[
                    "zero_quantity"
                ].sum()
            ),
        },
        {
            "問題": "完全重複資料列",
            "筆數": int(
                standardized_dataframe[
                    "exact_duplicate"
                ].sum()
            ),
        },
        {
            "問題": "同日同商品多筆",
            "筆數": int(
                standardized_dataframe[
                    "same_day_product_multiple"
                ].sum()
            ),
        },
        {
            "問題": "有任一品質問題",
            "筆數": int(
                standardized_dataframe[
                    "has_quality_issue"
                ].sum()
            ),
        },
    ]
)


st.subheader("資料品質摘要")

st.dataframe(
    summary_dataframe,
    use_container_width=True,
    hide_index=True,
)


st.subheader("標準化資料預覽")

st.dataframe(
    standardized_dataframe.head(30),
    use_container_width=True,
)


issues_dataframe = standardized_dataframe[
    standardized_dataframe[
        "has_quality_issue"
    ]
].copy()


st.subheader("問題資料")

if issues_dataframe.empty:
    st.success("未發現品質問題。")

else:
    st.warning(
        f"共有 {len(issues_dataframe)} 筆資料"
        "需要確認。系統目前不會自行刪除。"
    )

    st.dataframe(
        issues_dataframe,
        use_container_width=True,
    )


cleaned_csv = standardized_dataframe.to_csv(
    index=False,
    encoding="utf-8-sig",
    date_format="%Y-%m-%d",
).encode("utf-8-sig")


issues_csv = issues_dataframe.to_csv(
    index=False,
    encoding="utf-8-sig",
    date_format="%Y-%m-%d",
).encode("utf-8-sig")


col1, col2 = st.columns(2)

with col1:
    st.download_button(
        label="下載標準化銷量資料",
        data=cleaned_csv,
        file_name="sales_standardized.csv",
        mime="text/csv",
    )

with col2:
    st.download_button(
        label="下載資料品質問題",
        data=issues_csv,
        file_name="sales_quality_issues.csv",
        mime="text/csv",
    )