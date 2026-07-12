import streamlit as st

from session_helpers import (
    clear_uploaded_data,
    initialize_session_state,
    load_uploaded_sheet,
    save_uploaded_excel,
)


initialize_session_state()

st.title("資料上傳")

st.write(
    "上傳 Excel 後，系統會保存檔案與工作表，"
    "供後續欄位對應及資料品質頁使用。"
)


uploaded_file = st.file_uploader(
    "上傳 Excel 檔案",
    type=["xlsx"],
    key="main_excel_uploader",
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
            sheet_names = save_uploaded_excel(
                file_name=uploaded_file.name,
                file_bytes=file_bytes,
            )

            st.success(
                f"已成功讀取：{uploaded_file.name}"
            )

        except Exception as error:
            st.error(
                f"Excel 讀取失敗：{error}"
            )
            st.stop()

    else:
        sheet_names = (
            st.session_state.excel_sheet_names
        )


if st.session_state.uploaded_file_bytes:
    st.success(
        "目前檔案："
        f"{st.session_state.uploaded_file_name}"
    )

    sheet_names = (
        st.session_state.excel_sheet_names
    )

    default_index = 0

    current_sheet = (
        st.session_state.selected_sheet_name
    )

    if current_sheet in sheet_names:
        default_index = sheet_names.index(
            current_sheet
        )

    selected_sheet = st.selectbox(
        "選擇要使用的工作表",
        options=sheet_names,
        index=default_index,
    )

    if st.button(
        "載入此工作表",
        type="primary",
    ):
        try:
            dataframe = load_uploaded_sheet(
                selected_sheet
            )

            st.success(
                f"已載入工作表：{selected_sheet}"
            )

        except Exception as error:
            st.error(
                f"工作表載入失敗：{error}"
            )

    dataframe = (
        st.session_state.uploaded_dataframe
    )

    if dataframe is not None:
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "資料列數",
            len(dataframe),
        )

        col2.metric(
            "欄位數",
            len(dataframe.columns),
        )

        col3.metric(
            "缺值總數",
            int(
                dataframe.isna()
                .sum()
                .sum()
            ),
        )

        st.subheader("目前欄位")

        st.write(
            list(dataframe.columns)
        )

        st.subheader("資料預覽")

        st.dataframe(
            dataframe.head(20),
            use_container_width=True,
        )

        st.info(
            "資料已保存。請從左側進入「欄位對應」。"
        )

    st.divider()

    if st.button("清除目前上傳資料"):
        clear_uploaded_data()
        st.rerun()

else:
    st.info("請先上傳一份 Excel 檔案。")