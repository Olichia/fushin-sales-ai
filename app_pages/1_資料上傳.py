from pathlib import Path
import sys

import streamlit as st


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


# =========================================================
# 專案模組
# =========================================================

from src.column_labels import default_column_config
from src.sales_processing import (
    FIELD_LABELS,
    REQUIRED_FIELDS,
    create_sales_data_summary,
    create_sales_quality_summary,
    get_sales_issues_dataframe,
    standardize_sales_data,
    suggest_sales_mapping,
    validate_sales_mapping,
)

from src.demo_data import apply_demo_sales_data_to_session
from src.session_helpers import (
    clear_uploaded_data,
    initialize_session_state,
    load_uploaded_sheet,
    save_uploaded_excel,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.markdown(
    """
    <div class="step-label">STEP 01</div>
    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>銷量資料處理</h1>
    </div>
    <p class="product-page-description">
        上傳銷量 Excel 後，系統會自動載入工作表、辨識必要欄位，
        並完成日期、商品編號、商品名稱與銷量的標準化及品質檢查。
        請依序完成檔案上傳、工作表確認、欄位對應與最終確認。
    </p>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 資料來源選擇：示範資料／自訂上傳資料
#
# 預設示範資料，讓使用者一打開分頁就直接看到「已上傳並完成
# 欄位分析」後的畫面，不用先上傳才看得到成果；切換成自訂上傳
# 資料則會恢復成尚未上傳的空白畫面，逼使用者重新走一次上傳
# 流程（且不會寫入資料庫，重新整理瀏覽器就會清空）。
# =========================================================

st.subheader("資料來源")

sales_data_mode = st.radio(
    "資料來源",
    options=["示範資料", "自訂上傳資料"],
    horizontal=True,
    key="sales_data_mode",
    label_visibility="collapsed",
)

if sales_data_mode == "示範資料":
    apply_demo_sales_data_to_session()

    st.info(
        "目前顯示示範資料的處理結果。"
        "若要改用自己的資料，請切換至「自訂上傳資料」。"
    )

    demo_standardized_dataframe = st.session_state[
        "standardized_dataframe"
    ]

    demo_data_summary = create_sales_data_summary(
        demo_standardized_dataframe
    )

    demo_quality_summary = create_sales_quality_summary(
        demo_standardized_dataframe
    )

    demo_issues_dataframe = get_sales_issues_dataframe(
        demo_standardized_dataframe
    )

    demo_col1, demo_col2, demo_col3, demo_col4 = st.columns(4)

    demo_col1.metric(
        "標準化資料筆數",
        f"{demo_data_summary['total_rows']:,}",
    )
    demo_col2.metric(
        "需確認資料",
        f"{demo_data_summary['issue_rows']:,}",
    )
    demo_col3.metric(
        "商品數量",
        f"{demo_data_summary['product_count']:,}",
    )
    demo_col4.metric(
        "銷量合計",
        f"{demo_data_summary['total_quantity']:,.0f}",
    )

    st.caption(
        f"資料日期範圍：{demo_data_summary['date_range_text']}"
    )

    with st.expander("查看資料品質摘要", expanded=False):
        st.dataframe(
            demo_quality_summary,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("標準化資料預覽")

    demo_preview_columns = [
        column
        for column in [
            "source_row_number",
            "sale_date",
            "product_id",
            "product_name",
            "quantity",
            "has_quality_issue",
            "quality_issue_description",
        ]
        if column in demo_standardized_dataframe.columns
    ]

    st.caption("目前僅預覽前 50 筆資料。")

    demo_preview_dataframe = demo_standardized_dataframe[
        demo_preview_columns
    ].head(50)

    st.dataframe(
        demo_preview_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config=default_column_config(
            demo_preview_dataframe
        ),
    )

    if demo_issues_dataframe.empty:
        st.success("未發現需要人工確認的資料品質問題。")
    else:
        st.warning(
            f"共有 {len(demo_issues_dataframe):,} 筆資料需要確認。"
        )

    st.success(
        "示範銷量資料已就緒，可以繼續處理活動資料。"
    )

    st.stop()


# 切換回自訂上傳資料時，先清掉示範資料，恢復成尚未上傳的
# 空白畫面，不能讓示範資料看起來像是使用者自己上傳的結果。
if st.session_state.get("is_demo_sales_data"):
    clear_uploaded_data()
    st.session_state["is_demo_sales_data"] = False


# =========================================================
# 小工具函式
# =========================================================

def get_default_index(
    options: list[str],
    selected_value: str | None,
) -> int:
    """
    取得 selectbox 的預設位置。

    找不到指定值時，預設選擇第一個欄位。
    """

    if selected_value in options:
        return options.index(
            selected_value
        )

    return 0


def reset_mapping_widget_state() -> None:
    """
    切換檔案或工作表後，
    清除舊的欄位選擇元件狀態。
    """

    for system_field in REQUIRED_FIELDS:
        widget_key = (
            f"sales_mapping_{system_field}"
        )

        st.session_state.pop(
            widget_key,
            None,
        )

    st.session_state.pop(
        "sales_final_confirmation_checkbox",
        None,
    )


# =========================================================
# Step 1：上傳 Excel
# =========================================================

st.subheader("1. 上傳銷量 Excel")

with st.container(border=True):
    st.markdown(
        """
        <div class="upload-card-heading">
            <div class="upload-card-icon">📊</div>
            <div>
                <div class="upload-card-title">銷量資料匯入</div>
                <div class="upload-card-description">
                    必要欄位包含訂單日期、商品編號、商品名稱與銷量。
                    系統會自動讀取 Excel 工作表並建議欄位對應。
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "選擇 Excel 檔案",
        type=["xlsx"],
        key="main_excel_uploader",
        help="目前支援 .xlsx 格式。",
    )


if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()

    is_new_file = (
        st.session_state.uploaded_file_name
        != uploaded_file.name
        or st.session_state.uploaded_file_bytes
        != file_bytes
    )

    if is_new_file:
        try:
            with st.spinner(
                "正在讀取 Excel 檔案……"
            ):
                save_uploaded_excel(
                    file_name=uploaded_file.name,
                    file_bytes=file_bytes,
                )

            reset_mapping_widget_state()

            st.success(
                f"已成功讀取：{uploaded_file.name}"
            )

        except Exception as error:
            st.error(
                f"Excel 讀取失敗：{error}"
            )
            st.stop()


# =========================================================
# 尚未上傳檔案
# =========================================================

if not st.session_state.uploaded_file_bytes:
    st.info(
        "請先上傳一份銷量 Excel 檔案。"
    )
    st.stop()


# =========================================================
# 已上傳檔案資訊
# =========================================================

file_size_mb = (
    len(st.session_state.uploaded_file_bytes)
    / 1024
    / 1024
)

file_info_col1, file_info_col2 = st.columns(2)

file_info_col1.metric(
    "目前檔案",
    st.session_state.uploaded_file_name,
)

file_info_col2.metric(
    "檔案大小",
    f"{file_size_mb:.2f} MB",
)


# =========================================================
# Step 2：選擇並自動載入工作表
# =========================================================

st.subheader("2. 選擇工作表")

sheet_names = (
    st.session_state.excel_sheet_names
)

if not sheet_names:
    st.warning(
        "目前 Excel 中沒有可使用的工作表。"
    )
    st.stop()


current_sheet = (
    st.session_state.selected_sheet_name
)

default_sheet_index = 0

if current_sheet in sheet_names:
    default_sheet_index = sheet_names.index(
        current_sheet
    )


selected_sheet = st.selectbox(
    "選擇要使用的工作表",
    options=sheet_names,
    index=default_sheet_index,
)


# 使用者切換工作表時，自動載入；
# 不需要再按「載入此工作表」。
should_load_sheet = (
    st.session_state.selected_sheet_name
    != selected_sheet
    or st.session_state.uploaded_dataframe
    is None
)

if should_load_sheet:
    try:
        with st.spinner(
            f"正在載入工作表：{selected_sheet}……"
        ):
            load_uploaded_sheet(
                selected_sheet
            )

        reset_mapping_widget_state()

        st.success(
            f"已載入工作表：{selected_sheet}"
        )

    except Exception as error:
        st.error(
            f"工作表載入失敗：{error}"
        )
        st.stop()


dataframe = (
    st.session_state.uploaded_dataframe
)

if dataframe is None:
    st.warning(
        "目前無法取得工作表資料。"
    )
    st.stop()


# =========================================================
# 原始資料摘要
# =========================================================

summary_col1, summary_col2, summary_col3 = (
    st.columns(3)
)

summary_col1.metric(
    "資料列數",
    f"{len(dataframe):,}",
)

summary_col2.metric(
    "欄位數",
    f"{len(dataframe.columns):,}",
)

summary_col3.metric(
    "缺值總數",
    f"{int(dataframe.isna().sum().sum()):,}",
)


with st.expander(
    "查看原始資料",
    expanded=False,
):
    st.caption(
        "目前僅預覽前 20 筆資料。"
    )

    st.write(
        "原始欄位："
    )

    st.write(
        list(dataframe.columns)
    )

    st.dataframe(
        dataframe.head(20),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# Step 3：確認必要欄位
# =========================================================

st.divider()
st.subheader("3. 確認必要欄位")

st.caption(
    "系統會根據欄位名稱自動建議。"
    "若辨識不正確，再使用下拉選單調整。"
)


column_options = [
    str(column).strip()
    for column in dataframe.columns
]

if not column_options:
    st.error(
        "目前工作表沒有任何欄位。"
    )
    st.stop()


try:
    suggested_mapping = (
        suggest_sales_mapping(
            dataframe
        )
    )

except Exception as error:
    st.error(
        f"自動欄位辨識失敗：{error}"
    )
    st.stop()


saved_mapping = st.session_state.get(
    "column_mapping",
    {},
)


# 在 selectbox 建立前設定合理預設值
for system_field in REQUIRED_FIELDS:
    widget_key = (
        f"sales_mapping_{system_field}"
    )

    saved_value = saved_mapping.get(
        system_field
    )

    suggested_value = (
        saved_value
        or suggested_mapping.get(
            system_field
        )
    )

    # 舊選項不存在於新工作表時，
    # 改用系統建議值。
    current_widget_value = (
        st.session_state.get(
            widget_key
        )
    )

    if (
        current_widget_value
        not in column_options
    ):
        if suggested_value in column_options:
            st.session_state[
                widget_key
            ] = suggested_value

        else:
            st.session_state[
                widget_key
            ] = column_options[0]


mapping: dict[str, str] = {}

mapping_columns = st.columns(2)

for index, system_field in enumerate(
    REQUIRED_FIELDS
):
    widget_key = (
        f"sales_mapping_{system_field}"
    )

    saved_value = saved_mapping.get(
        system_field
    )

    suggested_value = (
        saved_value
        or suggested_mapping.get(
            system_field
        )
    )

    with mapping_columns[index % 2]:
        selected_column = st.selectbox(
            FIELD_LABELS[system_field],
            options=column_options,
            index=get_default_index(
                column_options,
                suggested_value,
            ),
            key=widget_key,
        )

        mapping[system_field] = (
            selected_column
        )


# =========================================================
# 欄位對應摘要
# =========================================================

mapping_rows = []

for system_field in REQUIRED_FIELDS:
    selected_column = mapping[
        system_field
    ]

    automatic_column = (
        suggested_mapping.get(
            system_field
        )
    )

    if selected_column == automatic_column:
        mapping_status = "系統自動辨識"

    else:
        mapping_status = "手動調整"

    mapping_rows.append(
        {
            "系統標準欄位": (
                FIELD_LABELS[
                    system_field
                ]
            ),
            "原始資料欄位": (
                selected_column
            ),
            "對應方式": mapping_status,
        }
    )


import pandas as pd

mapping_preview = pd.DataFrame(
    mapping_rows
)

st.dataframe(
    mapping_preview,
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# 欄位驗證
# =========================================================

mapping_errors = (
    validate_sales_mapping(
        mapping
    )
)

if mapping_errors:
    for error in mapping_errors:
        st.error(error)


# =========================================================
# 檢查目前欄位是否與已處理版本不同
# =========================================================

standardized_dataframe = (
    st.session_state.get(
        "standardized_dataframe"
    )
)

mapping_has_changed = (
    bool(saved_mapping)
    and saved_mapping != mapping
)

if (
    standardized_dataframe is not None
    and mapping_has_changed
):
    st.warning(
        "目前欄位選擇已變更。"
        "請重新按下處理按鈕，"
        "才能更新標準化資料。"
    )


# =========================================================
# Step 4：標準化與品質檢查
# =========================================================

st.divider()
st.subheader("4. 處理銷量資料")

st.write(
    "按下按鈕後，系統會完成："
)

st.markdown(
    """
- 日期格式標準化
- 商品編號與商品名稱整理
- 銷量轉換為數值
- 缺值檢查
- 負數及零銷量檢查
- 完全重複資料檢查
- 同日同商品多筆資料檢查
"""
)


process_button = st.button(
    "確認欄位並處理銷量資料",
    type="primary",
    use_container_width=True,
    disabled=bool(mapping_errors),
)


if process_button:
    try:
        with st.spinner(
            "正在進行資料標準化與品質檢查……"
        ):
            processed_dataframe = (
                standardize_sales_data(
                    dataframe=dataframe,
                    mapping=mapping,
                )
            )

        st.session_state.column_mapping = (
            mapping.copy()
        )

        st.session_state.standardized_dataframe = (
            processed_dataframe
        )

        st.session_state.sales_data_confirmed = (
            False
        )

        st.session_state[
            "sales_final_confirmation_checkbox"
        ] = False

        standardized_dataframe = (
            processed_dataframe
        )

        mapping_has_changed = False

        st.success(
            "銷量資料標準化與品質檢查完成。"
        )

    except Exception as error:
        st.error(
            f"資料處理失敗：{error}"
        )


# =========================================================
# 尚未產生標準化資料
# =========================================================

standardized_dataframe = (
    st.session_state.get(
        "standardized_dataframe"
    )
)

if standardized_dataframe is None:
    st.info(
        "確認欄位後，按下「確認欄位並處理銷量資料」，"
        "即可產生標準化資料表。"
    )

else:
    # 若欄位已變更，不讓使用者確認舊結果
    result_is_current = (
        st.session_state.column_mapping
        == mapping
    )

    if not result_is_current:
        st.warning(
            "下方結果是先前欄位設定產生的資料。"
            "請重新執行資料處理後再確認。"
        )

    # =====================================================
    # Step 5：標準化結果
    # =====================================================

    st.divider()
    st.subheader("5. 標準化結果與最終確認")

    try:
        data_summary = (
            create_sales_data_summary(
                standardized_dataframe
            )
        )

        quality_summary = (
            create_sales_quality_summary(
                standardized_dataframe
            )
        )

        issues_dataframe = (
            get_sales_issues_dataframe(
                standardized_dataframe
            )
        )

    except Exception as error:
        st.error(
            f"無法建立資料摘要：{error}"
        )
        st.stop()


    result_col1, result_col2, result_col3, result_col4 = (
        st.columns(4)
    )

    result_col1.metric(
        "標準化資料筆數",
        f"{data_summary['total_rows']:,}",
    )

    result_col2.metric(
        "需確認資料",
        f"{data_summary['issue_rows']:,}",
    )

    result_col3.metric(
        "商品數量",
        f"{data_summary['product_count']:,}",
    )

    result_col4.metric(
        "銷量合計",
        f"{data_summary['total_quantity']:,.0f}",
    )


    st.caption(
        "資料日期範圍："
        f"{data_summary['date_range_text']}"
    )


    # =====================================================
    # 品質摘要
    # =====================================================

    with st.expander(
        "查看資料品質摘要",
        expanded=(
            data_summary[
                "issue_rows"
            ]
            > 0
        ),
    ):
        st.dataframe(
            quality_summary,
            use_container_width=True,
            hide_index=True,
        )


    # =====================================================
    # 標準化資料預覽
    # =====================================================

    st.subheader("標準化資料預覽")

    preview_columns = [
        "source_row_number",
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
        "has_quality_issue",
        "quality_issue_description",
    ]

    available_preview_columns = [
        column
        for column in preview_columns
        if column
        in standardized_dataframe.columns
    ]

    st.caption(
        "目前僅預覽前 50 筆資料。"
    )

    preview_dataframe = standardized_dataframe[
        available_preview_columns
    ].head(50)

    st.dataframe(
        preview_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config=default_column_config(
            preview_dataframe
        ),
    )


    # =====================================================
    # 問題資料
    # =====================================================

    if issues_dataframe.empty:
        st.success(
            "未發現需要人工確認的資料品質問題。"
        )

    else:
        st.warning(
            f"共有 {len(issues_dataframe):,} 筆資料"
            "需要確認。系統目前只會標記問題，"
            "不會自動刪除或修改原始資料。"
        )

        with st.expander(
            "查看需要確認的資料",
            expanded=False,
        ):
            issues_preview = issues_dataframe.head(100)

            st.dataframe(
                issues_preview,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    issues_preview
                ),
            )


    # =====================================================
    # 下載資料
    # =====================================================

    standardized_csv = (
        standardized_dataframe.to_csv(
            index=False,
            encoding="utf-8-sig",
            date_format="%Y-%m-%d",
        ).encode(
            "utf-8-sig"
        )
    )

    issues_csv = (
        issues_dataframe.to_csv(
            index=False,
            encoding="utf-8-sig",
            date_format="%Y-%m-%d",
        ).encode(
            "utf-8-sig"
        )
    )

    download_col1, download_col2 = (
        st.columns(2)
    )

    with download_col1:
        st.download_button(
            "下載標準化銷量資料",
            data=standardized_csv,
            file_name=(
                "sales_standardized.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

    with download_col2:
        st.download_button(
            "下載資料品質問題",
            data=issues_csv,
            file_name=(
                "sales_quality_issues.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )


    # =====================================================
    # 最終確認
    # =====================================================

    st.divider()
    st.subheader("最終確認")

    if result_is_current:
        confirmed_checkbox = st.checkbox(
            "我已確認欄位對應、標準化資料與品質摘要",
            value=st.session_state.get(
                "sales_data_confirmed",
                False,
            ),
            key=(
                "sales_final_confirmation_checkbox"
            ),
        )

        confirm_button = st.button(
            "確認使用此銷量資料",
            type="primary",
            use_container_width=True,
            disabled=not confirmed_checkbox,
        )

        if confirm_button:
            st.session_state.sales_data_confirmed = (
                True
            )

            st.success(
                "銷量資料已完成最終確認，"
                "可以繼續處理活動資料。"
            )

    else:
        st.info(
            "請先使用目前欄位設定重新處理資料，"
            "才能進行最終確認。"
        )


    if st.session_state.get(
        "sales_data_confirmed",
        False,
    ):
        st.success(
            "目前銷量標準化資料已確認完成。"
        )


# =========================================================
# 清除資料
# =========================================================

st.divider()
st.subheader("重新開始")

st.caption(
    "清除後會移除目前銷量檔案、欄位設定、"
    "標準化資料，以及依賴這份銷量資料的分析結果。"
)

if st.button(
    "清除目前銷量資料"
):
    clear_uploaded_data()

    reset_mapping_widget_state()

    st.rerun()