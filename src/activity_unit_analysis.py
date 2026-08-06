from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.analysis_pipeline import (
    combine_unique_text,
    normalize_product_id,
    prepare_daily_sales,
)


# =========================================================
# 活動單位分析設定與結果
#
# 這套引擎實作的是「活動單位切分＋同月安靜期基準＋
# 量價拆解＋代理牌價＋瀑布法配對拆解」方法論，對應參考
# 報表「3-4月活動成效表_v2.xlsx」工作表2-7。
#
# 與 analysis_pipeline.py 的 calculate_activity_performance()
# 是兩套完全獨立、互不相依的方法論（基準定義不同：
# 這裡是「同月安靜期」，舊pipeline是「活動前N天」），
# 因此獨立成檔案，不修改 analysis_pipeline.py。
# =========================================================

def combine_gift_text(values: pd.Series) -> str | None:
    """
    合併贈品/加碼文字：先把每個值用「、」拆成片語，
    濾掉「無」與空白片語，再依片語去重合併。

    比 combine_unique_text() 多做兩件事，避免合併後出現
    語意不通的文字：
    1. 過濾「無」這個佔位字，避免跟真正贈品內容並列
       產生「無、贈綠豆500g」這種文字。
    2. 先拆解已用「、」串接的複合字串再去重，避免同一
       單位內不同天的相似複合字串只有部分重疊時，
       殘留片語級的重複內容
       （如「...抽宜蘭力麗威斯汀度假酒店(1名)、
       ...抽宜蘭力麗威斯汀度假酒店(1名)」）。
    """

    parts: list[str] = []

    for value in values.dropna():
        for part in str(value).split("、"):
            part = part.strip()

            if part and part != "無" and part not in parts:
                parts.append(part)

    if not parts:
        return None

    return "、".join(parts)

@dataclass(frozen=True)
class ActivityUnitAnalysisSettings:
    """活動單位分析使用的參數設定。"""

    default_year: int = 2026
    month_unit_prefix: dict[int, str] = field(
        default_factory=lambda: {3: "M", 4: "A"}
    )
    minimum_days_for_confidence: int = 2


@dataclass
class ActivityUnitAnalysisResult:
    """執行活動單位分析後回傳的所有結果。"""

    corresponding_activity_calendar: pd.DataFrame
    daily_price_panel: pd.DataFrame
    unit_timeline: pd.DataFrame
    unit_timeline_wide: pd.DataFrame
    unit_price_table: pd.DataFrame
    unit_overview: pd.DataFrame
    waterfall_pairing_table: pd.DataFrame
    waterfall_summary: pd.DataFrame
    bundle_rules: pd.DataFrame
    bundle_date_mismatches: pd.DataFrame


# =========================================================
# ① 對應活動日曆（平台層級，每日）
# =========================================================

def _prepare_schedule_and_other_level(
    calendar_dataframe: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    list[tuple[int, pd.Timestamp, pd.Timestamp]],
]:
    """
    清理／去重 activity_calendar_dataframe，拆分成「檔期層」
    （schedule_level，已補上子階段合併後的 effective_name欄位）
    與「鋪底/其他層」（other_level）兩張表，外加子階段合併時
    需要抑制的父層日期區間清單（suppress_ranges）。

    build_corresponding_activity_calendar() 與
    detect_unconditional_bundles() 共用這份清理結果，確保兩邊
    看到完全一致的母/子活動名稱，母子活動判斷才不會跟「對應
    活動」標籤實際顯示的名稱脫鉤。
    """

    calendar = calendar_dataframe.dropna(
        subset=[
            "campaign_name",
            "campaign_start_date",
            "campaign_end_date",
        ]
    ).copy()

    calendar["campaign_start_date"] = pd.to_datetime(
        calendar["campaign_start_date"], errors="coerce"
    )
    calendar["campaign_end_date"] = pd.to_datetime(
        calendar["campaign_end_date"], errors="coerce"
    )

    calendar = calendar.dropna(
        subset=["campaign_start_date", "campaign_end_date"]
    )
    calendar = calendar[
        calendar["campaign_end_date"] >= calendar["campaign_start_date"]
    ]

    if calendar.empty:
        empty_schedule = pd.DataFrame(
            columns=[
                "campaign_name",
                "campaign_level",
                "campaign_start_date",
                "campaign_end_date",
                "effective_name",
                "root_title",
            ]
        )
        empty_other = pd.DataFrame(
            columns=[
                "campaign_name",
                "campaign_level",
                "campaign_start_date",
                "campaign_end_date",
            ]
        )
        return empty_schedule, empty_other, []

    # 1-2/1-4：同一活動名稱＋起訖日期只留一筆
    # （鋪底門檻級距不同但屬同一機制、同一時間區間）
    unique_campaigns = calendar.drop_duplicates(
        subset=[
            "campaign_name",
            "campaign_start_date",
            "campaign_end_date",
        ]
    ).reset_index(drop=True)

    schedule_level = unique_campaigns[
        unique_campaigns["campaign_level"] == "平台檔期"
    ].copy()
    other_level = unique_campaigns[
        unique_campaigns["campaign_level"] != "平台檔期"
    ].copy()

    # 子階段合併偵測：只在「檔期」層級內找包含關係，
    # 且只有「在同一個月份內只出現過一次」的活動名稱才視為
    # 子階段候選（避免像「廚電日」這種會在同月內重複出現的
    # 跨檔期活動被誤merge；用「同月內」而非「全域」判斷單次
    # 出現，是因為「暖身」「正式」這類子階段名稱在不同月份
    # 會重複使用，例如3月與4月都有「暖身」，但各自在自己
    # 月份內只出現一次，仍應各自視為合法的子階段候選）。
    schedule_level["_start_month"] = schedule_level[
        "campaign_start_date"
    ].dt.month
    schedule_level["_duration_days"] = (
        schedule_level["campaign_end_date"]
        - schedule_level["campaign_start_date"]
    ).dt.days

    name_occurrence = schedule_level.groupby(
        ["campaign_name", "_start_month"]
    ).size()

    rename_lookup: dict[int, str] = {}
    root_title_lookup: dict[int, str] = {}
    suppress_ranges: list[tuple[int, pd.Timestamp, pd.Timestamp]] = []

    for b_index, b_row in schedule_level.iterrows():
        occurrence_key = (
            b_row["campaign_name"],
            b_row["_start_month"],
        )

        if name_occurrence.get(occurrence_key, 0) != 1:
            continue

        b_duration_days = (
            b_row["campaign_end_date"] - b_row["campaign_start_date"]
        ).days

        candidates = schedule_level[
            (schedule_level.index != b_index)
            & (schedule_level["campaign_name"] != b_row["campaign_name"])
            & (
                schedule_level["campaign_start_date"]
                <= b_row["campaign_start_date"]
            )
            & (
                schedule_level["campaign_end_date"]
                >= b_row["campaign_end_date"]
            )
            # 候選母活動的時間跨度必須嚴格大於子活動本身，才
            # 視為真正的包含式子階段關係（如女王節15天 >
            # 暖身6天）。如果跨度相同，代表兩個檔期活動只是
            # 剛好日期完全重疊，彼此是各自獨立的檔期活動。
            & (schedule_level["_duration_days"] > b_duration_days)
        ]

        # 只有「剛好只有一個」符合包含關係的候選母活動時，才
        # 視為真正的子階段關係（如女王節暖身/正式，各自都只
        # 對到女王節這一個候選）。如果同時有兩個以上的候選都
        # 包住這個子活動（如品牌日剛好同時落在廚電日、平台日
        # 各自的區間內），代表這只是巧合的日期重疊，不是真正
        # 的母子關係——品牌日本身就是有意義的獨立活動名稱，
        # 不應該被巧合重疊的其他檔期活動吸收成複合名稱，否則
        # 會產生「廚電日品牌日」這種語意錯誤、且會把兩個本來
        # 不相干活動的效果混在一起評估的結果。
        if len(candidates) != 1:
            continue

        parent_row = candidates.iloc[0]

        rename_lookup[b_index] = (
            f"{parent_row['campaign_name']}{b_row['campaign_name']}"
        )

        root_title_lookup[b_index] = parent_row["campaign_name"]

        suppress_ranges.append(
            (
                parent_row.name,
                b_row["campaign_start_date"],
                b_row["campaign_end_date"],
            )
        )

    schedule_level["effective_name"] = [
        rename_lookup.get(index, row["campaign_name"])
        for index, row in schedule_level.iterrows()
    ]

    # root_title：子階段合併發生時，記錄合併前母活動自己的
    # campaign_name（如「女王節」）；沒有合併、維持獨立的列
    # （如「廚電日」），root_title 就是自己的 campaign_name。
    # 給 detect_unconditional_bundles() 用來比對子活動名稱
    # 是否包含母活動關鍵字。
    schedule_level["root_title"] = [
        root_title_lookup.get(index, row["campaign_name"])
        for index, row in schedule_level.iterrows()
    ]

    # 鋪底日期優先：同一個活動名稱如果鋪底表自己也有一列
    # （例如「平台日」除了是檔期，鋪底表也有一列「平台日」
    # 滿額登記送平台幣機制），代表這才是真正有實際優惠、
    # 可以拿來算增益的期間，通常比檔期表的概略日期更準確。
    # 這種情況下改用鋪底表自己列出的日期取代檔期日期；檔期表
    # 裡「有檔期、但鋪底表完全沒有對應列」的活動則維持原本
    # 檔期日期不變。用 effective_name（子階段合併後的名稱）
    # 比對，確保跟鋪底表慣用的複合命名（如「女王節正式」）
    # 對得上。
    if not other_level.empty:
        # 用「同月份」限定比對範圍，避免像「平台日」這種名稱
        # 在不同月份各自出現一次時，被誤合併成橫跨兩個月份的
        # 荒謬日期區間（跟子階段合併偵測用「同月內」限定單次
        # 出現是同一個道理）。
        for index, row in schedule_level.iterrows():
            effective_name = row["effective_name"]
            row_start_month = row["campaign_start_date"].month

            same_name_same_month = other_level[
                (other_level["campaign_name"] == effective_name)
                & (
                    other_level["campaign_start_date"].dt.month
                    == row_start_month
                )
            ]

            if same_name_same_month.empty:
                continue

            schedule_level.loc[
                index, "campaign_start_date"
            ] = same_name_same_month[
                "campaign_start_date"
            ].min()
            schedule_level.loc[
                index, "campaign_end_date"
            ] = same_name_same_month["campaign_end_date"].max()

    return schedule_level, other_level, suppress_ranges


