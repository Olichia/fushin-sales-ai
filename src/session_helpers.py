from __future__ import annotations

import io

import pandas as pd
import streamlit as st


# =========================================================
# Session State 預設值
# =========================================================

SESSION_DEFAULTS = {
    # -----------------------------
    # 銷量資料
    # -----------------------------
    "uploaded_file_name": None,
    "uploaded_file_bytes": None,
    "excel_sheet_names": [],
    "selected_sheet_name": None,
    "uploaded_dataframe": None,
    "column_mapping": {},
    "standardized_dataframe": None,
    "strategy_report_dataframe": None,
    "strategy_report_text": None,

    # -----------------------------
    # AI 顧問
    # -----------------------------
    "ai_chat_messages": [],
    "ai_last_context": None,
    # -----------------------------
    # 活動資料
        # -----------------------------
    # 整合分析資料
    # -----------------------------
    "integrated_sales_activity_dataframe": None,
    "integration_issues_dataframe": None,
    # -----------------------------
    # 格式：
    # {
    #     "3月品牌活動_通路.xlsx": b"...",
    #     "4月品牌活動_通路.xlsx": b"...",
    # }
    "activity_uploaded_files": {},

    # 每一份檔案包含的工作表名稱
    # {
    #     "3月品牌活動_通路.xlsx": ["檔期", "三月鋪底", ...]
    # }
    "activity_sheet_names": {},

    "selected_activity_file_name": None,
    "selected_activity_sheet_name": None,
    "activity_uploaded_dataframe": None,

    # 後續活動標準化會使用
    "activity_standardized_dataframe": None,
    "activity_calendar_dataframe": None,
    "promotion_benefits_dataframe": None,
}


# =========================================================
# 共用初始化
# =========================================================

def initialize_session_state() -> None:
    """
    初始化跨頁共用狀態。

    每次頁面重新執行時，只補上不存在的欄位，
    不會覆蓋已經保存的資料。
    """

    for key, default_value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            # dict 必須建立新的物件，
            # 避免不同 key 意外共用同一份資料。
            if isinstance(default_value, dict):
                st.session_state[key] = {}
            elif isinstance(default_value, list):
                st.session_state[key] = []
            else:
                st.session_state[key] = default_value


# =========================================================
# 銷量 Excel
# =========================================================

def save_uploaded_excel(
    file_name: str,
    file_bytes: bytes,
) -> list[str]:
    """
    保存一份銷量 Excel，
    並回傳工作表名稱。
    """

    excel_buffer = io.BytesIO(file_bytes)

    excel_file = pd.ExcelFile(
        excel_buffer,
        engine="openpyxl",
    )

    st.session_state.uploaded_file_name = (
        file_name
    )

    st.session_state.uploaded_file_bytes = (
        file_bytes
    )

    st.session_state.excel_sheet_names = (
        excel_file.sheet_names
    )

    # 上傳新銷量檔案時清除舊結果
    st.session_state.selected_sheet_name = None
    st.session_state.uploaded_dataframe = None
    st.session_state.column_mapping = {}
    st.session_state.standardized_dataframe = None

    return excel_file.sheet_names


def load_uploaded_sheet(
    sheet_name: str,
) -> pd.DataFrame:
    """
    從 Session State 讀取銷量 Excel 工作表。
    """

    file_bytes = st.session_state.get(
        "uploaded_file_bytes"
    )

    if not file_bytes:
        raise ValueError(
            "尚未上傳銷量 Excel 檔案。"
        )

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

    # 切換工作表後清除舊對應結果
    st.session_state.column_mapping = {}
    st.session_state.standardized_dataframe = None

    return dataframe


def get_uploaded_dataframe() -> pd.DataFrame | None:
    """
    取得目前銷量 DataFrame。
    """

    dataframe = st.session_state.get(
        "uploaded_dataframe"
    )

    if dataframe is None:
        return None

    return dataframe.copy()


def clear_uploaded_data() -> None:
    """
    只清除銷量資料，不影響活動資料。
    """

    sales_keys = [
        "uploaded_file_name",
        "uploaded_file_bytes",
        "excel_sheet_names",
        "selected_sheet_name",
        "uploaded_dataframe",
        "column_mapping",
        "standardized_dataframe",
     "integrated_sales_activity_dataframe",
        "integration_issues_dataframe",
                "activity_performance_dataframe",
        "strategy_report_dataframe",
        "strategy_report_text",
                "ai_chat_messages",
        "ai_last_context",
    ]

    for key in sales_keys:
        default_value = SESSION_DEFAULTS[key]

        if isinstance(default_value, dict):
            st.session_state[key] = {}
        elif isinstance(default_value, list):
            st.session_state[key] = []
        else:
            st.session_state[key] = default_value


# =========================================================
# 活動 Excel
# =========================================================

