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

from src.activity_processing import (
    create_activity_data_summary,
    process_activity_files,
)
from src.column_labels import default_column_config

from src.persistence import (
    clear_analysis_snapshot,
    diff_dataframes,
    load_activity_snapshot_into_session,
    load_state,
    save_activity_snapshot,
)
from src.session_helpers import (
    clear_activity_data,
    clear_downstream_analysis,
    get_activity_file_names,
    get_activity_sheet_names,
    initialize_session_state,
    remove_activity_file,
    save_activity_excel,
)


# =========================================================
# 頁面初始化與全域字體放大 CSS
# =========================================================

initialize_session_state()

st.markdown(
    """
    <style>
        /* 全域文字放大 */
        html, body, [class*="css"] {
            font-size: 18px !important;
        }
        .product-page-title h1 {
            font-size: 32px !important;
            font-weight: 900 !important;
        }
        .product-page-description {
            font-size: 18px !important;
        }
    </style>
    <div class="step-label">STEP 02</div>
    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>活動資料處理</h1>
    </div>
    <p class="product-page-description">
        一次上傳 3 月與 4 月活動 Excel，確認月份對應後，
        系統會自動解析商品活動期間、活動價格、活動日曆、
        優惠內容與需要人工確認的資料問題。
    </p>
    """,
    unsafe_allow_html=True,
)

st.info(
    "目前系統依照 3 月與 4 月活動表格式進行處理。"
)


# =========================================================
# 小工具函式
# =========================================================

def find_month_candidate(
    file_names: list[str],
    month_number: int,
    month_text: str,
) -> str | None:
    """
    根據檔名尋找月份候選檔案。
    """
    for file_name in file_names:
        if (
            f"{month_number}月" in file_name
            or month_text in file_name
        ):
            return file_name

    return None


def get_default_index(
    options: list[str],
    selected_value: str | None,
) -> int:
    """
    取得 selectbox 的預設位置。
    """
    if selected_value in options:
        return options.index(
            selected_value
        )

    return 0


def reset_activity_widget_state() -> None:
    """
    清除活動頁面上的月份選擇與最終確認元件狀態。
    """
    widget_keys = [
        "march_activity_file_select",
        "april_activity_file_select",
        "activity_final_confirmation_checkbox",
    ]

    for key in widget_keys:
        st.session_state.pop(
            key,
            None,
        )


# =========================================================
# 資料來源模式選擇（預設使用示範資料，免手動上傳）
# =========================================================

st.subheader("1. 選擇資料來源")

data_source_mode = st.radio(
    "活動資料來源模式",
    ["使用系統示範資料 (推薦，免手動上傳)", "自行上傳 Excel 檔案"],
    key="activity_data_source_mode",
    horizontal=True,
    help="選擇「使用系統示範資料」將自動載入 3 月與 4 月品牌活動範本，直接呈現處理完成狀態。",
)

is_demo_mode = "使用系統示範資料" in data_source_mode

if is_demo_mode:
    march_demo_path = PROJECT_ROOT / "3月品牌活動_模板.xlsx"
    april_demo_path = PROJECT_ROOT / "4月品牌活動_模板.xlsx"

    if march_demo_path.exists() and april_demo_path.exists():
        if "3月品牌活動_模板.xlsx" not in st.session_state.get("activity_uploaded_files", {}) or st.session_state.get("activity_standardized_dataframe") is None:
            try:
                march_bytes = march_demo_path.read_bytes()
                april_bytes = april_demo_path.read_bytes()

                save_activity_excel("3月品牌活動_模板.xlsx", march_bytes)
                save_activity_excel("4月品牌活動_模板.xlsx", april_bytes)

                processing_results = process_activity_files(
                    march_file_bytes=march_bytes,
                    april_file_bytes=april_bytes,
                )

                for key, dataframe in processing_results.items():
                    st.session_state[key] = dataframe

                st.session_state["processed_march_activity_file_name"] = "3月品牌活動_模板.xlsx"
                st.session_state["processed_april_activity_file_name"] = "4月品牌活動_模板.xlsx"
                st.session_state.activity_data_confirmed = True
                save_activity_snapshot()
            except Exception as error:
                st.error(f"自動載入活動示範資料失敗：{error}")

    st.success("✅ 已成功載入 3 月與 4 月品牌活動範本，活動期間、價格、日曆與優惠內容已自動解析完成！")


