from pathlib import Path
import sys

import pandas as pd
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

from src.persistence import (
    clear_analysis_snapshot,
    diff_dataframes,
    load_state,
    load_sales_snapshot_into_session,
    save_sales_snapshot,
)
from src.session_helpers import (
    clear_downstream_analysis,
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
# 資料來源切換：示範資料 / 自行上傳
# =========================================================

DEMO_SALES_EXCEL_PATH = PROJECT_ROOT / "assets" / "demo_sales_data.xlsx"


def load_demo_sales_into_session() -> bool:
    """
    示範模式：優先使用資料庫中已確認的 3-4 月銷量標準化資料；
    若資料庫尚無資料，改為自動讀取內建示範 Excel 並自動完成
    欄位辨識與標準化，略過使用者手動上傳與確認的流程。
    """

    if st.session_state.get("sales_demo_loaded"):
        return st.session_state.get("standardized_dataframe") is not None

    try:
        load_sales_snapshot_into_session()
    except Exception:
        pass

    if st.session_state.get("standardized_dataframe") is None:
        if not DEMO_SALES_EXCEL_PATH.exists():
            st.error("找不到內建示範資料，請改用自行上傳。")
            return False

        try:
            demo_excel = pd.ExcelFile(DEMO_SALES_EXCEL_PATH)
            sheet_name = (
                "銷量原始資料(零填補)"
                if "銷量原始資料(零填補)" in demo_excel.sheet_names
                else demo_excel.sheet_names[0]
            )
            demo_dataframe = pd.read_excel(demo_excel, sheet_name=sheet_name)

            demo_mapping = suggest_sales_mapping(demo_dataframe)
            demo_standardized = standardize_sales_data(
                dataframe=demo_dataframe,
                mapping=demo_mapping,
            )

            st.session_state.column_mapping = demo_mapping
            st.session_state.standardized_dataframe = demo_standardized

        except Exception as error:
            st.error(f"示範資料自動處理失敗：{error}")
            return False

    st.session_state.uploaded_file_name = "demo_sales_data.xlsx"
    st.session_state.uploaded_file_bytes = b""
    st.session_state.sales_data_confirmed = True
    st.session_state["sales_demo_loaded"] = True

    return True


DEMO_SALES_LABEL = "使用示範資料（3-4 月）"
UPLOAD_SALES_LABEL = "自行上傳檔案"

data_source_mode = st.radio(
    "資料來源",
    options=[DEMO_SALES_LABEL, UPLOAD_SALES_LABEL],
    index=0,
    horizontal=True,
    key="sales_data_source_mode",
)

use_demo_data = data_source_mode == DEMO_SALES_LABEL

if not use_demo_data:
    st.session_state["sales_demo_loaded"] = False

if use_demo_data:
    demo_ready = load_demo_sales_into_session()

    if not demo_ready:
        st.stop()

    standardized_dataframe = st.session_state.get("standardized_dataframe")

    st.success("✅ 示範資料已載入：檔案上傳、欄位對應、品質檢查皆已完成。")

    try:
        data_summary = create_sales_data_summary(standardized_dataframe)
        quality_summary = create_sales_quality_summary(standardized_dataframe)
        issues_dataframe = get_sales_issues_dataframe(standardized_dataframe)
    except Exception as error:
        st.error(f"無法建立資料摘要：{error}")
        st.stop()

    result_col1, result_col2, result_col3, result_col4 = st.columns(4)

    result_col1.metric("標準化資料筆數", f"{data_summary['total_rows']:,}")
    result_col2.metric("需確認資料", f"{data_summary['issue_rows']:,}")
    result_col3.metric("商品數量", f"{data_summary['product_count']:,}")
    result_col4.metric("銷量合計", f"{data_summary['total_quantity']:,.0f}")

    st.caption(f"資料日期範圍：{data_summary['date_range_text']}")

    with st.expander("查看資料品質摘要", expanded=False):
        st.dataframe(quality_summary, use_container_width=True, hide_index=True)

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
        column for column in preview_columns if column in standardized_dataframe.columns
    ]

    st.caption("目前僅預覽前 50 筆資料。")

    preview_dataframe = standardized_dataframe[available_preview_columns].head(50)

    st.dataframe(
        preview_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config=default_column_config(preview_dataframe),
    )

    if issues_dataframe.empty:
        st.success("未發現需要人工確認的資料品質問題。")
    else:
        st.warning(f"共有 {len(issues_dataframe):,} 筆資料需要確認。")
        with st.expander("查看需要確認的資料", expanded=False):
            issues_preview = issues_dataframe.head(100)
            st.dataframe(
                issues_preview,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(issues_preview),
            )

    st.info("✅ 銷量資料已完成最終確認，可以繼續處理活動資料。")

    st.stop()


st.divider()


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