def save_activity_excel(
    file_name: str,
    file_bytes: bytes,
) -> list[str]:
    """
    保存一份活動 Excel。

    可以重複呼叫，所以能同時保存：
    3 月活動檔和 4 月活動檔。
    """

    excel_buffer = io.BytesIO(file_bytes)

    excel_file = pd.ExcelFile(
        excel_buffer,
        engine="openpyxl",
    )

    activity_files = dict(
        st.session_state.get(
            "activity_uploaded_files",
            {},
        )
    )

    sheet_names_mapping = dict(
        st.session_state.get(
            "activity_sheet_names",
            {},
        )
    )

    activity_files[file_name] = file_bytes

    sheet_names_mapping[file_name] = (
        excel_file.sheet_names
    )

    st.session_state.activity_uploaded_files = (
        activity_files
    )

    st.session_state.activity_sheet_names = (
        sheet_names_mapping
    )

    # 上傳或更新活動檔案後，
    # 清除舊的活動標準化結果。
    st.session_state.activity_standardized_dataframe = (
        None
    )

    st.session_state.activity_calendar_dataframe = (
        None
    )

    st.session_state.promotion_benefits_dataframe = (
        None
    )

    return excel_file.sheet_names


def load_activity_sheet(
    file_name: str,
    sheet_name: str,
    header: int | None = 0,
) -> pd.DataFrame:
    """
    從保存的活動 Excel 中讀取指定工作表。
    """

    activity_files = st.session_state.get(
        "activity_uploaded_files",
        {},
    )

    if file_name not in activity_files:
        raise ValueError(
            f"找不到活動檔案：{file_name}"
        )

    file_bytes = activity_files[file_name]

    excel_buffer = io.BytesIO(file_bytes)

    dataframe = pd.read_excel(
        excel_buffer,
        sheet_name=sheet_name,
        header=header,
        engine="openpyxl",
    )

    if header is not None:
        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

    st.session_state.selected_activity_file_name = (
        file_name
    )

    st.session_state.selected_activity_sheet_name = (
        sheet_name
    )

    st.session_state.activity_uploaded_dataframe = (
        dataframe
    )

    return dataframe


def get_activity_file_names() -> list[str]:
    """
    取得目前已上傳的活動檔案名稱。
    """

    activity_files = st.session_state.get(
        "activity_uploaded_files",
        {},
    )

    return sorted(
        activity_files.keys()
    )


def get_activity_sheet_names(
    file_name: str,
) -> list[str]:
    """
    取得指定活動檔案的工作表名稱。
    """

    sheet_names_mapping = (
        st.session_state.get(
            "activity_sheet_names",
            {},
        )
    )

    return sheet_names_mapping.get(
        file_name,
        [],
    )


def get_activity_dataframe() -> pd.DataFrame | None:
    """
    取得目前載入的活動工作表。
    """

    dataframe = st.session_state.get(
        "activity_uploaded_dataframe"
    )

    if dataframe is None:
        return None

    return dataframe.copy()


def remove_activity_file(
    file_name: str,
) -> None:
    """
    移除指定活動檔案。
    """

    activity_files = dict(
        st.session_state.get(
            "activity_uploaded_files",
            {},
        )
    )

    sheet_names_mapping = dict(
        st.session_state.get(
            "activity_sheet_names",
            {},
        )
    )

    activity_files.pop(
        file_name,
        None,
    )

    sheet_names_mapping.pop(
        file_name,
        None,
    )

    st.session_state.activity_uploaded_files = (
        activity_files
    )

    st.session_state.activity_sheet_names = (
        sheet_names_mapping
    )

    if (
        st.session_state.get(
            "selected_activity_file_name"
        )
        == file_name
    ):
        st.session_state.selected_activity_file_name = (
            None
        )

        st.session_state.selected_activity_sheet_name = (
            None
        )

        st.session_state.activity_uploaded_dataframe = (
            None
        )

    st.session_state.activity_standardized_dataframe = (
        None
    )

    st.session_state.activity_calendar_dataframe = (
        None
    )

    st.session_state.promotion_benefits_dataframe = (
        None
    )


def clear_activity_data() -> None:
    """
    清除所有活動資料，不影響銷量資料。
    """

    activity_keys = [
        "activity_uploaded_files",
        "activity_sheet_names",
        "selected_activity_file_name",
        "selected_activity_sheet_name",
        "activity_uploaded_dataframe",
        "activity_standardized_dataframe",
        "activity_calendar_dataframe",
        "promotion_benefits_dataframe",
        "integrated_sales_activity_dataframe",
        "integration_issues_dataframe",
                "activity_performance_dataframe",
        "strategy_report_dataframe",
        "strategy_report_text",
                "ai_chat_messages",
        "ai_last_context",
    ]

    for key in activity_keys:
        default_value = SESSION_DEFAULTS[key]

        if isinstance(default_value, dict):
            st.session_state[key] = {}
        elif isinstance(default_value, list):
            st.session_state[key] = []
        else:
            st.session_state[key] = default_value