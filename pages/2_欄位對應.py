import pandas as pd
import streamlit as st

from session_helpers import (
    get_uploaded_dataframe,
    initialize_session_state,
)


initialize_session_state()

st.title("欄位對應")


dataframe = get_uploaded_dataframe()

if dataframe is None:
    st.warning(
        "尚未載入工作表，"
        "請先到「資料上傳」頁上傳並載入資料。"
    )
    st.stop()


st.success(
    "目前資料："
    f"{st.session_state.uploaded_file_name}"
    "／"
    f"{st.session_state.selected_sheet_name}"
)


SYSTEM_FIELDS = [
    "不使用",
    "sale_date",
    "product_id",
    "product_name",
    "quantity",
]


DEFAULT_MAPPING = {
    "日期": "sale_date",
    "訂單日期": "sale_date",
    "銷售日期": "sale_date",
    "編號": "product_id",
    "商品編號": "product_id",
    "產品編號": "product_id",
    "SKU": "product_id",
    "品號": "product_id",
    "商品名稱": "product_name",
    "產品名稱": "product_name",
    "品名": "product_name",
    "銷量": "quantity",
    "銷售量": "quantity",
    "銷售數量": "quantity",
    "數量": "quantity",
}


previous_mapping = st.session_state.get(
    "column_mapping",
    {},
)

mapping_result = {}


st.write(
    "請確認每個原始欄位對應到哪個系統欄位。"
)


with st.form("column_mapping_form"):
    for column in dataframe.columns:
        original_name = str(column).strip()

        selected_default = previous_mapping.get(
            original_name,
            DEFAULT_MAPPING.get(
                original_name,
                "不使用",
            ),
        )

        if selected_default not in SYSTEM_FIELDS:
            selected_default = "不使用"

        selected_field = st.selectbox(
            f"原始欄位：{original_name}",
            options=SYSTEM_FIELDS,
            index=SYSTEM_FIELDS.index(
                selected_default
            ),
            key=f"mapping_select_{original_name}",
        )

        mapping_result[original_name] = (
            selected_field
        )

    submitted = st.form_submit_button(
        "儲存欄位對應",
        type="primary",
    )


if submitted:
    selected_targets = [
        target
        for target in mapping_result.values()
        if target != "不使用"
    ]

    duplicate_targets = {
        target
        for target in selected_targets
        if selected_targets.count(target) > 1
    }

    required_fields = {
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
    }

    selected_fields = set(
        selected_targets
    )

    missing_fields = (
        required_fields - selected_fields
    )

    if duplicate_targets:
        st.error(
            "下列系統欄位被重複指定："
            + ", ".join(
                sorted(duplicate_targets)
            )
        )

    elif missing_fields:
        st.error(
            "尚未完成必要欄位："
            + ", ".join(
                sorted(missing_fields)
            )
        )

    else:
        st.session_state.column_mapping = (
            mapping_result
        )

        st.session_state.standardized_dataframe = (
            None
        )

        st.success(
            "欄位對應已儲存。"
            "請前往「資料品質」。"
        )


st.subheader("欄位對應預覽")

display_mapping = (
    st.session_state.column_mapping
    if st.session_state.column_mapping
    else mapping_result
)

mapping_dataframe = pd.DataFrame(
    [
        {
            "原始欄位": source,
            "系統欄位": target,
        }
        for source, target in (
            display_mapping.items()
        )
    ]
)

st.dataframe(
    mapping_dataframe,
    use_container_width=True,
)