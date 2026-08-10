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

from src.demo_data import apply_demo_activity_data_to_session
from src.session_helpers import (
    clear_activity_data,
    get_activity_file_names,
    get_activity_sheet_names,
    initialize_session_state,
    remove_activity_file,
    save_activity_excel,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.markdown(
    """
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
# 資料來源選擇：示範資料／自訂上傳資料
#
# 邏輯同「01 銷量資料處理」：預設示範資料，一打開分頁就直接
# 看到已處理完成的畫面；切換成自訂上傳資料則恢復成尚未上傳的
# 空白畫面，且不會寫入資料庫。
# =========================================================

activity_data_mode = st.radio(
    "資料來源",
    options=["示範資料", "自訂上傳資料"],
    horizontal=True,
    key="activity_data_mode",
)

if activity_data_mode == "示範資料":
    apply_demo_activity_data_to_session()

    st.info(
        "目前顯示示範資料的處理結果。"
        "若要改用自己的資料，請切換至「自訂上傳資料」。"
    )

    demo_main_activity_dataframe = st.session_state[
        "activity_standardized_dataframe"
    ]
    demo_calendar_dataframe = st.session_state[
        "activity_calendar_dataframe"
    ]
    demo_benefits_dataframe = st.session_state[
        "promotion_benefits_dataframe"
    ]
    demo_activity_issues_dataframe = st.session_state[
        "activity_issues_dataframe"
    ]

    demo_activity_summary = create_activity_data_summary(
        activity_standardized_dataframe=demo_main_activity_dataframe,
        activity_calendar_dataframe=demo_calendar_dataframe,
        promotion_benefits_dataframe=demo_benefits_dataframe,
        activity_issues_dataframe=demo_activity_issues_dataframe,
    )

    demo_result_col1, demo_result_col2, demo_result_col3, demo_result_col4 = (
        st.columns(4)
    )

    demo_result_col1.metric(
        "商品活動期間",
        f"{demo_activity_summary['main_activity_rows']:,}",
    )
    demo_result_col2.metric(
        "活動日曆",
        f"{demo_activity_summary['calendar_rows']:,}",
    )
    demo_result_col3.metric(
        "優惠內容",
        f"{demo_activity_summary['benefit_rows']:,}",
    )
    demo_result_col4.metric(
        "待確認問題",
        f"{demo_activity_summary['issue_rows']:,}",
    )

    demo_tab1, demo_tab2, demo_tab3, demo_tab4 = st.tabs(
        ["商品活動價格", "活動日曆", "優惠內容", "資料問題"]
    )

    with demo_tab1:
        demo_non_empty_columns = [
            column
            for column in demo_main_activity_dataframe.columns
            if demo_main_activity_dataframe[column].notna().any()
        ]

        st.dataframe(
            demo_main_activity_dataframe[demo_non_empty_columns].head(100),
            use_container_width=True,
            hide_index=True,
            column_config=default_column_config(
                demo_main_activity_dataframe[demo_non_empty_columns].head(100)
            ),
        )

    with demo_tab2:
        if demo_calendar_dataframe is None or demo_calendar_dataframe.empty:
            st.info("沒有活動日曆資料。")
        else:
            st.dataframe(
                demo_calendar_dataframe.head(100),
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    demo_calendar_dataframe.head(100)
                ),
            )

    with demo_tab3:
        if demo_benefits_dataframe is None or demo_benefits_dataframe.empty:
            st.info("沒有優惠內容資料。")
        else:
            st.dataframe(
                demo_benefits_dataframe.head(100),
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    demo_benefits_dataframe.head(100)
                ),
            )

    with demo_tab4:
        if (
            demo_activity_issues_dataframe is None
            or demo_activity_issues_dataframe.empty
        ):
            st.success("目前程式未發現需要人工確認的問題。")
        else:
            st.dataframe(
                demo_activity_issues_dataframe.head(100),
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    demo_activity_issues_dataframe.head(100)
                ),
            )

    st.success(
        "示範活動資料已就緒，可以進入銷量與活動資料整合。"
    )

    st.stop()


# 切換回自訂上傳資料時，先清掉示範資料，恢復成尚未上傳的
# 空白畫面。
if st.session_state.get("is_demo_activity_data"):
    clear_activity_data()
    st.session_state["is_demo_activity_data"] = False


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

    例如：
    3月活動.xlsx
    三月活動.xlsx
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
# Step 1：上傳活動 Excel
# =========================================================

st.subheader("1. 上傳活動 Excel")

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
        "目前尚未上傳活動 Excel。"
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


# =========================================================
# 檢查已處理結果是否仍符合目前檔案
# =========================================================

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


# =========================================================
# 取得活動處理結果
# =========================================================

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


    # =====================================================
    # 分頁顯示結果
    # =====================================================

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

        # 新模板／舊格式各自專屬的欄位，另一種格式一律補
        # 空值，顯示前動態濾掉「這批資料」完全沒有內容的
        # 欄位，兩種格式都能正確適應（不寫死欄位名稱清單）。
        non_empty_columns = [
            column
            for column in main_activity_dataframe.columns
            if main_activity_dataframe[column].notna().any()
        ]

        # 品類欄位習慣上緊接在商品編號、商品名稱之後。
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
            # 商品專屬優惠（如指定商品贈品）才會有 product_id／
            # product_name，全站或品牌活動的優惠這兩欄永遠是空
            # 值；比照「商品活動價格」表，顯示前動態濾掉這批
            # 資料完全沒有內容的欄位，兩種情況都能正確適應。
            # product_name 等文字欄位在無資料時預設是空字串而非
            # NaN，先轉成字串、去除頭尾空白、把空字串當缺值，
            # 才能正確判斷「整欄皆空」。
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


    # =====================================================
    # 下載標準化結果
    # =====================================================

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


    # =====================================================
    # 最終確認
    # =====================================================

    st.divider()
    st.subheader("最終確認")

    if result_is_current:
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


# =========================================================
# 清除活動資料
# =========================================================

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