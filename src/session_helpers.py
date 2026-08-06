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
    "sales_data_confirmed": False,
    "standardized_dataframe": None,

    # -----------------------------
    # 活動資料
    # -----------------------------
    # 格式：
    # {
    #     "3月品牌活動_通路.xlsx": b"...",
    #     "4月品牌活動_通路.xlsx": b"...",
    # }
    "activity_uploaded_files": {},

    # 每一份檔案包含的工作表名稱
    # {
    #     "3月品牌活動_通路.xlsx": [
    #         "檔期",
    #         "三月鋪底",
    #         ...
    #     ]
    # }
    "activity_sheet_names": {},

    "selected_activity_file_name": None,
    "selected_activity_sheet_name": None,
    "activity_uploaded_dataframe": None,

    # 活動資料處理狀態
    "activity_data_confirmed": False,
    "processed_march_activity_file_name": None,
    "processed_april_activity_file_name": None,

    # 活動標準化結果
    "activity_standardized_dataframe": None,
    "activity_calendar_dataframe": None,
    "promotion_benefits_dataframe": None,
    "activity_issues_dataframe": None,
    "main_activity_summary_dataframe": None,
    "other_activity_summary_dataframe": None,

    # -----------------------------
    # 整合及成效分析資料
    # -----------------------------
    "integrated_sales_activity_dataframe": None,
    "integration_issues_dataframe": None,
    "activity_performance_dataframe": None,

    # -----------------------------
    # 策略報告
    # -----------------------------
    "strategy_report_dataframe": None,
    "strategy_report_text": None,

    # -----------------------------
    # 活動單位分析（新方法論，對應參考報表工作表3-7）
    # -----------------------------
    "unit_analysis_completed": False,
    "activity_unit_timeline_dataframe": None,
    "activity_unit_timeline_wide_dataframe": None,
    "activity_unit_price_dataframe": None,
    "activity_unit_overview_dataframe": None,
    "activity_waterfall_pairing_dataframe": None,
    "activity_waterfall_summary_dataframe": None,

    # -----------------------------
    # AI 顧問
    # -----------------------------
    "ai_chat_messages": [],
    "ai_last_context": None,

    # -----------------------------
    # 情境模擬・已採用方案
    # -----------------------------
    "adopted_whatif_scenarios": [],

    # -----------------------------
    # 介面主題
    # -----------------------------
    "dark_mode": False,
    "landing_page_dismissed": False,
    "sidebar_icon_only": False,
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
            if isinstance(default_value, dict):
                st.session_state[key] = {}

            elif isinstance(default_value, list):
                st.session_state[key] = []

            else:
                st.session_state[key] = default_value


# =========================================================
# 共用清除工具
# =========================================================

def reset_session_keys(
    keys: list[str],
) -> None:
    """
    將指定的 Session State key
    恢復成 SESSION_DEFAULTS 中的預設值。

    若 key 尚未存在於 SESSION_DEFAULTS，
    會直接略過，避免產生 KeyError。
    """

    for key in keys:
        if key not in SESSION_DEFAULTS:
            continue

        default_value = SESSION_DEFAULTS[key]

        if isinstance(default_value, dict):
            st.session_state[key] = {}

        elif isinstance(default_value, list):
            st.session_state[key] = []

        else:
            st.session_state[key] = default_value


def clear_downstream_analysis() -> None:
    """
    清除資料更新後已經失效的下游結果。

    銷量或活動資料只要發生改變，
    舊的整合資料、成效分析、策略結果
    及 AI 對話脈絡就不應繼續保留。
    """

    downstream_keys = [
        "integrated_sales_activity_dataframe",
        "integration_issues_dataframe",
        "activity_performance_dataframe",
        "strategy_report_dataframe",
        "strategy_report_text",
        "ai_chat_messages",
        "ai_last_context",
        "unit_analysis_completed",
        "activity_unit_timeline_dataframe",
        "activity_unit_timeline_wide_dataframe",
        "activity_unit_price_dataframe",
        "activity_unit_overview_dataframe",
        "activity_waterfall_pairing_dataframe",
        "activity_waterfall_summary_dataframe",
    ]

    reset_session_keys(
        downstream_keys
    )


def clear_sales_processing_results() -> None:
    """
    清除銷量工作表載入後產生的處理結果。

    保留已上傳的 Excel 檔案，
    但清除欄位對應、標準化資料與確認狀態。

    只重置銷量資料自己的確認狀態；活動資料本身沒有改變，
    不需要連帶要求使用者回頭重新確認活動資料。
    """

    sales_processing_keys = [
        "column_mapping",
        "sales_data_confirmed",
        "standardized_dataframe",
    ]

    reset_session_keys(
        sales_processing_keys
    )

    clear_downstream_analysis()


