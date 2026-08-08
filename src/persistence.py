from __future__ import annotations

import pickle
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


# =========================================================
# SQLite 當 key-value blob store
#
# 不用關聯式 schema：每個要保存的 session_state 值直接
# pickle 存成 BLOB，讀回來 unpickle，型別／index 100% 原樣
# 還原，不用管 DataFrame 裡有 datetime64／bool／混合型欄位，
# 也不會因為以後新增分析欄位就要改資料庫 schema。符合這是
# 小規模分析雛形、資料庫不用大也不用複雜的前提。
# =========================================================

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app_state.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_state (
            state_key TEXT PRIMARY KEY,
            value_blob BLOB NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    return connection


def save_state(key: str, value: Any) -> None:
    """把單一 session_state 值序列化存進資料庫（沒有就新增，有就覆蓋）。"""

    value_blob = pickle.dumps(value)
    updated_at = datetime.now(timezone.utc).isoformat()

    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO app_state (state_key, value_blob, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(state_key) DO UPDATE SET
                value_blob = excluded.value_blob,
                updated_at = excluded.updated_at
            """,
            (key, value_blob, updated_at),
        )


def load_state(key: str) -> Any | None:
    """讀回單一 key 的值；資料庫裡沒有就回傳 None。"""

    with _get_connection() as connection:
        row = connection.execute(
            "SELECT value_blob FROM app_state WHERE state_key = ?",
            (key,),
        ).fetchone()

    if row is None:
        return None

    return pickle.loads(row[0])


def delete_state(key: str) -> None:
    """刪除資料庫裡的單一 key（目前沒有任何流程會呼叫，保留給未來用）。"""

    with _get_connection() as connection:
        connection.execute(
            "DELETE FROM app_state WHERE state_key = ?",
            (key,),
        )


# =========================================================
# 三組領域快照：銷量／活動／分析結果
# =========================================================

SALES_SNAPSHOT_KEYS = [
    "uploaded_file_name",
    "uploaded_file_bytes",
    "excel_sheet_names",
    "selected_sheet_name",
    "column_mapping",
    "standardized_dataframe",
    "sales_data_confirmed",
]

ACTIVITY_SNAPSHOT_KEYS = [
    "activity_uploaded_files",
    "activity_sheet_names",
    "processed_march_activity_file_name",
    "processed_april_activity_file_name",
    "activity_standardized_dataframe",
    "activity_calendar_dataframe",
    "promotion_benefits_dataframe",
    "activity_issues_dataframe",
    "main_activity_summary_dataframe",
    "other_activity_summary_dataframe",
    "activity_data_confirmed",
]

ANALYSIS_SNAPSHOT_KEYS = [
    "integrated_sales_activity_dataframe",
    "integration_issues_dataframe",
    "activity_performance_dataframe",
    "strategy_report_dataframe",
    "strategy_report_text",
    "unit_analysis_completed",
    "activity_unit_timeline_dataframe",
    "activity_unit_timeline_wide_dataframe",
    "activity_unit_price_dataframe",
    "activity_unit_overview_dataframe",
    "activity_waterfall_pairing_dataframe",
    "activity_waterfall_summary_dataframe",
    "activity_bundle_rules_dataframe",
    "activity_bundle_date_mismatch_dataframe",
    "full_analysis_completed",
    "integration_completed",
    "performance_analysis_completed",
    "strategy_report_completed",
]


def _save_snapshot(keys: list[str]) -> None:
    for key in keys:
        if key in st.session_state:
            save_state(key, st.session_state[key])


def _load_snapshot_into_session(keys: list[str]) -> bool:
    """
    把資料庫裡的快照寫回 session_state。

    回傳是否真的有找到任何資料（用來判斷資料庫是不是空的，
    第一次使用系統時不需要顯示任何「已還原」提示）。
    """

    found_any = False

    for key in keys:
        value = load_state(key)

        if value is not None:
            st.session_state[key] = value
            found_any = True

    return found_any


def save_sales_snapshot() -> None:
    _save_snapshot(SALES_SNAPSHOT_KEYS)


def load_sales_snapshot_into_session() -> bool:
    return _load_snapshot_into_session(SALES_SNAPSHOT_KEYS)


def save_activity_snapshot() -> None:
    _save_snapshot(ACTIVITY_SNAPSHOT_KEYS)


def load_activity_snapshot_into_session() -> bool:
    return _load_snapshot_into_session(ACTIVITY_SNAPSHOT_KEYS)


def save_analysis_snapshot() -> None:
    _save_snapshot(ANALYSIS_SNAPSHOT_KEYS)


def load_analysis_snapshot_into_session() -> bool:
    return _load_snapshot_into_session(ANALYSIS_SNAPSHOT_KEYS)


def _dataframe_ready(value: Any) -> bool:
    return isinstance(value, pd.DataFrame) and not value.empty


def bootstrap_session_from_db() -> None:
    """
    App 啟動時（每個瀏覽器 session 只執行一次）嘗試從資料庫
    回填分析結果快照，只在對應 session_state 欄位還是預設空值
    時才寫入，不會覆蓋使用者在這個 session 裡已經做的操作。

    刻意不回填銷量／活動這兩組「上傳」快照：01/02 兩個資料
    處理分頁、側邊欄進度與「開始使用」頁面都必須在每個新
    session 一開始就是「尚未上傳」的空白狀態，逼使用者重新
    走一次上傳流程才會顯示成「已完成」；只有分析結果（第三
    步「執行完整分析」與之後的成果頁面）才延續資料庫裡的
    舊資料，讓使用者不用重新上傳就能看到上次的分析結果。
    """

    if not _dataframe_ready(
        st.session_state.get("activity_unit_overview_dataframe")
    ):
        load_analysis_snapshot_into_session()


def clear_analysis_snapshot() -> None:
    """
    刪除資料庫中的分析結果快照。

    銷量或活動資料被「覆蓋」後，資料庫裡先前存的分析結果是
    用已經不存在的舊資料算出來的，必須一併清掉，「執行完整
    分析」頁面才會恢復成「尚未執行」的初始狀態，逼使用者用
    新資料重新跑一次分析。
    """

    for key in ANALYSIS_SNAPSHOT_KEYS:
        delete_state(key)


# =========================================================
# DataFrame 差異比對
# =========================================================

def _hash_row(row: tuple) -> Any:
    """
    把一列資料轉成可比較的形式：NaN／NaT 全部視為同一個值
    （否則 NaN != NaN，同一列只要有缺值就永遠判定為不同）。
    """

    return tuple(
        None if (isinstance(value, float) and pd.isna(value)) or value is pd.NaT
        else value
        for value in row
    )


def diff_dataframes(
    old_dataframe: pd.DataFrame | None,
    new_dataframe: pd.DataFrame,
) -> dict[str, Any]:
    """
    比較新舊 DataFrame，回傳差異摘要。

    用「整列內容」當比對單位，不假設有業務上的主鍵欄位——
    小規模雛形不需要做到欄位級別的異動追蹤，只需要讓使用者
    知道「有沒有東西不一樣、大概差多少」。
    """

    if not _dataframe_ready(old_dataframe):
        return {
            "has_old_data": False,
            "identical": False,
            "old_row_count": 0,
            "new_row_count": len(new_dataframe),
            "differing_row_count": 0,
        }

    old_row_set = {
        _hash_row(row) for row in old_dataframe.itertuples(index=False, name=None)
    }
    new_row_set = {
        _hash_row(row) for row in new_dataframe.itertuples(index=False, name=None)
    }

    differing_rows = old_row_set.symmetric_difference(new_row_set)

    return {
        "has_old_data": True,
        "identical": len(differing_rows) == 0,
        "old_row_count": len(old_dataframe),
        "new_row_count": len(new_dataframe),
        "differing_row_count": len(differing_rows),
    }
