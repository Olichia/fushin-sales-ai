from __future__ import annotations

import io

import pandas as pd
import streamlit as st


SESSION_DEFAULTS = {
    "uploaded_file_name": None,
    "uploaded_file_bytes": None,
    "excel_sheet_names": [],
    "selected_sheet_name": None,
    "uploaded_dataframe": None,
    "column_mapping": {},
    "standardized_dataframe": None,
}


def initialize_session_state() -> None:
    """
    初始化跨頁共用狀態。
    """

    for key, default_value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def save_uploaded_excel(
    file_name: str,
    file_bytes: bytes,
) -> list[str]:
    """
    將上傳檔案儲存在 session_state，
    並回傳 Excel 工作表名稱。
    """

    excel_buffer = io.BytesIO(file_bytes)

    excel_file = pd.ExcelFile(
        excel_buffer,
        engine="openpyxl",
    )

    st.session_state.uploaded_file_name = file_name
    st.session_state.uploaded_file_bytes = file_bytes
    st.session_state.excel_sheet_names = (
        excel_file.sheet_names
    )

    # 上傳新檔案時，清除舊結果
    st.session_state.selected_sheet_name = None
    st.session_state.uploaded_dataframe = None
    st.session_state.column_mapping = {}
    st.session_state.standardized_dataframe = None

    return excel_file.sheet_names


def load_uploaded_sheet(
    sheet_name: str,
) -> pd.DataFrame:
    """
    從 session_state 的 Excel 位元資料讀取工作表。
    """

    file_bytes = st.session_state.get(
        "uploaded_file_bytes"
    )

    if not file_bytes:
        raise ValueError("尚未上傳 Excel 檔案。")

    excel_buffer = io.BytesIO(file_bytes)

    dataframe = pd.read_excel(
        excel_buffer,
        sheet_name=sheet_name,
        engine="openpyxl",
    )

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    st.session_state.selected_sheet_name = (
        sheet_name
    )

    st.session_state.uploaded_dataframe = (
        dataframe
    )

    # 更換工作表後，清除舊對應與清理結果
    st.session_state.column_mapping = {}
    st.session_state.standardized_dataframe = None

    return dataframe


def get_uploaded_dataframe() -> pd.DataFrame | None:
    """
    取得目前跨頁共用的 DataFrame。
    """

    dataframe = st.session_state.get(
        "uploaded_dataframe"
    )

    if dataframe is None:
        return None

    return dataframe.copy()


def clear_uploaded_data() -> None:
    """
    清除目前上傳資料及後續結果。
    """

    for key, default_value in SESSION_DEFAULTS.items():
        st.session_state[key] = default_value