# =========================================================
# Step 1（若選擇自行上傳）：上傳活動 Excel
# =========================================================

if not is_demo_mode:
    st.subheader("2. 上傳活動 Excel")

    with st.container(border=True):
        st.markdown(
            """
            <div class="upload-card-heading">
                <div class="upload-card-icon">🏷️</div>
                <div>
                    <div class="upload-card-title">活動資料匯入</div>
                    <div class="upload-card-description">
                        可一次選擇多份 Excel。請至少上傳 3 月與 4 月活動檔案，
                        系統會根據檔名建議月份，之後仍可手動調整。
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_files = st.file_uploader(
            "可一次選擇多份 Excel",
            type=["xlsx"],
            accept_multiple_files=True,
            key="activity_excel_uploader",
            help="目前請至少上傳 3 月及 4 月活動檔案。",
        )

    if uploaded_files:
        successful_files: list[str] = []
        failed_files: list[dict[str, str]] = []

        for uploaded_file in uploaded_files:
            file_bytes = uploaded_file.getvalue()

            existing_files = (
                st.session_state.activity_uploaded_files
            )

            is_new_or_changed = (
                uploaded_file.name not in existing_files
                or existing_files[
                    uploaded_file.name
                ] != file_bytes
            )

            if not is_new_or_changed:
                continue

            try:
                with st.spinner(
                    f"正在讀取：{uploaded_file.name}……"
                ):
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
            reset_activity_widget_state()

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
# 取得已上傳活動檔案
# =========================================================

activity_file_names = (
    get_activity_file_names()
)

if not activity_file_names:
    st.warning(
        "目前尚未上傳活動 Excel，或請切換為「使用系統示範資料」。"
    )
    st.stop()


# =========================================================
# 已上傳檔案摘要
# =========================================================

st.subheader("已上傳的活動檔案")

file_summary_rows = []

for file_name in activity_file_names:
    sheet_names = get_activity_sheet_names(
        file_name
    )

    file_bytes = (
        st.session_state.activity_uploaded_files[
            file_name
        ]
    )

    file_size_mb = (
        len(file_bytes)
        / 1024
        / 1024
    )

    file_summary_rows.append(
        {
            "檔案名稱": file_name,
            "檔案大小": f"{file_size_mb:.2f} MB",
            "工作表數量": len(sheet_names),
            "工作表": "、".join(sheet_names),
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
# 移除單一活動檔案
# =========================================================

with st.expander(
    "管理已上傳檔案",
    expanded=False,
):
    file_to_remove = st.selectbox(
        "選擇要移除的檔案",
        options=activity_file_names,
        key="activity_file_remove_select",
    )

    if st.button(
        "移除選取檔案",
        key="remove_activity_file_button",
    ):
        remove_activity_file(
            file_to_remove
        )

        reset_activity_widget_state()

        st.success(
            f"已移除：{file_to_remove}"
        )

        st.rerun()


# =========================================================
# Step 2：確認月份檔案
# =========================================================

st.divider()
st.subheader("2. 確認月份檔案")

st.caption(
    "系統會根據檔名自動判斷月份。"
    "若判斷不正確，再使用下拉選單修改。"
)


march_candidate = find_month_candidate(
    file_names=activity_file_names,
    month_number=3,
    month_text="三月",
)

april_candidate = find_month_candidate(
    file_names=activity_file_names,
    month_number=4,
    month_text="四月",
)


march_default_index = get_default_index(
    activity_file_names,
    march_candidate,
)

april_default_index = get_default_index(
    activity_file_names,
    april_candidate,
)


month_col1, month_col2 = st.columns(2)

with month_col1:
    march_file_name = st.selectbox(
        "3 月活動檔案",
        options=activity_file_names,
        index=march_default_index,
        key="march_activity_file_select",
    )

with month_col2:
    april_file_name = st.selectbox(
        "4 月活動檔案",
        options=activity_file_names,
        index=april_default_index,
        key="april_activity_file_select",
    )


same_file_selected = (
    march_file_name
    == april_file_name
)

if same_file_selected:
    st.error(
        "3 月與 4 月不可選擇同一份檔案。"
    )


month_mapping_dataframe = pd.DataFrame(
    [
        {
            "月份": "3 月",
            "使用檔案": march_file_name,
            "系統自動辨識": (
                "是"
                if march_file_name
                == march_candidate
                else "已手動調整"
            ),
        },
        {
            "月份": "4 月",
            "使用檔案": april_file_name,
            "系統自動辨識": (
                "是"
                if april_file_name
                == april_candidate
                else "已手動調整"
            ),
        },
    ]
)

st.dataframe(
    month_mapping_dataframe,
    use_container_width=True,
    hide_index=True,
)


saved_march_file_name = (
    st.session_state.get(
        "processed_march_activity_file_name"
    )
)

saved_april_file_name = (
    st.session_state.get(
        "processed_april_activity_file_name"
    )
)

activity_result_exists = (
    st.session_state.get(
        "activity_standardized_dataframe"
    )
    is not None
)

file_selection_has_changed = (
    activity_result_exists
    and (
        saved_march_file_name
        != march_file_name
        or saved_april_file_name
        != april_file_name
    )
)

if file_selection_has_changed:
    st.warning(
        "目前月份檔案選擇已變更。"
        "請重新執行活動資料處理，"
        "才能更新標準化結果。"
    )


# =========================================================
# Step 3：執行活動資料處理
# =========================================================

st.divider()
st.subheader("3. 處理活動資料")

st.write(
    "按下按鈕後，系統會自動完成："
)

st.markdown(
    """
- 解析商品活動期間與活動價格
- 展開活動開始及結束日期
- 整理活動日曆
- 整理鋪底、折價券、贈品與包套活動
- 整理品牌日及品牌週
- 建立資料問題清單
"""
)


process_button = st.button(
    "確認檔案並處理活動資料",
    type="primary",
    use_container_width=True,
    disabled=same_file_selected,
)


if process_button:
    try:
        activity_files = (
            st.session_state.activity_uploaded_files
        )

        march_file_bytes = activity_files.get(
            march_file_name
        )

        april_file_bytes = activity_files.get(
            april_file_name
        )

        with st.spinner(
            "正在解析活動日期、價格與優惠內容……"
        ):
            processing_results = (
                process_activity_files(
                    march_file_bytes=(
                        march_file_bytes
                    ),
                    april_file_bytes=(
                        april_file_bytes
                    ),
                )
            )

        for key, dataframe in (
            processing_results.items()
        ):
            st.session_state[key] = dataframe

        st.session_state[
            "processed_march_activity_file_name"
        ] = march_file_name

        st.session_state[
            "processed_april_activity_file_name"
        ] = april_file_name

        st.session_state.activity_data_confirmed = (
            False
        )

        st.session_state[
            "activity_final_confirmation_checkbox"
        ] = False

        file_selection_has_changed = False

        st.success(
            "活動資料標準化與品質檢查完成。"
        )

    except Exception as error:
        st.error(
            f"活動資料處理失敗：{error}"
        )


main_activity_dataframe = (
    st.session_state.get(
        "activity_standardized_dataframe"
    )
)

calendar_dataframe = (
    st.session_state.get(
        "activity_calendar_dataframe"
    )
)

benefits_dataframe = (
    st.session_state.get(
        "promotion_benefits_dataframe"
    )
)

activity_issues_dataframe = (
    st.session_state.get(
        "activity_issues_dataframe"
    )
)


if main_activity_dataframe is None:
    st.info(
        "確認月份檔案後，"
        "按下「確認檔案並處理活動資料」，"
        "即可產生活動標準化結果。"
    )

else:
    result_is_current = (
        saved_march_file_name
        == march_file_name
        and saved_april_file_name
        == april_file_name
    )

    if process_button:
        result_is_current = True

    if not result_is_current:
        st.warning(
            "下方結果是先前月份檔案產生的資料。"
            "請重新執行活動資料處理後再確認。"
        )

    # =====================================================
    # Step 4：活動資料結果
    # =====================================================

    st.divider()
    st.subheader("4. 標準化結果與最終確認")

    try:
        activity_summary = (
            create_activity_data_summary(
                activity_standardized_dataframe=(
                    main_activity_dataframe
                ),
                activity_calendar_dataframe=(
                    calendar_dataframe
                ),
                promotion_benefits_dataframe=(
                    benefits_dataframe
                ),
                activity_issues_dataframe=(
                    activity_issues_dataframe
                ),
            )
        )

    except Exception as error:
        st.error(
            f"無法建立活動資料摘要：{error}"
        )
        st.stop()


    result_col1, result_col2, result_col3, result_col4 = (
        st.columns(4)
    )

    result_col1.metric(
        "商品活動期間",
        f"{activity_summary['main_activity_rows']:,}",
    )

    result_col2.metric(
        "活動日曆",
        f"{activity_summary['calendar_rows']:,}",
    )

    result_col3.metric(
        "優惠內容",
        f"{activity_summary['benefit_rows']:,}",
    )

    result_col4.metric(
        "待確認問題",
        f"{activity_summary['issue_rows']:,}",
    )


    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "商品活動價格",
            "活動日曆",
            "優惠內容",
            "資料問題",
        ]
    )


    with tab1:
        st.subheader(
            "商品活動價格資料"
        )

        st.caption(
            "同一商品可能有多個活動期間與活動價格。"
        )

        non_empty_columns = [
            column
            for column in main_activity_dataframe.columns
            if main_activity_dataframe[column].notna().any()
        ]

        ordered_columns = list(non_empty_columns)

        if {
            "product_id",
            "product_name",
            "product_category",
        }.issubset(ordered_columns):
            ordered_columns.remove("product_category")
            insert_at = ordered_columns.index("product_name")
            ordered_columns.insert(insert_at, "product_category")

        main_activity_preview = (
            main_activity_dataframe[ordered_columns].head(100)
        )

        st.dataframe(
            main_activity_preview,
            use_container_width=True,
            hide_index=True,
            column_config=default_column_config(
                main_activity_preview
            ),
        )

        if len(main_activity_dataframe) > 100:
            st.caption(
                "目前僅預覽前 100 筆資料。"
            )


    with tab2:
        st.subheader(
            "活動日曆"
        )

        if (
            calendar_dataframe is None
            or calendar_dataframe.empty
        ):
            st.info(
                "沒有活動日曆資料。"
            )

        else:
            calendar_preview = (
                calendar_dataframe.head(100)
            )

            st.dataframe(
                calendar_preview,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    calendar_preview
                ),
            )

            if len(calendar_dataframe) > 100:
                st.caption(
                    "目前僅預覽前 100 筆資料。"
                )


    with tab3:
        st.subheader(
            "優惠內容"
        )

        if (
            benefits_dataframe is None
            or benefits_dataframe.empty
        ):
            st.info(
                "沒有優惠內容資料。"
            )

        else:
            non_empty_benefit_columns = [
                column
                for column in benefits_dataframe.columns
                if benefits_dataframe[column]
                .astype("string")
                .str.strip()
                .replace("", pd.NA)
                .notna()
                .any()
            ]

            benefits_preview = (
                benefits_dataframe[non_empty_benefit_columns]
                .head(100)
            )

            st.dataframe(
                benefits_preview,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    benefits_preview
                ),
            )

            if len(benefits_dataframe) > 100:
                st.caption(
                    "目前僅預覽前 100 筆資料。"
                )


    with tab4:
        st.subheader(
            "資料問題"
        )

        if (
            activity_issues_dataframe is None
            or activity_issues_dataframe.empty
        ):
            st.success(
                "目前程式未發現需要人工確認的問題。"
            )

        else:
            st.warning(
                "以下資料不會被系統自行修改，"
                "需由使用者或企業確認。"
            )

            activity_issues_preview = (
                activity_issues_dataframe.head(100)
            )

            st.dataframe(
                activity_issues_preview,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    activity_issues_preview
                ),
            )

            if len(activity_issues_dataframe) > 100:
                st.caption(
                    "目前僅預覽前 100 筆問題資料。"
                )


    st.divider()
    st.subheader("下載標準化資料")


    main_activity_csv = (
        main_activity_dataframe.to_csv(
            index=False,
            encoding="utf-8-sig",
            date_format="%Y-%m-%d",
        ).encode(
            "utf-8-sig"
        )
    )


    if calendar_dataframe is None:
        calendar_for_download = pd.DataFrame()

    else:
        calendar_for_download = (
            calendar_dataframe
        )


    calendar_csv = (
        calendar_for_download.to_csv(
            index=False,
            encoding="utf-8-sig",
            date_format="%Y-%m-%d",
        ).encode(
            "utf-8-sig"
        )
    )


    if benefits_dataframe is None:
        benefits_for_download = pd.DataFrame()

    else:
        benefits_for_download = (
            benefits_dataframe
        )


    benefits_csv = (
        benefits_for_download.to_csv(
            index=False,
            encoding="utf-8-sig",
            date_format="%Y-%m-%d",
        ).encode(
            "utf-8-sig"
        )
    )


    if activity_issues_dataframe is None:
        issues_for_download = pd.DataFrame()

    else:
        issues_for_download = (
            activity_issues_dataframe
        )


    issues_csv = (
        issues_for_download.to_csv(
            index=False,
            encoding="utf-8-sig",
        ).encode(
            "utf-8-sig"
        )
    )


    download_col1, download_col2 = (
        st.columns(2)
    )

    with download_col1:
        st.download_button(
            "下載商品活動價格",
            data=main_activity_csv,
            file_name=(
                "activity_main_standardized.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

        st.download_button(
            "下載優惠內容",
            data=benefits_csv,
            file_name=(
                "promotion_benefits_standardized.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )


    with download_col2:
        st.download_button(
            "下載活動日曆",
            data=calendar_csv,
            file_name=(
                "campaign_calendar_standardized.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

        st.download_button(
            "下載活動資料問題",
            data=issues_csv,
            file_name=(
                "activity_quality_issues.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )


    st.divider()
    st.subheader("最終確認")

    if result_is_current:
        old_activity_dataframe = load_state(
            "activity_standardized_dataframe"
        )

        activity_diff_result = diff_dataframes(
            old_activity_dataframe,
            main_activity_dataframe,
        )

        if activity_diff_result["has_old_data"]:
            if activity_diff_result["identical"]:
                st.info(
                    "這份資料跟資料庫中的舊資料完全相同，不需要覆蓋。"
                )
            else:
                st.warning(
                    f"偵測到資料異動：資料庫中舊資料"
                    f"{activity_diff_result['old_row_count']} 筆，"
                    f"本次上傳{activity_diff_result['new_row_count']} 筆，"
                    f"其中{activity_diff_result['differing_row_count']} 筆內容不同。"
                    "請選擇要覆蓋還是保留舊資料。"
                )

                overwrite_col, keep_col = st.columns(2)

                if overwrite_col.button(
                    "覆蓋舊資料，使用本次上傳",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.activity_data_confirmed = (
                        True
                    )

                    save_activity_snapshot()

                    clear_downstream_analysis()
                    clear_analysis_snapshot()

                    st.success(
                        "已覆蓋資料庫中的舊資料，"
                        "活動資料已完成最終確認。"
                    )

                    st.rerun()

                if keep_col.button(
                    "保留舊資料，捨棄本次上傳",
                    use_container_width=True,
                ):
                    load_activity_snapshot_into_session()

                    st.success(
                        "已保留資料庫中的舊資料，本次上傳已捨棄。"
                    )

                    st.rerun()

                st.stop()

        confirmed_checkbox = st.checkbox(
            "我已確認月份檔案、標準化結果與問題資料",
            value=st.session_state.get(
                "activity_data_confirmed",
                False,
            ),
            key=(
                "activity_final_confirmation_checkbox"
            ),
        )

        confirm_button = st.button(
            "確認使用此活動資料",
            type="primary",
            use_container_width=True,
            disabled=not confirmed_checkbox,
        )

        if confirm_button:
            st.session_state.activity_data_confirmed = (
                True
            )

            save_activity_snapshot()

            st.success(
                "活動資料已完成最終確認，"
                "可以進入銷量與活動資料整合。"
            )

    else:
        st.info(
            "請先使用目前月份檔案重新處理資料，"
            "才能進行最終確認。"
        )


    if st.session_state.get(
        "activity_data_confirmed",
        False,
    ):
        st.success(
            "目前活動標準化資料已確認完成。"
        )


st.divider()
st.subheader("重新開始")

st.caption(
    "清除後會移除目前活動檔案、標準化結果，"
    "以及依賴活動資料的整合與分析結果。"
)

if st.button(
    "清除所有活動資料"
):
    clear_activity_data()

    reset_activity_widget_state()

    st.rerun()
