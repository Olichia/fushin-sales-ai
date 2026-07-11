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


from src.session_helpers import (
    clear_activity_data,
    get_activity_dataframe,
    get_activity_file_names,
    get_activity_sheet_names,
    initialize_session_state,
    load_activity_sheet,
    remove_activity_file,
    save_activity_excel,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.title("活動資料上傳")

st.write(
    "本頁用於上傳品牌活動 Excel。"
    "可以同時保存多個月份的活動檔案，"
    "並預覽每一份檔案中的不同工作表。"
)

st.info(
    "目前請上傳 3 月與 4 月品牌活動檔案。"
)


# =========================================================
# 多檔案上傳
# =========================================================

uploaded_files = st.file_uploader(
    "上傳活動 Excel，可一次選擇多份",
    type=["xlsx"],
    accept_multiple_files=True,
    key="activity_excel_uploader",
)


if uploaded_files:
    successful_files = []
    failed_files = []

    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.getvalue()

        existing_files = (
            st.session_state.activity_uploaded_files
        )

        is_new_or_changed = (
            uploaded_file.name
            not in existing_files
            or existing_files[
                uploaded_file.name
            ] != file_bytes
        )

        if not is_new_or_changed:
            continue

        try:
            save_activity_excel(
                file_name=uploaded_file.name,
                file_bytes=file_bytes,
            )

            successful_files.append(
                uploaded_file.name
            )

        except Exception as error:
            failed_files.append(
                {
                    "file_name": uploaded_file.name,
                    "error": str(error),
                }
            )

    if successful_files:
        st.success(
            "成功保存："
            + "、".join(successful_files)
        )

    for failed_file in failed_files:
        st.error(
            f"{failed_file['file_name']} "
            f"讀取失敗：{failed_file['error']}"
        )


# =========================================================
# 已上傳檔案列表
# =========================================================

activity_file_names = (
    get_activity_file_names()
)


if not activity_file_names:
    st.warning(
        "目前尚未上傳活動 Excel。"
    )
    st.stop()


st.subheader("已上傳的活動檔案")


file_summary_rows = []

for file_name in activity_file_names:
    sheet_names = get_activity_sheet_names(
        file_name
    )

    file_summary_rows.append(
        {
            "檔案名稱": file_name,
            "工作表數量": len(
                sheet_names
            ),
            "工作表": "、".join(
                sheet_names
            ),
        }
    )


file_summary_dataframe = pd.DataFrame(
    file_summary_rows
)


st.dataframe(
    file_summary_dataframe,
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# 選擇檔案
# =========================================================

current_file_name = (
    st.session_state.get(
        "selected_activity_file_name"
    )
)


default_file_index = 0

if current_file_name in activity_file_names:
    default_file_index = (
        activity_file_names.index(
            current_file_name
        )
    )


selected_file_name = st.selectbox(
    "選擇要預覽的活動檔案",
    options=activity_file_names,
    index=default_file_index,
)


sheet_names = get_activity_sheet_names(
    selected_file_name
)


if not sheet_names:
    st.error(
        "這份 Excel 沒有可讀取的工作表。"
    )
    st.stop()


# =========================================================
# 選擇工作表
# =========================================================

current_sheet_name = (
    st.session_state.get(
        "selected_activity_sheet_name"
    )
)


default_sheet_index = 0

if (
    current_file_name == selected_file_name
    and current_sheet_name in sheet_names
):
    default_sheet_index = (
        sheet_names.index(
            current_sheet_name
        )
    )


selected_sheet_name = st.selectbox(
    "選擇要預覽的工作表",
    options=sheet_names,
    index=default_sheet_index,
)


if st.button(
    "載入活動工作表",
    type="primary",
):
    try:
        dataframe = load_activity_sheet(
            file_name=selected_file_name,
            sheet_name=selected_sheet_name,
            header=0,
        )

        st.success(
            f"已載入："
            f"{selected_file_name}"
            f"／{selected_sheet_name}"
        )

    except Exception as error:
        st.error(
            f"工作表載入失敗：{error}"
        )


# =========================================================
# 顯示目前載入的工作表
# =========================================================

activity_dataframe = (
    get_activity_dataframe()
)


loaded_file_name = (
    st.session_state.get(
        "selected_activity_file_name"
    )
)

loaded_sheet_name = (
    st.session_state.get(
        "selected_activity_sheet_name"
    )
)


if (
    activity_dataframe is not None
    and loaded_file_name == selected_file_name
    and loaded_sheet_name == selected_sheet_name
):
    st.divider()

    st.subheader("活動資料預覽")

    st.caption(
        f"目前預覽："
        f"{loaded_file_name}"
        f"／{loaded_sheet_name}"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "資料列數",
        len(activity_dataframe),
    )

    col2.metric(
        "欄位數",
        len(activity_dataframe.columns),
    )

    col3.metric(
        "缺值總數",
        int(
            activity_dataframe
            .isna()
            .sum()
            .sum()
        ),
    )

    st.write("欄位名稱：")

    st.write(
        list(
            activity_dataframe.columns
        )
    )

    st.dataframe(
        activity_dataframe.head(30),
        use_container_width=True,
    )

    st.info(
        "活動檔案已保存。"
        "下一步會建立活動資料標準化頁面。"
    )


# =========================================================
# 檔案管理
# =========================================================

st.divider()

st.subheader("檔案管理")


col1, col2 = st.columns(2)


with col1:
    if st.button(
        f"移除目前檔案：{selected_file_name}"
    ):
        remove_activity_file(
            selected_file_name
        )

        st.rerun()


with col2:
    if st.button(
        "清除所有活動檔案"
    ):
        clear_activity_data()
        st.rerun()