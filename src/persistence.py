from __future__ import annotations

import os
import pickle
from datetime import datetime, timezone
from typing import Any

import psycopg2
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


# =========================================================
# Supabase (Postgres) 當 key-value blob store
#
# 不用關聯式 schema：每個要保存的值直接 pickle 存成 BYTEA，
# 讀回來 unpickle，型別／index 100% 原樣還原，不用管 DataFrame
# 裡有 datetime64／bool／混合型欄位，也不會因為以後新增分析
# 欄位就要改資料庫 schema。符合這是小規模分析雛形、資料庫不用
# 大也不用複雜的前提。
#
# 這裡沒有任何 session／使用者隔離：所有 key 都是全站共用。這
# 個限制目前只給示範資料（src/demo_data.py）使用——示範資料
# 本來就該是全站共用同一份，才適合放進這種「無隔離」的全域
# key-value store。使用者自訂上傳的資料完全不會呼叫這裡的
# save_state，只留在 st.session_state，重新整理瀏覽器就會清空，
# 這樣才不會被其他使用者的上傳互相覆蓋。
# =========================================================


def _get_database_url() -> str:
    """
    取得 Supabase Postgres 連線字串。

    優先順序：
    1. Streamlit Cloud Secrets（DATABASE_URL）
    2. 本機 .env 環境變數（DATABASE_URL）
    """

    secret_database_url = ""

    try:
        secret_database_url = str(
            st.secrets.get(
                "DATABASE_URL",
                "",
            )
        ).strip()

    except Exception:
        # 本機沒有 secrets.toml 時可能會發生例外，
        # 此時改從 .env 讀取即可。
        secret_database_url = ""

    environment_database_url = str(
        os.getenv(
            "DATABASE_URL",
            "",
        )
    ).strip()

    database_url = (
        secret_database_url
        or environment_database_url
    )

    if not database_url:
        raise RuntimeError(
            "找不到 DATABASE_URL，請在 Streamlit Cloud secrets 或本機 .env "
            "設定 Supabase 的 Postgres 連線字串。"
        )

    return database_url


def _get_connection() -> psycopg2.extensions.connection:
    connection = psycopg2.connect(_get_database_url())

    with connection, connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                state_key TEXT PRIMARY KEY,
                value_blob BYTEA NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

    return connection


def save_state(key: str, value: Any) -> None:
    """把單一值序列化存進資料庫（沒有就新增，有就覆蓋）。"""

    value_blob = pickle.dumps(value)
    updated_at = datetime.now(timezone.utc).isoformat()

    connection = _get_connection()

    try:
        with connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_state (state_key, value_blob, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (state_key) DO UPDATE SET
                    value_blob = EXCLUDED.value_blob,
                    updated_at = EXCLUDED.updated_at
                """,
                (key, psycopg2.Binary(value_blob), updated_at),
            )
    finally:
        connection.close()


def load_state(key: str) -> Any | None:
    """讀回單一 key 的值；資料庫裡沒有就回傳 None。"""

    connection = _get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT value_blob FROM app_state WHERE state_key = %s",
                (key,),
            )
            row = cursor.fetchone()
    finally:
        connection.close()

    if row is None:
        return None

    return pickle.loads(bytes(row[0]))


def delete_state(key: str) -> None:
    """刪除資料庫裡的單一 key。"""

    connection = _get_connection()

    try:
        with connection, connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM app_state WHERE state_key = %s",
                (key,),
            )
    finally:
        connection.close()
