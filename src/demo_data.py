from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.activity_processing import process_activity_files
from src.activity_unit_analysis import run_activity_unit_analysis
from src.analysis_pipeline import AnalysisSettings, run_full_analysis
from src.persistence import load_state, save_state
from src.sales_processing import standardize_sales_data, suggest_sales_mapping


# =========================================================
# 示範資料來源檔案
#
# 沿用專案根目錄既有的範例 Excel，格式跟一般使用者上傳的檔案
# 完全一樣（銷量走欄位自動辨識、活動走 3 月／4 月範本），所以
# 可以直接餵給正式的處理與分析流程，不需要另外準備假資料。
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEMO_SALES_FILE = PROJECT_ROOT / "銷量新_依日期排序.xlsx"
DEMO_MARCH_ACTIVITY_FILE = PROJECT_ROOT / "3月品牌活動_模板.xlsx"
DEMO_APRIL_ACTIVITY_FILE = PROJECT_ROOT / "4月品牌活動_模板.xlsx"

# 示範資料在資料庫裡一律用這個前綴跟一般 key 區隔，
# 沒有 schema 變更，純粹是命名慣例。
DEMO_DB_KEY_PREFIX = "demo_"

DEMO_ANALYSIS_SETTINGS = AnalysisSettings(
    baseline_days=7,
    post_days=7,
    fill_missing_dates_with_zero=True,
    high_uplift_threshold=0.20,
    low_uplift_threshold=0.0,
    minimum_campaign_sales=1.0,
    only_complete_periods=True,
)

SALES_RESULT_KEYS = [
    "standardized_dataframe",
]

ACTIVITY_RESULT_KEYS = [
    "activity_standardized_dataframe",
    "activity_calendar_dataframe",
    "promotion_benefits_dataframe",
    "activity_issues_dataframe",
    "main_activity_summary_dataframe",
    "other_activity_summary_dataframe",
]

ANALYSIS_RESULT_KEYS = [
    "integrated_sales_activity_dataframe",
    "integration_issues_dataframe",
    "activity_performance_dataframe",
    "strategy_report_dataframe",
    "strategy_report_text",
    "activity_unit_timeline_dataframe",
    "activity_unit_timeline_wide_dataframe",
    "activity_unit_price_dataframe",
    "activity_unit_overview_dataframe",
    "activity_waterfall_pairing_dataframe",
    "activity_waterfall_summary_dataframe",
    "activity_bundle_rules_dataframe",
    "activity_bundle_date_mismatch_dataframe",
]


# =========================================================
# 資料庫快取讀寫
# =========================================================

def _demo_db_key(key: str) -> str:
    return f"{DEMO_DB_KEY_PREFIX}{key}"


def _load_cached_result(keys: list[str]) -> dict[str, object] | None:
    """
    嘗試從資料庫讀回一組示範資料 key。

    只要其中任何一個 key 還沒存過，就視為快取不完整，
    回傳 None 讓呼叫端重新計算整組結果。
    """

    values: dict[str, object] = {}

    for key in keys:
        value = load_state(_demo_db_key(key))

        if value is None:
            return None

        values[key] = value

    return values


def _save_result_to_cache(values: dict[str, object]) -> None:
    for key, value in values.items():
        save_state(_demo_db_key(key), value)


# =========================================================
# 即時運算示範資料（資料庫沒有快取時才會執行）
# =========================================================

def _compute_demo_sales_result() -> dict[str, object]:
    dataframe = pd.read_excel(DEMO_SALES_FILE, engine="openpyxl")

    dataframe.columns = [
        str(column).strip() for column in dataframe.columns
    ]

    mapping = suggest_sales_mapping(dataframe)

    standardized_dataframe = standardize_sales_data(
        dataframe=dataframe,
        mapping=mapping,
    )

    return {"standardized_dataframe": standardized_dataframe}


def _compute_demo_activity_result() -> dict[str, object]:
    march_file_bytes = DEMO_MARCH_ACTIVITY_FILE.read_bytes()
    april_file_bytes = DEMO_APRIL_ACTIVITY_FILE.read_bytes()

    processing_results = process_activity_files(
        march_file_bytes=march_file_bytes,
        april_file_bytes=april_file_bytes,
    )

    return {
        key: processing_results[key] for key in ACTIVITY_RESULT_KEYS
    }