def clear_activity_processing_results() -> None:
    """
    清除活動資料處理結果。

    保留已上傳的活動 Excel，
    但清除月份紀錄、標準化結果、
    摘要、問題資料與確認狀態。

    只重置活動資料自己的確認狀態；銷量資料本身沒有改變，
    不需要連帶要求使用者回頭重新確認銷量資料。
    """

    activity_processing_keys = [
        "activity_data_confirmed",
        "processed_march_activity_file_name",
        "processed_april_activity_file_name",
        "activity_standardized_dataframe",
        "activity_calendar_dataframe",
        "promotion_benefits_dataframe",
        "activity_issues_dataframe",
        "main_activity_summary_dataframe",
        "other_activity_summary_dataframe",
    ]

    reset_session_keys(
        activity_processing_keys
    )

    clear_downstream_analysis()


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

    上傳新檔案後會清除：
    - 舊工作表資料
    - 舊欄位對應
    - 舊標準化資料
    - 舊整合及分析結果
    """

    if not file_name:
        raise ValueError(
            "銷量 Excel 檔案名稱不可為空。"
        )

    if not file_bytes:
        raise ValueError(
            "銷量 Excel 檔案內容不可為空。"
        )

    excel_buffer = io.BytesIO(
        file_bytes
    )

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

    st.session_state.excel_sheet_names = list(
        excel_file.sheet_names
    )

    # 上傳新銷量檔案時，
    # 清除舊工作表及處理結果。
    st.session_state.selected_sheet_name = None
    st.session_state.uploaded_dataframe = None

    clear_sales_processing_results()

    return list(
        excel_file.sheet_names
    )


def load_uploaded_sheet(
    sheet_name: str,
) -> pd.DataFrame:
    """
    從 Session State 讀取銷量 Excel 工作表。

    切換工作表後會清除舊欄位對應、
    標準化資料及下游分析結果。
    """

    file_bytes = st.session_state.get(
        "uploaded_file_bytes"
    )

    if not file_bytes:
        raise ValueError(
            "尚未上傳銷量 Excel 檔案。"
        )

    sheet_names = st.session_state.get(
        "excel_sheet_names",
        [],
    )

    if sheet_name not in sheet_names:
        raise ValueError(
            f"找不到銷量工作表：{sheet_name}"
        )

    excel_buffer = io.BytesIO(
        file_bytes
    )

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

    # 切換或重新載入工作表後，
    # 舊欄位對應及標準化結果失效。
    clear_sales_processing_results()

    return dataframe


def get_uploaded_dataframe() -> pd.DataFrame | None:
    """
    取得目前銷量 DataFrame。

    回傳 copy，避免其他頁面直接修改
    Session State 內的原始資料。
    """

    dataframe = st.session_state.get(
        "uploaded_dataframe"
    )

    if dataframe is None:
        return None

    return dataframe.copy()


def clear_uploaded_data() -> None:
    """
    清除所有銷量資料。

    不清除活動上傳及活動標準化資料，
    但會清除依賴銷量資料的整合與分析結果。
    """

    sales_keys = [
        "uploaded_file_name",
        "uploaded_file_bytes",
        "excel_sheet_names",
        "selected_sheet_name",
        "uploaded_dataframe",
        "column_mapping",
        "sales_data_confirmed",
        "standardized_dataframe",
    ]

    reset_session_keys(
        sales_keys
    )

    clear_downstream_analysis()


# =========================================================
# 活動 Excel
# =========================================================

def save_activity_excel(
    file_name: str,
    file_bytes: bytes,
) -> list[str]:
    """
    保存一份活動 Excel。

    可以重複呼叫，因此可同時保存：
    - 3 月活動檔
    - 4 月活動檔
    - 其他月份或活動檔

    上傳或更新活動檔案後，
    會清除舊活動標準化及下游分析結果。
    """

    if not file_name:
        raise ValueError(
            "活動 Excel 檔案名稱不可為空。"
        )

    if not file_bytes:
        raise ValueError(
            "活動 Excel 檔案內容不可為空。"
        )

    excel_buffer = io.BytesIO(
        file_bytes
    )

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

    activity_files[file_name] = (
        file_bytes
    )

    sheet_names_mapping[file_name] = list(
        excel_file.sheet_names
    )

    st.session_state.activity_uploaded_files = (
        activity_files
    )

    st.session_state.activity_sheet_names = (
        sheet_names_mapping
    )

    clear_activity_processing_results()

    return list(
        excel_file.sheet_names
    )


def load_activity_sheet(
    file_name: str,
    sheet_name: str,
    header: int | None = 0,
) -> pd.DataFrame:
    """
    從保存的活動 Excel 中讀取指定工作表。

    此函式主要提供活動資料預覽
    或標準化函式讀取工作表使用。
    """

    activity_files = st.session_state.get(
        "activity_uploaded_files",
        {},
    )

    if file_name not in activity_files:
        raise ValueError(
            f"找不到活動檔案：{file_name}"
        )

    sheet_names = get_activity_sheet_names(
        file_name
    )

    if sheet_name not in sheet_names:
        raise ValueError(
            f"檔案「{file_name}」中"
            f"找不到工作表「{sheet_name}」。"
        )

    file_bytes = activity_files[
        file_name
    ]

    excel_buffer = io.BytesIO(
        file_bytes
    )

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

    return list(
        sheet_names_mapping.get(
            file_name,
            [],
        )
    )


def get_activity_dataframe() -> pd.DataFrame | None:
    """
    取得目前載入的活動工作表。

    回傳 copy，避免直接修改
    Session State 中的原始資料。
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

    移除檔案後，舊的活動標準化、
    整合及分析結果都會被清除。
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

    clear_activity_processing_results()


def clear_activity_data() -> None:
    """
    清除所有活動資料。

    不清除銷量資料，
    但會清除依賴活動資料的整合及分析結果。
    """

    activity_keys = [
        "activity_uploaded_files",
        "activity_sheet_names",
        "selected_activity_file_name",
        "selected_activity_sheet_name",
        "activity_uploaded_dataframe",
        "activity_data_confirmed",
        "processed_march_activity_file_name",
        "processed_april_activity_file_name",
        "activity_standardized_dataframe",
        "activity_calendar_dataframe",
        "promotion_benefits_dataframe",
        "activity_issues_dataframe",
        "main_activity_summary_dataframe",
        "other_activity_summary_dataframe",
    ]

    reset_session_keys(
        activity_keys
    )

    clear_downstream_analysis()