def build_corresponding_activity_calendar(
    calendar_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    展開 activity_calendar_dataframe 成每日「對應活動」清單。

    設計假設：「對應活動」在此實作中是平台層級（同一天
    對所有 SKU 相同），因為檔期/鋪底來源表本身沒有商品欄位，
    無法做到真正 SKU 專屬。SKU 層級的參與差異由
    build_daily_sku_price_panel() 的 is_participating 旗標
    另外表達。這是對照參考 Excel 報表時最需要優先核對的假設。
    """

    schedule_level, other_level, suppress_ranges = (
        _prepare_schedule_and_other_level(calendar_dataframe)
    )

    if schedule_level.empty and other_level.empty:
        return pd.DataFrame(
            columns=[
                "sale_date",
                "corresponding_activities",
                "corresponding_activities_label",
            ]
        )

    schedule_daily_records: list[dict[str, object]] = []

    for row in schedule_level.itertuples():
        for day in pd.date_range(
            row.campaign_start_date,
            row.campaign_end_date,
            freq="D",
        ):
            schedule_daily_records.append(
                {
                    "sale_date": day,
                    "source_index": row.Index,
                    "name": row.effective_name,
                }
            )

    schedule_daily = pd.DataFrame(schedule_daily_records)

    # 被合併成子階段複合名稱的天數，原父層活動本身的
    # 純文字名稱要在那些天被抑制，避免同時出現
    # 「女王節」與「女王節暖身」造成語意重複。
    for parent_index, start_date, end_date in suppress_ranges:
        if schedule_daily.empty:
            break

        mask = (
            (schedule_daily["source_index"] == parent_index)
            & (schedule_daily["sale_date"] >= start_date)
            & (schedule_daily["sale_date"] <= end_date)
        )
        schedule_daily = schedule_daily[~mask]

    other_daily_records: list[dict[str, object]] = []

    for row in other_level.itertuples():
        for day in pd.date_range(
            row.campaign_start_date,
            row.campaign_end_date,
            freq="D",
        ):
            other_daily_records.append(
                {
                    "sale_date": day,
                    "name": row.campaign_name,
                }
            )

    other_daily = pd.DataFrame(other_daily_records)

    combined_daily = pd.concat(
        [
            schedule_daily[["sale_date", "name"]]
            if not schedule_daily.empty
            else pd.DataFrame(columns=["sale_date", "name"]),
            other_daily
            if not other_daily.empty
            else pd.DataFrame(columns=["sale_date", "name"]),
        ],
        ignore_index=True,
    )

    if combined_daily.empty:
        return pd.DataFrame(
            columns=[
                "sale_date",
                "corresponding_activities",
                "corresponding_activities_label",
            ]
        )

    grouped = (
        combined_daily.groupby("sale_date")["name"]
        .agg(lambda names: sorted(set(n for n in names if n)))
        .reset_index()
        .rename(columns={"name": "corresponding_activities"})
    )

    grouped["corresponding_activities_label"] = grouped[
        "corresponding_activities"
    ].apply(lambda names: "、".join(names))

    return grouped


# =========================================================
# ①之二 母子活動不可分割群組
# =========================================================

BUNDLE_RULE_COLUMNS = [
    "mother_name",
    "mother_start_date",
    "mother_end_date",
    "child_name",
    "child_start_date",
    "child_end_date",
]


def detect_unconditional_bundles(
    calendar_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    找出「母子活動密不可分」的明確規則，取代原本純粹依賴
    瀑布法找不到對照組時的被動 fallback。

    子候選一律只從鋪底層（other_level）取，母候選一律只從
    檔期層（schedule_level，已套用子階段合併命名）取——這個
    層級限制本身就足以避免「兩個檔期活動剛好同一天重疊」被
    誤判成母子關係。

    母子關係需要同時滿足兩個條件，缺一不可：
    1. 日期區間完全一致（起訖日都相等，不是包含關係）。
    2. 子活動的活動名稱欄位文字要包含母活動的根關鍵字
       （root_title，例如母活動「女王節正式」的根關鍵字是
       「女王節」，子活動「女王節原廠鋪底贈」因為文字裡有
       「女王節」才算數）。

    只驗證日期不驗證名稱，會把剛好同期但主題無關的活動誤判
    成一組（例如母親節檔期跟廚電日鋪底贈剛好同期）；只驗證
    名稱不驗證日期，則會把同一名稱在不同時間點的多次出現
    互相混淆。兩個條件一起要求，才能同時避免這兩種誤判。

    兩個條件同時滿足的候選母活動如果剛好只有一個，才產生一筆
    bundle rule；零個或多個都不產生（不確定時寧可不合併，維持
    各自獨立）。

    每一次子機制出現都各自獨立判斷歸屬，所以像「送平台幣」
    這種在多個不同母活動下、用不同門檻重複出現的名稱，每次
    出現會各自產生一筆規則、各自歸到當次真正符合條件的母活動，
    不會互相污染。
    """

    schedule_level, other_level, _ = _prepare_schedule_and_other_level(
        calendar_dataframe
    )

    if schedule_level.empty or other_level.empty:
        return pd.DataFrame(columns=BUNDLE_RULE_COLUMNS)

    records: list[dict[str, object]] = []

    for _, child_row in other_level.iterrows():
        candidates = schedule_level[
            (
                schedule_level["campaign_start_date"]
                == child_row["campaign_start_date"]
            )
            & (
                schedule_level["campaign_end_date"]
                == child_row["campaign_end_date"]
            )
            & (
                schedule_level["root_title"].apply(
                    lambda root_title: root_title
                    in child_row["campaign_name"]
                )
            )
        ]

        if len(candidates) != 1:
            continue

        mother_row = candidates.iloc[0]

        records.append(
            {
                "mother_name": mother_row["effective_name"],
                "mother_start_date": mother_row[
                    "campaign_start_date"
                ],
                "mother_end_date": mother_row["campaign_end_date"],
                "child_name": child_row["campaign_name"],
                "child_start_date": child_row["campaign_start_date"],
                "child_end_date": child_row["campaign_end_date"],
            }
        )

    return pd.DataFrame(records, columns=BUNDLE_RULE_COLUMNS)


BUNDLE_DATE_MISMATCH_COLUMNS = [
    "mother_name",
    "mother_start_date",
    "mother_end_date",
    "child_name",
    "child_start_date",
    "child_end_date",
    "issue_type",
    "problem_text",
]


def detect_bundle_date_mismatches(
    calendar_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    找出「子活動名稱包含母活動關鍵字、日期也有重疊，但沒有
    完全對齊」的情況，標註出來提醒使用者確認來源資料。

    detect_unconditional_bundles() 要求日期完全一致才會判定
    成正式組合，這裡是它的互補：日期只要沒有完全對齊，不論
    是包含關係還是部分重疊，只要子活動名稱包含母活動關鍵字
    就會被標註成一筆提醒，不會被實際合併（分類與顯示名稱都
    不受影響），純粹讓使用者知道「這兩筆名稱看起來屬於同一組，
    但日期對不上，可能是來源資料填寫不精準，建議回頭確認」。

    完全沒有重疊的日期區間不會被標註——那種情況比較像是
    名稱剛好用到相同關鍵字的巧合，不是真正日期填寫落差。
    """

    schedule_level, other_level, _ = _prepare_schedule_and_other_level(
        calendar_dataframe
    )

    if schedule_level.empty or other_level.empty:
        return pd.DataFrame(columns=BUNDLE_DATE_MISMATCH_COLUMNS)

    records: list[dict[str, object]] = []

    for _, child_row in other_level.iterrows():
        keyword_candidates = schedule_level[
            schedule_level["root_title"].apply(
                lambda root_title: root_title
                in child_row["campaign_name"]
            )
            & (
                schedule_level["campaign_start_date"]
                <= child_row["campaign_end_date"]
            )
            & (
                schedule_level["campaign_end_date"]
                >= child_row["campaign_start_date"]
            )
        ]

        for _, mother_row in keyword_candidates.iterrows():
            exact_match = (
                mother_row["campaign_start_date"]
                == child_row["campaign_start_date"]
                and mother_row["campaign_end_date"]
                == child_row["campaign_end_date"]
            )

            if exact_match:
                continue

            records.append(
                {
                    "mother_name": mother_row["effective_name"],
                    "mother_start_date": mother_row[
                        "campaign_start_date"
                    ],
                    "mother_end_date": mother_row["campaign_end_date"],
                    "child_name": child_row["campaign_name"],
                    "child_start_date": child_row["campaign_start_date"],
                    "child_end_date": child_row["campaign_end_date"],
                    "issue_type": (
                        "活動組合關鍵字相符但日期未完全對齊"
                    ),
                    "problem_text": (
                        f"「{child_row['campaign_name']}」"
                        f"（{child_row['campaign_start_date'].date()}"
                        f"～{child_row['campaign_end_date'].date()}）"
                        f"名稱包含母活動關鍵字「"
                        f"{mother_row['root_title']}」，但跟"
                        f"「{mother_row['effective_name']}」"
                        f"（{mother_row['campaign_start_date'].date()}"
                        f"～{mother_row['campaign_end_date'].date()}）"
                        "的日期不完全一致，未被視為同一個不可分割"
                        "活動組合，建議確認來源資料日期是否正確。"
                    ),
                }
            )

    return pd.DataFrame(
        records, columns=BUNDLE_DATE_MISMATCH_COLUMNS
    )


def _bundle_windows(
    bundle_rules: pd.DataFrame,
) -> list[tuple[pd.Timestamp, pd.Timestamp, frozenset[str], str]]:
    """
    把 detect_unconditional_bundles() 產生的逐子機制規則列，
    依 (mother_name, mother_start_date, mother_end_date) 分組，
    整理成「這個時間窗口內，這些名稱要被當成同一個不可分割
    的原子單位，收合後要用哪個母活動名稱命名」的清單，只有
    真的有子機制被合併的母活動才會產生一筆。
    """

    if bundle_rules is None or bundle_rules.empty:
        return []

    windows: list[
        tuple[pd.Timestamp, pd.Timestamp, frozenset[str], str]
    ] = []

    grouped = bundle_rules.groupby(
        ["mother_name", "mother_start_date", "mother_end_date"]
    )

    for (mother_name, start_date, end_date), group in grouped:
        members = frozenset({mother_name, *group["child_name"]})
        windows.append((start_date, end_date, members, mother_name))

    return windows


def collapse_activity_set_with_bundles(
    activity_set: frozenset[str],
    reference_date: pd.Timestamp,
    bundle_rules: pd.DataFrame
    | list[tuple[pd.Timestamp, pd.Timestamp, frozenset[str], str]]
    | None,
) -> frozenset[str]:
    """
    把 activity_set 裡屬於同一個已知不可分割組合的名稱，合併
    成單一原子標籤「{母活動名稱}組合」（例如「女王節正式
    組合」），當成一個普通活動名稱使用，跟其他單一活動名稱
    （如「廚電日」）一視同仁——不再逐一把被合併的名稱串接
    起來顯示，避免名稱過長。不屬於任何已知組合窗口的名稱維持
    原樣，逐一通過。

    bundle_rules 可以直接傳 detect_unconditional_bundles() 的
    原始輸出（DataFrame），也可以傳已經用 _bundle_windows()
    整理好的清單（build_waterfall_pairing_table() 內部重複呼叫
    很多次時，外部先轉換一次比較有效率）。
    """

    if isinstance(bundle_rules, pd.DataFrame):
        windows = _bundle_windows(bundle_rules)
    else:
        windows = bundle_rules or []

    remaining = set(activity_set)
    collapsed: set[str] = set()

    for start_date, end_date, members, mother_name in windows:
        if not (start_date <= reference_date <= end_date):
            continue

        matched = remaining & members

        if not matched:
            continue

        remaining -= matched
        collapsed.add(f"{mother_name}組合")

    collapsed |= remaining

    return frozenset(collapsed)


# =========================================================
# ② 逐日逐SKU 銷量與售價面板（含全域零填補與代理牌價）
# =========================================================

def build_daily_sku_price_panel(
    sales_dataframe: pd.DataFrame,
    activity_standardized_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    建立逐日逐SKU的銷量／售價面板，對應工作表2。

    與 analysis_pipeline.py::get_period_daily_sales() 不同，
    這裡是對「整個資料集」做零填補（真正的全域零填補），
    不只是在分析窗格內補零。
    """

    daily_sales = prepare_daily_sales(sales_dataframe)

    activity = activity_standardized_dataframe.copy()

    activity["product_id"] = normalize_product_id(
        activity["product_id"]
    )
    activity["activity_start_date"] = pd.to_datetime(
        activity["activity_start_date"], errors="coerce"
    )
    activity["activity_end_date"] = pd.to_datetime(
        activity["activity_end_date"], errors="coerce"
    )
    activity["campaign_price"] = pd.to_numeric(
        activity["campaign_price"], errors="coerce"
    )

    activity = activity.dropna(
        subset=[
            "product_id",
            "activity_start_date",
            "activity_end_date",
            "campaign_price",
        ]
    )
    activity = activity[
        activity["activity_end_date"] >= activity["activity_start_date"]
    ]

    all_dates = pd.date_range(
        daily_sales["sale_date"].min(),
        daily_sales["sale_date"].max(),
        freq="D",
    )

    product_lookup = (
        pd.concat(
            [
                daily_sales[["product_id", "product_name"]],
                activity[["product_id", "product_name"]]
                if "product_name" in activity.columns
                else pd.DataFrame(
                    columns=["product_id", "product_name"]
                ),
            ],
            ignore_index=True,
        )
        .dropna(subset=["product_id"])
        .drop_duplicates(subset=["product_id"])
        .set_index("product_id")["product_name"]
    )

    all_products = sorted(product_lookup.index.tolist())

    full_grid = pd.MultiIndex.from_product(
        [all_dates, all_products],
        names=["sale_date", "product_id"],
    ).to_frame(index=False)

    full_grid["product_name"] = full_grid["product_id"].map(
        product_lookup
    )

    full_grid = full_grid.merge(
        daily_sales[["sale_date", "product_id", "quantity"]],
        on=["sale_date", "product_id"],
        how="left",
    )
    full_grid["quantity_zero_filled"] = full_grid[
        "quantity"
    ].fillna(0)

    activity_daily_records: list[dict[str, object]] = []

    for row in activity.itertuples():
        for day in pd.date_range(
            row.activity_start_date,
            row.activity_end_date,
            freq="D",
        ):
            activity_daily_records.append(
                {
                    "sale_date": day,
                    "product_id": row.product_id,
                    "campaign_price_day": row.campaign_price,
                    "activity_tag": getattr(
                        row, "activity_tag", None
                    ),
                    "activity_gift": getattr(
                        row, "activity_gift", None
                    ),
                    "bonus_gift_text": getattr(
                        row, "bonus_gift_text", None
                    ),
                    "bonus_campaign_text": getattr(
                        row, "bonus_campaign_text", None
                    ),
                    "product_category": getattr(
                        row, "product_category", None
                    ),
                }
            )

    activity_daily = pd.DataFrame(activity_daily_records)

    if not activity_daily.empty:
        activity_daily = activity_daily.groupby(
            ["sale_date", "product_id"], as_index=False
        ).agg(
            campaign_price_day=("campaign_price_day", "min"),
            activity_tag=("activity_tag", combine_unique_text),
            activity_gift=("activity_gift", combine_gift_text),
            bonus_gift_text=(
                "bonus_gift_text",
                combine_gift_text,
            ),
            bonus_campaign_text=(
                "bonus_campaign_text",
                combine_gift_text,
            ),
            product_category=(
                "product_category",
                combine_unique_text,
            ),
        )

        full_grid = full_grid.merge(
            activity_daily,
            on=["sale_date", "product_id"],
            how="left",
        )
    else:
        for column in [
            "campaign_price_day",
            "activity_tag",
            "activity_gift",
            "bonus_gift_text",
            "bonus_campaign_text",
            "product_category",
        ]:
            full_grid[column] = pd.NA

    full_grid["is_participating"] = full_grid[
        "campaign_price_day"
    ].notna()

    activity["month"] = activity["activity_start_date"].dt.month

    proxy_price_lookup = (
        activity.groupby(["product_id", "month"], as_index=False)[
            "campaign_price"
        ]
        .max()
        .rename(columns={"campaign_price": "proxy_price"})
    )

    full_grid["month"] = full_grid["sale_date"].dt.month

    full_grid = full_grid.merge(
        proxy_price_lookup,
        on=["product_id", "month"],
        how="left",
    )

    full_grid["effective_price"] = full_grid[
        "campaign_price_day"
    ].where(
        full_grid["is_participating"],
        full_grid["proxy_price"],
    )

    full_grid["price_source"] = pd.NA
    full_grid.loc[
        full_grid["is_participating"], "price_source"
    ] = "活動表(實際)"

    proxy_used_mask = (
        ~full_grid["is_participating"]
        & full_grid["proxy_price"].notna()
    )
    full_grid.loc[
        proxy_used_mask, "price_source"
    ] = "代理牌價(當月最高售價,估算)"

    return full_grid[
        [
            "sale_date",
            "product_id",
            "product_name",
            "month",
            "quantity_zero_filled",
            "is_participating",
            "effective_price",
            "price_source",
            "activity_tag",
            "activity_gift",
            "bonus_gift_text",
            "bonus_campaign_text",
            "product_category",
        ]
    ]


# =========================================================
# ③ 掛上對應活動
# =========================================================

def assign_corresponding_activity(
    daily_price_panel: pd.DataFrame,
    corresponding_activity_calendar: pd.DataFrame,
) -> pd.DataFrame:
    """合併每日售價面板與對應活動日曆。"""

    merged = daily_price_panel.merge(
        corresponding_activity_calendar,
        on="sale_date",
        how="left",
    )

    merged["corresponding_activities"] = merged[
        "corresponding_activities"
    ].apply(lambda value: value if isinstance(value, list) else [])

    merged["corresponding_activities_label"] = merged[
        "corresponding_activities_label"
    ].fillna("")

    merged["is_quiet_period"] = merged[
        "corresponding_activities"
    ].apply(lambda value: len(value) == 0)

    return merged


# =========================================================
# ④ 活動單位切分（切點聯集）
# =========================================================

def split_activity_units(
    daily_panel_with_calendar: pd.DataFrame,
    settings: ActivityUnitAnalysisSettings,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    依「(對應活動,售價) 任一SKU發生變化即切一刀」的規則，
    切出全部SKU共用的活動單位時間軸。
    """

    frame = daily_panel_with_calendar.copy()

    signature_records: list[dict[str, object]] = []

    for sale_date, group in frame.groupby("sale_date"):
        signature = tuple(
            sorted(
                (
                    row.product_id,
                    row.corresponding_activities_label,
                    round(float(row.effective_price), 2)
                    if pd.notna(row.effective_price)
                    else None,
                    bool(row.is_participating),
                )
                for row in group.itertuples()
            )
        )

        signature_records.append(
            {
                "sale_date": sale_date,
                "month": sale_date.month,
                "signature": signature,
            }
        )

    signature_dataframe = pd.DataFrame(
        signature_records
    ).sort_values("sale_date").reset_index(drop=True)

    unit_records: list[dict[str, object]] = []
    lookup_records: list[dict[str, object]] = []

    def is_quiet_signature(signature: tuple) -> bool:
        return all(
            label == "" for (_, label, _, _) in signature
        )

    def flush_segment(
        prefix: str,
        unit_number: int,
        month: int,
        segment_signature: tuple,
        segment_start: pd.Timestamp,
        segment_end: pd.Timestamp,
    ) -> None:
        unit_code = f"{prefix}{unit_number}"

        unit_records.append(
            {
                "unit_code": unit_code,
                "month": int(month),
                "start_date": segment_start,
                "end_date": segment_end,
                "days": (segment_end - segment_start).days + 1,
                "note": (
                    "(基準/安靜期)"
                    if is_quiet_signature(segment_signature)
                    else ""
                ),
            }
        )

        for day in pd.date_range(
            segment_start, segment_end, freq="D"
        ):
            lookup_records.append(
                {"sale_date": day, "unit_code": unit_code}
            )

    for month, month_group in signature_dataframe.groupby("month"):
        month_group = month_group.sort_values(
            "sale_date"
        ).reset_index(drop=True)

        prefix = settings.month_unit_prefix.get(
            int(month), f"M{month}"
        )

        unit_number = 0
        segment_signature = None
        segment_start = None
        segment_end = None

        for row in month_group.itertuples():
            if segment_signature is None:
                segment_signature = row.signature
                segment_start = row.sale_date
                segment_end = row.sale_date
                continue

            if row.signature == segment_signature:
                segment_end = row.sale_date
                continue

            unit_number += 1
            flush_segment(
                prefix,
                unit_number,
                month,
                segment_signature,
                segment_start,
                segment_end,
            )

            segment_signature = row.signature
            segment_start = row.sale_date
            segment_end = row.sale_date

        if segment_signature is not None:
            unit_number += 1
            flush_segment(
                prefix,
                unit_number,
                month,
                segment_signature,
                segment_start,
                segment_end,
            )

    unit_timeline = pd.DataFrame(unit_records)
    date_to_unit_lookup = pd.DataFrame(lookup_records)

    return unit_timeline, date_to_unit_lookup


# =========================================================
# ⑤ 掛上活動單位代碼
# =========================================================

def attach_unit_code(
    daily_panel_with_calendar: pd.DataFrame,
    date_to_unit_lookup: pd.DataFrame,
) -> pd.DataFrame:
    """把切分好的活動單位代碼合併回每日面板。"""

    return daily_panel_with_calendar.merge(
        date_to_unit_lookup, on="sale_date", how="left"
    )


# =========================================================
# ⑥ 活動單位清單（寬表，僅供頁面預覽）
# =========================================================

def pivot_unit_timeline_wide(
    unit_timeline: pd.DataFrame,
    daily_panel_with_units: pd.DataFrame,
) -> pd.DataFrame:
    """
    把活動單位清單轉成逐SKU一欄的寬表，
    比照參考 Excel 工作表3「活動單位清單(依時間)」樣式，
    僅供頁面預覽使用，不作為其他函式的輸入。
    """

    if unit_timeline.empty:
        return unit_timeline.copy()

    working = daily_panel_with_units[
        daily_panel_with_units["unit_code"].notna()
    ].copy()

    def most_common_label(values: pd.Series) -> str:
        mode_values = values.mode()

        if not mode_values.empty:
            return str(mode_values.iat[0])

        if len(values):
            return str(values.iloc[0])

        return ""

    per_unit_product = (
        working.groupby(
            ["unit_code", "product_id", "product_name"],
            as_index=False,
        )["corresponding_activities_label"]
        .agg(most_common_label)
    )

    per_unit_product["column_name"] = (
        per_unit_product["product_id"].astype(str)
        + "_"
        + per_unit_product["product_name"].astype(str)
        + "_對應活動"
    )

    wide = per_unit_product.pivot_table(
        index="unit_code",
        columns="column_name",
        values="corresponding_activities_label",
        aggfunc="first",
    ).reset_index()

    return unit_timeline.merge(wide, on="unit_code", how="left")


# =========================================================
# ⑦ 商品售價表（依單位）
# =========================================================

def build_unit_price_table(
    daily_panel_with_units: pd.DataFrame,
) -> pd.DataFrame:
    """對應工作表4「商品售價表(依單位)」。"""

    working = daily_panel_with_units[
        daily_panel_with_units["unit_code"].notna()
    ].copy()

    if working.empty:
        return pd.DataFrame(
            columns=[
                "unit_code",
                "product_id",
                "product_name",
                "product_category",
                "start_date",
                "end_date",
                "price",
                "price_source",
                "activity_tag",
                "gift",
                "bonus_gift_text",
                "bonus_campaign_text",
                "note",
            ]
        )

    grouped = working.groupby(
        ["unit_code", "product_id"], as_index=False
    ).agg(
        product_name=("product_name", "first"),
        product_category=(
            "product_category",
            combine_unique_text,
        ),
        start_date=("sale_date", "min"),
        end_date=("sale_date", "max"),
        price=("effective_price", "mean"),
        price_std=("effective_price", "std"),
        price_source=(
            "price_source",
            lambda series: (
                series.mode().iat[0]
                if not series.mode().empty
                else pd.NA
            ),
        ),
        activity_tag=("activity_tag", combine_unique_text),
        gift=("activity_gift", combine_gift_text),
        bonus_gift_text=(
            "bonus_gift_text",
            combine_gift_text,
        ),
        bonus_campaign_text=(
            "bonus_campaign_text",
            combine_gift_text,
        ),
    )

    grouped["note"] = grouped["price_std"].apply(
        lambda value: (
            "單位內售價非常數，已取平均"
            if pd.notna(value) and value > 0
            else ""
        )
    )

    return grouped.drop(columns=["price_std"])


# =========================================================
# ⑧ 活動單位總覽（vs 基準）
# =========================================================

def build_unit_overview_vs_baseline(
    daily_panel_with_units: pd.DataFrame,
    settings: ActivityUnitAnalysisSettings,
    bundle_rules: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    對應工作表5「活動單位總覽(vs基準)」（22欄）。

    bundle_rules（來自 detect_unconditional_bundles()）如果有
    提供，分類欄位會先把落在已知不可分割組合窗口內的標籤
    合併起來再算數量，讓「這其實是一個不可分割的活動組合」
    跟「單純疊加了多個活動、還不確定能不能拆」分開標示，不
    再一律都算成「多活動合併,不可分離」。傳 None 或空表時，
    行為與加這個參數之前完全相同。
    """

    columns = [
        "product_id",
        "product_name",
        "product_category",
        "month",
        "unit_code",
        "start_date",
        "end_date",
        "days",
        "corresponding_activities_label",
        "is_participating",
        "unit_avg_sales",
        "baseline_avg_sales",
        "baseline_price",
        "unit_avg_price",
        "sales_increment",
        "volume_effect_per_day",
        "price_effect_per_day",
        "net_revenue_effect_per_day",
        "net_revenue_effect_total",
        "classification",
        "sample_size_note",
        "proxy_price_note",
    ]

    working = daily_panel_with_units[
        daily_panel_with_units["unit_code"].notna()
    ].copy()

    if working.empty:
        return pd.DataFrame(columns=columns)

    baseline_stats = (
        working[working["is_quiet_period"]]
        .groupby(["product_id", "month"], as_index=False)
        .agg(
            baseline_avg_sales=("quantity_zero_filled", "mean"),
            baseline_price=("effective_price", "mean"),
            quiet_days=("sale_date", "nunique"),
        )
    )

    unit_stats = working.groupby(
        ["product_id", "unit_code"], as_index=False
    ).agg(
        product_name=("product_name", "first"),
        product_category=(
            "product_category",
            combine_unique_text,
        ),
        month=("month", "first"),
        start_date=("sale_date", "min"),
        end_date=("sale_date", "max"),
        days=("sale_date", "nunique"),
        unit_avg_sales=("quantity_zero_filled", "mean"),
        unit_avg_price=("effective_price", "mean"),
        is_participating=("is_participating", "any"),
        corresponding_activities_label=(
            "corresponding_activities_label",
            "first",
        ),
        is_quiet_period=("is_quiet_period", "first"),
        price_source_mode=(
            "price_source",
            lambda series: (
                series.mode().iat[0]
                if not series.mode().empty
                else pd.NA
            ),
        ),
    )

    unit_stats = unit_stats[~unit_stats["is_quiet_period"]].copy()

    merged = unit_stats.merge(
        baseline_stats, on=["product_id", "month"], how="left"
    )

    merged["sales_increment"] = (
        merged["unit_avg_sales"] - merged["baseline_avg_sales"]
    )

    merged["volume_effect_per_day"] = (
        merged["sales_increment"] * merged["baseline_price"]
    )

    merged["price_effect_per_day"] = merged[
        "baseline_avg_sales"
    ] * (merged["unit_avg_price"] - merged["baseline_price"])

    merged["net_revenue_effect_per_day"] = (
        merged["volume_effect_per_day"]
        + merged["price_effect_per_day"]
    )

    merged["net_revenue_effect_total"] = (
        merged["net_revenue_effect_per_day"] * merged["days"]
    )

    bundle_windows = _bundle_windows(bundle_rules)

    def classify_unit(row: pd.Series) -> tuple[str, str]:
        """
        回傳 (classification, 顯示用活動名稱)。

        classification 的值必須維持固定字串，因為畫面篩選/
        著色邏輯是直接比對這個欄位的值——是否判定成「不可
        分割活動組合」仍然要求收合後剛好只剩一個項目（代表
        當天的活動效果完全等於這一個組合，沒有混到其他無關
        活動，淨營收才能乾淨歸因給這個組合）。

        顯示用活動名稱則獨立處理：只要偵測到已知組合，不管
        當天是否還疊加了其他無關活動，都把組合成員收合成
        「{母活動名稱}組合」再跟其餘名稱一起顯示，取代原本
        逐一串接的完整名稱，避免名稱過長。
        """

        label = row["corresponding_activities_label"]
        raw_set = frozenset(
            part for part in (label or "").split("、") if part
        )

        if len(raw_set) <= 1:
            return "可分離,單一活動", label

        if not bundle_windows:
            return "多活動疊加,待瀑布法檢驗", label

        collapsed = collapse_activity_set_with_bundles(
            raw_set, row["start_date"], bundle_windows
        )

        display_label = "、".join(sorted(collapsed))

        if len(collapsed) == 1:
            return "不可分割活動組合", display_label

        return "多活動疊加,待瀑布法檢驗", display_label

    classification_and_label = merged.apply(classify_unit, axis=1)
    merged["classification"] = classification_and_label.apply(
        lambda pair: pair[0]
    )
    merged["corresponding_activities_label"] = (
        classification_and_label.apply(lambda pair: pair[1])
    )

    def sample_note(row: pd.Series) -> str:
        notes = []

        if row["days"] < settings.minimum_days_for_confidence:
            notes.append("樣本量小,信賴區間寬")

        if (
            pd.isna(row["quiet_days"])
            or row["quiet_days"]
            < settings.minimum_days_for_confidence
        ):
            notes.append("基準期樣本量小")

        return "、".join(notes)

    merged["sample_size_note"] = merged.apply(
        sample_note, axis=1
    )

    merged["proxy_price_note"] = merged[
        "price_source_mode"
    ].apply(
        lambda value: (
            "本期本品項未參與(使用代理牌價)"
            if isinstance(value, str) and "代理牌價" in value
            else ""
        )
    )

    return (
        merged[columns]
        .sort_values(["month", "unit_code", "product_id"])
        .reset_index(drop=True)
    )


def build_quiet_period_reference_units(
    daily_panel_with_units: pd.DataFrame,
) -> pd.DataFrame:
    """
    彙整安靜期活動單位的逐單位統計，供瀑布法拆解使用。

    當某個活動單位的對應活動只有單一活動X時，扣掉X後的
    「剩餘對應活動」是空集合，這種情況的正確對照組就是
    同商品同月份的安靜期單位本身（而不是任何仍有活動的
    單位），所以需要獨立於 build_unit_overview_vs_baseline()
    （該函式會排除安靜期單位）另外準備這份資料。
    """

    working = daily_panel_with_units[
        daily_panel_with_units["unit_code"].notna()
        & daily_panel_with_units["is_quiet_period"]
    ]

    columns = [
        "product_id",
        "month",
        "unit_code",
        "days",
        "unit_avg_sales",
        "unit_avg_price",
    ]

    if working.empty:
        return pd.DataFrame(columns=columns)

    return working.groupby(
        ["product_id", "month", "unit_code"], as_index=False
    ).agg(
        days=("sale_date", "nunique"),
        unit_avg_sales=("quantity_zero_filled", "mean"),
        unit_avg_price=("effective_price", "mean"),
    )[columns]


# =========================================================
# ⑨ 瀑布法單一活動拆解（配對比對）
# =========================================================

WATERFALL_PAIRING_COLUMNS = [
    "activity_type",
    "product_id",
    "product_name",
    "target_unit",
    "month",
    "target_unit_days",
    "target_unit_corresponding_activities",
    "remainder_corresponding_activities",
    "candidate_units",
    "target_unit_avg_sales",
    "target_unit_avg_price",
    "candidate_weighted_avg_daily_revenue",
    "actual_daily_revenue",
    "net_gain_per_day",
    "net_gain_total",
    "split_status",
    "sample_size_note",
]


def build_waterfall_pairing_table(
    unit_overview: pd.DataFrame,
    quiet_period_units: pd.DataFrame,
    bundle_rules: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    對應工作表6「配對比對-單一活動拆解」。

    當扣掉活動X後的剩餘對應活動是空集合（即X是該單位
    唯一的活動），正確的對照組是同商品同月份的安靜期單位
    本身，這種情況一樣視為「可拆分」（因為只有一個活動，
    效果天生就是可分離的），候選對照組改查
    quiet_period_units 而非 unit_overview 本身
    （unit_overview 已排除安靜期單位）。

    bundle_rules（來自 detect_unconditional_bundles()）如果有
    提供，會在建立 activity_set 之後、進入逐一測試拆分之前，
    先把落在同一個已知不可分割組合窗口內的名稱合併成一個
    原子標籤——這樣同一個組合只會產生一列，不會對組合內每個
    子機制各自產生一列相同總額的重複列，也不會因為某個子
    機制名稱剛好在別處有巧合的對照組而被誤判成可拆分。
    傳 None 或空表時，行為與加這個參數之前完全相同。
    """

    if unit_overview.empty:
        return pd.DataFrame(columns=WATERFALL_PAIRING_COLUMNS)

    working = unit_overview.copy()

    working["activity_set"] = working[
        "corresponding_activities_label"
    ].apply(
        lambda label: frozenset(
            part for part in label.split("、") if part
        )
    )

    bundle_windows = _bundle_windows(bundle_rules)

    if bundle_windows:
        working["activity_set"] = working.apply(
            lambda row: collapse_activity_set_with_bundles(
                row["activity_set"],
                row["start_date"],
                bundle_windows,
            ),
            axis=1,
        )

    signature_lookup: dict[tuple, list[int]] = {}

    for index, row in working.iterrows():
        key = (row["product_id"], row["month"], row["activity_set"])
        signature_lookup.setdefault(key, []).append(index)

    quiet_lookup: dict[tuple, pd.DataFrame] = {}

    if not quiet_period_units.empty:
        for (product_id, month), group in quiet_period_units.groupby(
            ["product_id", "month"]
        ):
            quiet_lookup[(product_id, month)] = group

    records: list[dict[str, object]] = []

    for index, row in working.iterrows():
        activity_set = row["activity_set"]

        if not activity_set:
            continue

        for activity_type in sorted(activity_set):
            remainder = activity_set - {activity_type}

            sample_note_parts: list[str] = []

            if not remainder:
                # 唯一活動：對照組是同商品同月份的安靜期單位。
                candidates = quiet_lookup.get(
                    (row["product_id"], row["month"])
                )
            else:
                candidate_key = (
                    row["product_id"],
                    row["month"],
                    remainder,
                )
                candidate_indices = [
                    candidate_index
                    for candidate_index in signature_lookup.get(
                        candidate_key, []
                    )
                    if candidate_index != index
                ]
                candidates = (
                    working.loc[candidate_indices]
                    if candidate_indices
                    else None
                )

            if candidates is not None and not candidates.empty:
                total_days = candidates["days"].sum()

                weighted_avg_sales = (
                    candidates["unit_avg_sales"]
                    * candidates["days"]
                ).sum() / total_days

                weighted_avg_price = (
                    candidates["unit_avg_price"]
                    * candidates["days"]
                ).sum() / total_days

                expected_daily_revenue = (
                    weighted_avg_sales * weighted_avg_price
                )
                actual_daily_revenue = (
                    row["unit_avg_sales"] * row["unit_avg_price"]
                )
                net_gain_per_day = (
                    actual_daily_revenue - expected_daily_revenue
                )
                net_gain_total = net_gain_per_day * row["days"]
                split_status = "可拆分"

                candidate_label = "、".join(
                    f"{candidate_row.unit_code}"
                    f"({int(candidate_row.days)}天)"
                    for candidate_row in candidates.itertuples()
                )

                if row["days"] < 2:
                    sample_note_parts.append(
                        "目標單位樣本量小,信賴區間寬"
                    )

                if total_days < 2:
                    sample_note_parts.append(
                        "對照組樣本量小,信賴區間寬"
                    )

            else:
                expected_daily_revenue = pd.NA
                actual_daily_revenue = (
                    row["unit_avg_sales"] * row["unit_avg_price"]
                )
                net_gain_per_day = row[
                    "net_revenue_effect_per_day"
                ]
                net_gain_total = row["net_revenue_effect_total"]
                split_status = (
                    "無法拆分(以整體對應活動對安靜期估算)"
                )
                candidate_label = (
                    "(無同月同組合對照期,已對安靜期估算)"
                )

                if row["days"] < 2:
                    sample_note_parts.append(
                        "樣本量小,信賴區間寬"
                    )

            records.append(
                {
                    "activity_type": activity_type,
                    "product_id": row["product_id"],
                    "product_name": row["product_name"],
                    "target_unit": row["unit_code"],
                    "month": row["month"],
                    "target_unit_days": row["days"],
                    "target_unit_corresponding_activities": row[
                        "corresponding_activities_label"
                    ],
                    "remainder_corresponding_activities": (
                        "、".join(sorted(remainder))
                        if remainder
                        else "(無,即安靜期)"
                    ),
                    "candidate_units": candidate_label,
                    "target_unit_avg_sales": row["unit_avg_sales"],
                    "target_unit_avg_price": row["unit_avg_price"],
                    "candidate_weighted_avg_daily_revenue": (
                        expected_daily_revenue
                    ),
                    "actual_daily_revenue": actual_daily_revenue,
                    "net_gain_per_day": net_gain_per_day,
                    "net_gain_total": net_gain_total,
                    "split_status": split_status,
                    "sample_size_note": "、".join(
                        sample_note_parts
                    ),
                }
            )

    return pd.DataFrame(records, columns=WATERFALL_PAIRING_COLUMNS)


# =========================================================
# ⑩ 瀑布法彙總（配對比對-彙總）
# =========================================================

WATERFALL_SUMMARY_COLUMNS = [
    "activity_type",
    "split_status",
    "product_id",
    "corresponding_activities",
    "interval_count",
    "total_days",
    "total_gain",
]


def build_waterfall_summary(
    waterfall_pairing_table: pd.DataFrame,
) -> pd.DataFrame:
    """對應工作表7「配對比對-彙總」。"""

    if waterfall_pairing_table.empty:
        return pd.DataFrame(columns=WATERFALL_SUMMARY_COLUMNS)

    working = waterfall_pairing_table.copy()

    splittable = working[working["split_status"] == "可拆分"]
    unsplittable = working[working["split_status"] != "可拆分"]

    if not splittable.empty:
        splittable_summary = splittable.groupby(
            ["activity_type", "product_id"], as_index=False
        ).agg(
            interval_count=("target_unit", "count"),
            total_days=("target_unit_days", "sum"),
            total_gain=("net_gain_total", "sum"),
        )
        splittable_summary["split_status"] = "可拆分"
        # 可拆分列本來就是單一活動的獨立效果，直接顯示
        # activity_type，不再用佔位字。
        splittable_summary["corresponding_activities"] = (
            splittable_summary["activity_type"]
        )
    else:
        splittable_summary = pd.DataFrame(
            columns=WATERFALL_SUMMARY_COLUMNS
        )

    if not unsplittable.empty:
        # 同一個活動單位若因組合內多個活動類型都退回「整體對
        # 安靜期估算」，net_gain_total／target_unit_days 對該
        # 單位而言必然相同（退回估算時用的是整個單位的效應，
        # 跟哪個活動類型觸發退回無關）。先用
        # (product_id, target_unit) 去重，避免同一單位的營收
        # 被重複列在組合內每個活動類型底下、重複加總；再依
        # (product_id, 組合) 分組，確保同組合只會有一列、
        # 總營收不會因為各活動類型拆分成功與否的巧合而不一致。
        unsplittable_unique = unsplittable.drop_duplicates(
            subset=["product_id", "target_unit"]
        )

        unsplittable_summary = unsplittable_unique.groupby(
            [
                "product_id",
                "target_unit_corresponding_activities",
            ],
            as_index=False,
        ).agg(
            interval_count=("target_unit", "count"),
            total_days=("target_unit_days", "sum"),
            total_gain=("net_gain_total", "sum"),
        ).rename(
            columns={
                "target_unit_corresponding_activities": (
                    "corresponding_activities"
                )
            }
        )
        unsplittable_summary["split_status"] = "無法拆分"
        # 無法拆分本質上無法歸因到單一活動類型，activity_type
        # 欄位改顯示組合本身。
        unsplittable_summary["activity_type"] = (
            unsplittable_summary["corresponding_activities"]
        )
    else:
        unsplittable_summary = pd.DataFrame(
            columns=WATERFALL_SUMMARY_COLUMNS
        )

    combined = pd.concat(
        [
            splittable_summary[WATERFALL_SUMMARY_COLUMNS],
            unsplittable_summary[WATERFALL_SUMMARY_COLUMNS],
        ],
        ignore_index=True,
    )

    return combined.sort_values(
        ["activity_type", "split_status", "product_id"]
    ).reset_index(drop=True)


# =========================================================
# 總入口
# =========================================================

def run_activity_unit_analysis(
    sales_dataframe: pd.DataFrame,
    activity_standardized_dataframe: pd.DataFrame,
    activity_calendar_dataframe: pd.DataFrame,
    settings: ActivityUnitAnalysisSettings | None = None,
) -> ActivityUnitAnalysisResult:
    """依序執行①→⑩，組成完整的活動單位分析結果。"""

    if sales_dataframe is None or sales_dataframe.empty:
        raise ValueError("缺少標準化銷量資料。")

    if (
        activity_standardized_dataframe is None
        or activity_standardized_dataframe.empty
    ):
        raise ValueError("缺少商品活動資料。")

    if (
        activity_calendar_dataframe is None
        or activity_calendar_dataframe.empty
    ):
        raise ValueError("缺少活動日曆資料。")

    resolved_settings = settings or ActivityUnitAnalysisSettings()

    corresponding_activity_calendar = (
        build_corresponding_activity_calendar(
            activity_calendar_dataframe
        )
    )

    bundle_rules = detect_unconditional_bundles(
        activity_calendar_dataframe
    )

    bundle_date_mismatches = detect_bundle_date_mismatches(
        activity_calendar_dataframe
    )

    daily_price_panel = build_daily_sku_price_panel(
        sales_dataframe, activity_standardized_dataframe
    )

    daily_panel_with_calendar = assign_corresponding_activity(
        daily_price_panel, corresponding_activity_calendar
    )

    unit_timeline, date_to_unit_lookup = split_activity_units(
        daily_panel_with_calendar, resolved_settings
    )

    daily_panel_with_units = attach_unit_code(
        daily_panel_with_calendar, date_to_unit_lookup
    )

    unit_timeline_wide = pivot_unit_timeline_wide(
        unit_timeline, daily_panel_with_units
    )

    unit_price_table = build_unit_price_table(
        daily_panel_with_units
    )

    unit_overview = build_unit_overview_vs_baseline(
        daily_panel_with_units, resolved_settings, bundle_rules
    )

    quiet_period_units = build_quiet_period_reference_units(
        daily_panel_with_units
    )

    waterfall_pairing_table = build_waterfall_pairing_table(
        unit_overview, quiet_period_units, bundle_rules
    )

    waterfall_summary = build_waterfall_summary(
        waterfall_pairing_table
    )

    return ActivityUnitAnalysisResult(
        corresponding_activity_calendar=(
            corresponding_activity_calendar
        ),
        daily_price_panel=daily_panel_with_units,
        unit_timeline=unit_timeline,
        unit_timeline_wide=unit_timeline_wide,
        unit_price_table=unit_price_table,
        unit_overview=unit_overview,
        waterfall_pairing_table=waterfall_pairing_table,
        waterfall_summary=waterfall_summary,
        bundle_rules=bundle_rules,
        bundle_date_mismatches=bundle_date_mismatches,
    )