def _compute_demo_analysis_result(
    sales_result: dict[str, object],
    activity_result: dict[str, object],
) -> dict[str, object]:
    sales_dataframe = sales_result["standardized_dataframe"]
    activity_dataframe = activity_result["activity_standardized_dataframe"]
    calendar_dataframe = activity_result["activity_calendar_dataframe"]
    benefits_dataframe = activity_result["promotion_benefits_dataframe"]

    full_result = run_full_analysis(
        sales_dataframe=sales_dataframe,
        main_activity_dataframe=activity_dataframe,
        calendar_dataframe=calendar_dataframe,
        benefits_dataframe=benefits_dataframe,
        settings=DEMO_ANALYSIS_SETTINGS,
    )

    unit_result = run_activity_unit_analysis(
        sales_dataframe=sales_dataframe,
        activity_standardized_dataframe=activity_dataframe,
        activity_calendar_dataframe=calendar_dataframe,
    )

    return {
        "integrated_sales_activity_dataframe": full_result.integrated_dataframe,
        "integration_issues_dataframe": full_result.integration_issues_dataframe,
        "activity_performance_dataframe": full_result.performance_dataframe,
        "strategy_report_dataframe": full_result.strategy_dataframe,
        "strategy_report_text": full_result.strategy_report_text,
        "activity_unit_timeline_dataframe": unit_result.unit_timeline,
        "activity_unit_timeline_wide_dataframe": unit_result.unit_timeline_wide,
        "activity_unit_price_dataframe": unit_result.unit_price_table,
        "activity_unit_overview_dataframe": unit_result.unit_overview,
        "activity_waterfall_pairing_dataframe": unit_result.waterfall_pairing_table,
        "activity_waterfall_summary_dataframe": unit_result.waterfall_summary,
        "activity_bundle_rules_dataframe": unit_result.bundle_rules,
        "activity_bundle_date_mismatch_dataframe": unit_result.bundle_date_mismatches,
    }


# =========================================================
# 對外取得示範資料結果（資料庫有快取就直接讀，
# 沒有就即時算一次並存回資料庫，下次就不用重算）
# =========================================================

def get_demo_sales_result() -> dict[str, object]:
    cached_result = _load_cached_result(SALES_RESULT_KEYS)

    if cached_result is not None:
        return cached_result

    computed_result = _compute_demo_sales_result()
    _save_result_to_cache(computed_result)

    return computed_result


def get_demo_activity_result() -> dict[str, object]:
    cached_result = _load_cached_result(ACTIVITY_RESULT_KEYS)

    if cached_result is not None:
        return cached_result

    computed_result = _compute_demo_activity_result()
    _save_result_to_cache(computed_result)

    return computed_result


def get_demo_analysis_result() -> dict[str, object]:
    cached_result = _load_cached_result(ANALYSIS_RESULT_KEYS)

    if cached_result is not None:
        return cached_result

    sales_result = get_demo_sales_result()
    activity_result = get_demo_activity_result()

    computed_result = _compute_demo_analysis_result(
        sales_result,
        activity_result,
    )
    _save_result_to_cache(computed_result)

    return computed_result


# =========================================================
# 套入 Session State
#
# 套入後跟真的走完上傳／欄位對應／確認流程的 session_state
# 長得一模一樣，下游頁面（執行完整分析、AI 策略中心……）
# 完全不用區分現在是示範資料還是使用者自己上傳的資料。
# =========================================================

def apply_demo_sales_data_to_session() -> None:
    result = get_demo_sales_result()

    st.session_state["standardized_dataframe"] = result[
        "standardized_dataframe"
    ]
    st.session_state["sales_data_confirmed"] = True
    st.session_state["is_demo_sales_data"] = True


def apply_demo_activity_data_to_session() -> None:
    result = get_demo_activity_result()

    for key in ACTIVITY_RESULT_KEYS:
        st.session_state[key] = result[key]

    st.session_state["activity_data_confirmed"] = True
    st.session_state["is_demo_activity_data"] = True


def apply_demo_analysis_to_session() -> None:
    result = get_demo_analysis_result()

    for key in ANALYSIS_RESULT_KEYS:
        st.session_state[key] = result[key]

    st.session_state["full_analysis_completed"] = True
    st.session_state["integration_completed"] = True
    st.session_state["performance_analysis_completed"] = True
    st.session_state["strategy_report_completed"] = True
    st.session_state["unit_analysis_completed"] = True


def apply_full_demo_data_to_session() -> None:
    """首頁「開始探索」使用：一次套入示範銷量、活動與分析結果。"""

    apply_demo_sales_data_to_session()
    apply_demo_activity_data_to_session()
    apply_demo_analysis_to_session()
