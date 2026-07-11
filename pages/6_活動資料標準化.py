from pathlib import Path
import sys
import tempfile

import pandas as pd
import streamlit as st


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.session_helpers import initialize_session_state

from src.clean_activities import (
    create_quality_summary as create_main_activity_summary,
    explode_promotion_periods,
    load_activity_sheet,
    prepare_activity_dataframe,
)

from src.clean_other_activities import (
    create_summary as create_other_activity_summary,
    parse_april_vacuum_coupons,
    parse_base_promotion_sheet,
    parse_brand_day_summary,
    parse_march_product_gifts,
    parse_package_sheet,
    parse_schedule_sheet,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.title("活動資料標準化")

st.write(
    "本頁會使用已上傳的 3 月與 4 月活動 Excel，"
    "產生商品活動價格、活動日曆、優惠內容及資料問題。"
)

st.info(
    "部分空白是活動表排版造成的正常現象，"
    "系統只會標記真正無法解析或缺少必要資訊的資料。"
)


# =========================================================
# 取得已上傳活動檔案
# =========================================================

activity_files = st.session_state.get(
    "activity_uploaded_files",
    {},
)

if not activity_files:
    st.warning(
        "尚未上傳活動 Excel。"
        "請先到「活動資料上傳」頁完成上傳。"
    )
    st.stop()


activity_file_names = sorted(
    activity_files.keys()
)


# =========================================================
# 自動辨識 3 月與 4 月檔案
# =========================================================

march_candidates = [
    file_name
    for file_name in activity_file_names
    if "3月" in file_name
    or "三月" in file_name
]

april_candidates = [
    file_name
    for file_name in activity_file_names
    if "4月" in file_name
    or "四月" in file_name
]


st.subheader("確認月份檔案")


march_default_index = 0

if march_candidates:
    march_default_index = (
        activity_file_names.index(
            march_candidates[0]
        )
    )


march_file_name = st.selectbox(
    "3 月活動檔案",
    options=activity_file_names,
    index=march_default_index,
    key="march_activity_file_select",
)


april_default_index = 0

if april_candidates:
    april_default_index = (
        activity_file_names.index(
            april_candidates[0]
        )
    )


april_file_name = st.selectbox(
    "4 月活動檔案",
    options=activity_file_names,
    index=april_default_index,
    key="april_activity_file_select",
)


if march_file_name == april_file_name:
    st.error(
        "3 月與 4 月不可選擇同一份檔案。"
    )
    st.stop()


st.caption(
    f"3 月：{march_file_name}　｜　"
    f"4 月：{april_file_name}"
)


# =========================================================
# 主活動表標準化
# =========================================================

def standardize_main_activities(
    march_path: Path,
    april_path: Path,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    整理兩個月份的主要活動表。
    """

    march_raw = load_activity_sheet(
        march_path,
        source_month=3,
    )

    april_raw = load_activity_sheet(
        april_path,
        source_month=4,
    )

    march_prepared = prepare_activity_dataframe(
        march_raw
    )

    april_prepared = prepare_activity_dataframe(
        april_raw
    )

    prepared_dataframe = pd.concat(
        [
            march_prepared,
            april_prepared,
        ],
        ignore_index=True,
    )

    (
        activity_dataframe,
        issues_dataframe,
    ) = explode_promotion_periods(
        prepared_dataframe
    )

    summary_dataframe = (
        create_main_activity_summary(
            prepared_dataframe,
            activity_dataframe,
            issues_dataframe,
        )
    )

    return (
        activity_dataframe,
        issues_dataframe,
        summary_dataframe,
    )


# =========================================================
# 其他活動標準化
# =========================================================

def standardize_other_activities(
    march_path: Path,
    april_path: Path,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    整理檔期、鋪底、平台幣、滿額贈、
    折價券、品牌日及包套。
    """

    calendar_records = []
    benefit_records = []
    issue_records = []

    # 3 月檔期
    records, issues = parse_schedule_sheet(
        march_path,
        source_month=3,
    )

    calendar_records.extend(records)
    issue_records.extend(issues)

    # 4 月檔期
    records, issues = parse_schedule_sheet(
        april_path,
        source_month=4,
    )

    calendar_records.extend(records)
    issue_records.extend(issues)

    # 3 月鋪底
    (
        records,
        benefits,
        issues,
    ) = parse_base_promotion_sheet(
        march_path,
        "三月鋪底",
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # 4 月鋪底
    (
        records,
        benefits,
        issues,
    ) = parse_base_promotion_sheet(
        april_path,
        "四月鋪底",
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # 3 月指定商品贈品
    benefits, issues = (
        parse_march_product_gifts(
            march_path
        )
    )

    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # 4 月吸塵器折價券
    benefits, issues = (
        parse_april_vacuum_coupons(
            april_path
        )
    )

    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # 品牌日與品牌週
    (
        records,
        benefits,
        issues,
    ) = parse_brand_day_summary(
        april_path
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    # 包套
    (
        records,
        benefits,
        issues,
    ) = parse_package_sheet(
        april_path
    )

    calendar_records.extend(records)
    benefit_records.extend(benefits)
    issue_records.extend(issues)

    calendar_dataframe = pd.DataFrame(
        calendar_records
    )

    benefits_dataframe = pd.DataFrame(
        benefit_records
    )

    issue_columns = [
        "source_file",
        "source_sheet",
        "source_row_number",
        "issue_type",
        "problem_text",
    ]

    issues_dataframe = pd.DataFrame(
        issue_records,
        columns=issue_columns,
    )

    if not calendar_dataframe.empty:
        calendar_dataframe = (
            calendar_dataframe
            .sort_values(
                by=[
                    "campaign_start_date",
                    "source_file",
                    "source_row_number",
                ],
                na_position="last",
            )
            .reset_index(drop=True)
        )

    if not benefits_dataframe.empty:
        benefits_dataframe = (
            benefits_dataframe
            .sort_values(
                by=[
                    "benefit_start_date",
                    "source_file",
                    "source_sheet",
                    "source_row_number",
                ],
                na_position="last",
            )
            .reset_index(drop=True)
        )

    summary_dataframe = (
        create_other_activity_summary(
            calendar_dataframe,
            benefits_dataframe,
            issues_dataframe,
        )
    )

    return (
        calendar_dataframe,
        benefits_dataframe,
        issues_dataframe,
        summary_dataframe,
    )


# =========================================================
# 執行按鈕
# =========================================================

if st.button(
    "執行活動資料標準化",
    type="primary",
):
    try:
        with st.spinner(
            "正在解析活動日期、價格與優惠內容……"
        ):
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                march_path = (
                    temp_path
                    / "3月品牌活動_通路.xlsx"
                )

                april_path = (
                    temp_path
                    / "4月品牌活動_通路.xlsx"
                )

                march_path.write_bytes(
                    activity_files[
                        march_file_name
                    ]
                )

                april_path.write_bytes(
                    activity_files[
                        april_file_name
                    ]
                )

                (
                    main_activity_dataframe,
                    main_activity_issues_dataframe,
                    main_activity_summary_dataframe,
                ) = standardize_main_activities(
                    march_path,
                    april_path,
                )

                (
                    calendar_dataframe,
                    benefits_dataframe,
                    other_issues_dataframe,
                    other_summary_dataframe,
                ) = standardize_other_activities(
                    march_path,
                    april_path,
                )

        # 合併兩種問題資料
        main_issues_for_merge = (
            main_activity_issues_dataframe.copy()
        )

        if (
            not main_issues_for_merge.empty
            and "problem_text"
            not in main_issues_for_merge.columns
        ):
            main_issues_for_merge[
                "problem_text"
            ] = pd.NA

        activity_issues_dataframe = pd.concat(
            [
                main_issues_for_merge,
                other_issues_dataframe,
            ],
            ignore_index=True,
            sort=False,
        )

        # 保存到 Session State
        st.session_state[
            "activity_standardized_dataframe"
        ] = main_activity_dataframe

        st.session_state[
            "activity_calendar_dataframe"
        ] = calendar_dataframe

        st.session_state[
            "promotion_benefits_dataframe"
        ] = benefits_dataframe

        st.session_state[
            "activity_issues_dataframe"
        ] = activity_issues_dataframe

        st.session_state[
            "main_activity_summary_dataframe"
        ] = main_activity_summary_dataframe

        st.session_state[
            "other_activity_summary_dataframe"
        ] = other_summary_dataframe

        st.success(
            "活動資料標準化完成。"
        )

    except Exception as error:
        st.error(
            f"活動資料標準化失敗：{error}"
        )


# =========================================================
# 取得標準化結果
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
        "請按下「執行活動資料標準化」。"
    )
    st.stop()


# =========================================================
# 顯示核心筆數
# =========================================================

st.divider()

st.subheader("標準化結果")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "商品活動期間",
    len(main_activity_dataframe),
)

col2.metric(
    "活動日曆",
    len(calendar_dataframe)
    if calendar_dataframe is not None
    else 0,
)

col3.metric(
    "優惠內容",
    len(benefits_dataframe)
    if benefits_dataframe is not None
    else 0,
)

col4.metric(
    "待確認問題",
    len(activity_issues_dataframe)
    if activity_issues_dataframe is not None
    else 0,
)


# =========================================================
# 分頁顯示資料
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "商品活動價格",
        "活動日曆",
        "優惠內容",
        "資料問題",
    ]
)


with tab1:
    st.subheader("商品活動價格資料")

    st.caption(
        "同一商品可能有多個活動期間與活動價格。"
    )

    st.dataframe(
        main_activity_dataframe,
        use_container_width=True,
        hide_index=True,
    )


with tab2:
    st.subheader("活動日曆")

    if (
        calendar_dataframe is None
        or calendar_dataframe.empty
    ):
        st.info("沒有活動日曆資料。")

    else:
        st.dataframe(
            calendar_dataframe,
            use_container_width=True,
            hide_index=True,
        )


with tab3:
    st.subheader("優惠內容")

    if (
        benefits_dataframe is None
        or benefits_dataframe.empty
    ):
        st.info("沒有優惠內容資料。")

    else:
        st.dataframe(
            benefits_dataframe,
            use_container_width=True,
            hide_index=True,
        )


with tab4:
    st.subheader("資料問題")

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

        st.dataframe(
            activity_issues_dataframe,
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# 下載標準化結果
# =========================================================

st.divider()

st.subheader("下載標準化資料")


main_activity_csv = (
    main_activity_dataframe.to_csv(
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )
    .encode("utf-8-sig")
)


calendar_csv = (
    calendar_dataframe.to_csv(
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )
    .encode("utf-8-sig")
)


benefits_csv = (
    benefits_dataframe.to_csv(
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )
    .encode("utf-8-sig")
)


issues_csv = (
    activity_issues_dataframe.to_csv(
        index=False,
        encoding="utf-8-sig",
    )
    .encode("utf-8-sig")
)


download_col1, download_col2 = st.columns(2)

with download_col1:
    st.download_button(
        "下載商品活動價格",
        data=main_activity_csv,
        file_name=(
            "activity_main_standardized.csv"
        ),
        mime="text/csv",
    )

    st.download_button(
        "下載優惠內容",
        data=benefits_csv,
        file_name=(
            "promotion_benefits_standardized.csv"
        ),
        mime="text/csv",
    )


with download_col2:
    st.download_button(
        "下載活動日曆",
        data=calendar_csv,
        file_name=(
            "campaign_calendar_standardized.csv"
        ),
        mime="text/csv",
    )

    st.download_button(
        "下載活動資料問題",
        data=issues_csv,
        file_name=(
            "activity_quality_issues.csv"
        ),
        mime="text/csv",
    )