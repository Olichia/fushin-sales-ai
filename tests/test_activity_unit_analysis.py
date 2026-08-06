from __future__ import annotations

import pandas as pd
import pytest

from src.activity_unit_analysis import (
    _prepare_schedule_and_other_level,
    build_corresponding_activity_calendar,
    build_waterfall_pairing_table,
    collapse_activity_set_with_bundles,
    detect_bundle_date_mismatches,
    detect_unconditional_bundles,
)


def _calendar_row(
    name: str,
    level: str,
    start: str,
    end: str,
) -> dict[str, object]:
    return {
        "campaign_name": name,
        "campaign_level": level,
        "campaign_start_date": start,
        "campaign_end_date": end,
    }


@pytest.fixture
def march_calendar() -> pd.DataFrame:
    """
    仿真三月檔期＋鋪底資料：女王節暖身/正式（各只出現一次，
    應合併成子階段複合名稱）、廚電日（同月出現4次，不應合併）、
    平台日（同月只出現一次，但找不到包住它的檔期，維持原名）、
    送平台幣／原廠鋪底贈（鋪底層，落在女王節正式區間內）。
    """

    rows = [
        _calendar_row("女王節", "平台檔期", "2026-02-25", "2026-03-12"),
        _calendar_row("暖身", "平台檔期", "2026-03-01", "2026-03-07"),
        _calendar_row("正式", "平台檔期", "2026-03-08", "2026-03-12"),
        _calendar_row("廚電日", "平台檔期", "2026-03-06", "2026-03-08"),
        _calendar_row("廚電日", "平台檔期", "2026-03-13", "2026-03-14"),
        _calendar_row("廚電日", "平台檔期", "2026-03-19", "2026-03-20"),
        _calendar_row("廚電日", "平台檔期", "2026-03-25", "2026-03-26"),
        _calendar_row("平台日", "平台檔期", "2026-03-18", "2026-03-26"),
        _calendar_row(
            "女王節送平台幣",
            "品牌鋪底活動",
            "2026-03-08",
            "2026-03-12",
        ),
        _calendar_row(
            "女王節原廠鋪底贈",
            "品牌鋪底活動",
            "2026-03-08",
            "2026-03-12",
        ),
    ]

    return pd.DataFrame(rows)


@pytest.fixture
def brand_day_calendar() -> pd.DataFrame:
    """
    仿真4月「品牌日」（4/20單日，5個子機制全部只在當天生效，
    名稱都以「品牌日-」開頭）與「品牌週」（4/21-4/25，3個子
    機制，名稱都以「品牌週-」開頭，機制類型跟品牌日重複但
    各自有自己的關鍵字前綴）、以及「平台日」「廚電日」兩個
    真正獨立、本身就是檔期層、只是剛好跟品牌日同一天重疊的
    活動——這兩者不應該被誤判成品牌日的子機制。
    """

    rows = [
        _calendar_row("品牌日", "平台檔期", "2026-04-20", "2026-04-20"),
        _calendar_row("品牌週", "平台檔期", "2026-04-21", "2026-04-25"),
        # 平台日／廚電日在真實資料裡同月會重複出現多次
        # （例如三月的廚電日就出現4次），這裡各放兩筆，
        # 確保它們不會被既有的子階段合併邏輯（只對「同月僅
        # 出現一次」的檔期名稱生效）誤判成品牌日的子階段，
        # 讓這個 fixture 乾淨地只測試「檔期層一律不會被
        # 判定成鋪底層子機制」這件事本身。
        _calendar_row("平台日", "平台檔期", "2026-04-18", "2026-04-19"),
        _calendar_row("平台日", "平台檔期", "2026-04-20", "2026-04-20"),
        _calendar_row("廚電日", "平台檔期", "2026-04-13", "2026-04-14"),
        _calendar_row("廚電日", "平台檔期", "2026-04-20", "2026-04-20"),
        _calendar_row(
            "品牌日-登記送平台幣",
            "品牌鋪底活動",
            "2026-04-20",
            "2026-04-20",
        ),
        _calendar_row(
            "品牌日-原廠鋪底贈",
            "品牌鋪底活動",
            "2026-04-20",
            "2026-04-20",
        ),
        _calendar_row(
            "品牌日-下單抽",
            "品牌鋪底活動",
            "2026-04-20",
            "2026-04-20",
        ),
        _calendar_row(
            "品牌日-夜貓加碼",
            "品牌鋪底活動",
            "2026-04-20",
            "2026-04-20",
        ),
        _calendar_row(
            "品牌日-限量折價券",
            "品牌鋪底活動",
            "2026-04-20",
            "2026-04-20",
        ),
        _calendar_row(
            "品牌週-登記送平台幣",
            "品牌鋪底活動",
            "2026-04-21",
            "2026-04-25",
        ),
        _calendar_row(
            "品牌週-原廠鋪底贈",
            "品牌鋪底活動",
            "2026-04-21",
            "2026-04-25",
        ),
        _calendar_row(
            "品牌週-下單抽",
            "品牌鋪底活動",
            "2026-04-21",
            "2026-04-25",
        ),
    ]

    return pd.DataFrame(rows)


class TestPrepareScheduleAndOtherLevel:
    def test_matches_build_corresponding_activity_calendar_labels(
        self, march_calendar: pd.DataFrame
    ) -> None:
        """
        回歸測試：抽出 _prepare_schedule_and_other_level() 這個
        私有函式之後，build_corresponding_activity_calendar() 的
        每日標籤輸出必須跟抽出前完全一致。這裡不比較「抽出前」
        的舊程式碼（已不存在），而是直接驗證抽出後的行為符合
        方法論文件描述的預期結果，作為這個純重構的行為基準。
        """

        result = build_corresponding_activity_calendar(march_calendar)
        by_date = result.set_index("sale_date")[
            "corresponding_activities_label"
        ]

        assert by_date[pd.Timestamp("2026-02-26")] == "女王節"
        assert by_date[pd.Timestamp("2026-03-02")] == "女王節暖身"
        assert (
            by_date[pd.Timestamp("2026-03-06")]
            == "女王節暖身、廚電日"
        )
        assert (
            by_date[pd.Timestamp("2026-03-09")]
            == "女王節原廠鋪底贈、女王節正式、女王節送平台幣"
        )
        assert (
            by_date[pd.Timestamp("2026-03-20")] == "平台日、廚電日"
        )

    def test_repeated_name_in_same_month_not_merged(
        self, march_calendar: pd.DataFrame
    ) -> None:
        schedule_level, _, _ = _prepare_schedule_and_other_level(
            march_calendar
        )

        kitchen_day_rows = schedule_level[
            schedule_level["campaign_name"] == "廚電日"
        ]

        assert (
            kitchen_day_rows["effective_name"] == "廚電日"
        ).all()

    def test_single_occurrence_without_containing_parent_unchanged(
        self, march_calendar: pd.DataFrame
    ) -> None:
        schedule_level, _, _ = _prepare_schedule_and_other_level(
            march_calendar
        )

        platform_day_row = schedule_level[
            schedule_level["campaign_name"] == "平台日"
        ].iloc[0]

        assert platform_day_row["effective_name"] == "平台日"

    def test_empty_calendar_returns_empty_frames(self) -> None:
        schedule_level, other_level, suppress_ranges = (
            _prepare_schedule_and_other_level(
                pd.DataFrame(
                    columns=[
                        "campaign_name",
                        "campaign_level",
                        "campaign_start_date",
                        "campaign_end_date",
                    ]
                )
            )
        )

        assert schedule_level.empty
        assert other_level.empty
        assert suppress_ranges == []


class TestBaselineDatePriority:
    """
    對應真實範本發現的情況：「平台日」在檔期表是 3/19-3/22，
    但鋪底表自己也有一列「平台日」（滿額登記送平台幣機制），
    日期是 3/18-3/26——鋪底日期才是真正有實際優惠、可以算
    增益的期間，應該取代檔期表的概略日期。
    """

    @pytest.fixture
    def platform_day_calendar(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                _calendar_row(
                    "平台日", "平台檔期", "2026-03-19", "2026-03-22"
                ),
                _calendar_row(
                    "平台日", "品牌鋪底活動", "2026-03-18", "2026-03-26"
                ),
                _calendar_row(
                    "平台日原廠鋪底贈",
                    "品牌鋪底活動",
                    "2026-03-18",
                    "2026-03-26",
                ),
            ]
        )

    def test_schedule_date_is_overridden_by_baseline_self_entry(
        self, platform_day_calendar: pd.DataFrame
    ) -> None:
        schedule_level, _, _ = _prepare_schedule_and_other_level(
            platform_day_calendar
        )

        platform_day_row = schedule_level[
            schedule_level["campaign_name"] == "平台日"
        ].iloc[0]

        assert platform_day_row[
            "campaign_start_date"
        ] == pd.Timestamp("2026-03-18")
        assert platform_day_row[
            "campaign_end_date"
        ] == pd.Timestamp("2026-03-26")

    def test_baseline_date_priority_enables_bundle_detection(
        self, platform_day_calendar: pd.DataFrame
    ) -> None:
        """
        日期校正後，「平台日」跟「平台日原廠鋪底贈」的日期
        變成完全一致，應該被正式判定成不可分割組合。
        """

        bundles = detect_unconditional_bundles(
            platform_day_calendar
        )

        platform_bundle = bundles[
            bundles["mother_name"] == "平台日"
        ]

        assert "平台日原廠鋪底贈" in set(
            platform_bundle["child_name"]
        )

    def test_schedule_only_activity_keeps_its_own_date(
        self, march_calendar: pd.DataFrame
    ) -> None:
        """
        「檔期有、鋪底完全沒有對應列」的活動（如廚電日）
        維持原本檔期日期，不受這個規則影響。
        """

        schedule_level, _, _ = _prepare_schedule_and_other_level(
            march_calendar
        )

        kitchen_day_row = schedule_level[
            schedule_level["campaign_name"] == "廚電日"
        ].iloc[0]

        assert kitchen_day_row[
            "campaign_start_date"
        ] == pd.Timestamp("2026-03-06")
        assert kitchen_day_row[
            "campaign_end_date"
        ] == pd.Timestamp("2026-03-08")

    def test_same_name_different_months_are_not_conflated(
        self,
    ) -> None:
        """
        「平台日」在三月跟四月各自出現一次（檔期跟鋪底都是），
        日期校正必須各自比對同月份的鋪底列，不能把兩個月份的
        鋪底日期取 min/max 合併成橫跨兩個月的荒謬區間。
        """

        calendar = pd.DataFrame(
            [
                _calendar_row(
                    "平台日", "平台檔期", "2026-03-19", "2026-03-22"
                ),
                _calendar_row(
                    "平台日", "品牌鋪底活動", "2026-03-18", "2026-03-26"
                ),
                _calendar_row(
                    "平台日", "平台檔期", "2026-04-19", "2026-04-22"
                ),
                _calendar_row(
                    "平台日", "品牌鋪底活動", "2026-04-18", "2026-04-19"
                ),
            ]
        )

        schedule_level, _, _ = _prepare_schedule_and_other_level(
            calendar
        )

        march_row = schedule_level[
            schedule_level["campaign_start_date"].dt.month == 3
        ].iloc[0]
        april_row = schedule_level[
            schedule_level["campaign_start_date"].dt.month == 4
        ].iloc[0]

        assert march_row["campaign_start_date"] == pd.Timestamp(
            "2026-03-18"
        )
        assert march_row["campaign_end_date"] == pd.Timestamp(
            "2026-03-26"
        )
        assert april_row["campaign_start_date"] == pd.Timestamp(
            "2026-04-18"
        )
        assert april_row["campaign_end_date"] == pd.Timestamp(
            "2026-04-19"
        )


class TestDetectUnconditionalBundles:
    def test_brand_day_five_mechanisms_bundle_together(
        self, brand_day_calendar: pd.DataFrame
    ) -> None:
        bundles = detect_unconditional_bundles(brand_day_calendar)

        brand_day_bundle = bundles[bundles["mother_name"] == "品牌日"]

        assert set(brand_day_bundle["child_name"]) == {
            "品牌日-登記送平台幣",
            "品牌日-原廠鋪底贈",
            "品牌日-下單抽",
            "品牌日-夜貓加碼",
            "品牌日-限量折價券",
        }

    def test_brand_week_is_a_separate_bundle_from_brand_day(
        self, brand_day_calendar: pd.DataFrame
    ) -> None:
        bundles = detect_unconditional_bundles(brand_day_calendar)

        brand_week_bundle = bundles[
            bundles["mother_name"] == "品牌週"
        ]

        assert set(brand_week_bundle["child_name"]) == {
            "品牌週-登記送平台幣",
            "品牌週-原廠鋪底贈",
            "品牌週-下單抽",
        }
        assert (
            brand_week_bundle["mother_start_date"].iloc[0]
            == pd.Timestamp("2026-04-21")
        )

    def test_overlapping_independent_campaigns_never_become_children(
        self, brand_day_calendar: pd.DataFrame
    ) -> None:
        bundles = detect_unconditional_bundles(brand_day_calendar)

        assert "平台日" not in set(bundles["child_name"])
        assert "廚電日" not in set(bundles["child_name"])

    def test_recurring_child_name_scoped_to_its_own_mother_window(
        self, march_calendar: pd.DataFrame
    ) -> None:
        """
        送平台幣／原廠鋪底贈這類名稱在不同母活動下重複出現時，
        每次出現要各自依自己的日期區間判斷歸屬，這裡只放了
        女王節正式一個窗口，驗證判斷結果精準落在那個窗口，
        不會誤判成涵蓋整個女王節或其他區間。
        """

        bundles = detect_unconditional_bundles(march_calendar)

        queen_bundle = bundles[
            bundles["mother_name"] == "女王節正式"
        ]

        assert set(queen_bundle["child_name"]) == {
            "女王節送平台幣",
            "女王節原廠鋪底贈",
        }
        assert (
            queen_bundle["child_start_date"].iloc[0]
            == pd.Timestamp("2026-03-08")
        )

    def test_partial_overlap_not_contained_stays_unbundled(
        self,
    ) -> None:
        calendar = pd.DataFrame(
            [
                _calendar_row(
                    "品牌日", "平台檔期", "2026-04-20", "2026-04-20"
                ),
                _calendar_row(
                    "品牌日跨日加碼",
                    "品牌鋪底活動",
                    "2026-04-19",
                    "2026-04-21",
                ),
            ]
        )

        bundles = detect_unconditional_bundles(calendar)

        assert bundles.empty

    def test_exact_date_match_without_keyword_stays_unbundled(
        self,
    ) -> None:
        """
        母親節檔期跟廚電日鋪底贈剛好日期完全重疊，但名稱互不
        相關，不應該被誤判成同一個不可分割組合——日期完全
        一致只是必要條件之一，還要子活動名稱包含母活動關鍵字
        才算數。
        """

        calendar = pd.DataFrame(
            [
                _calendar_row(
                    "母親節", "平台檔期", "2026-05-01", "2026-05-10"
                ),
                _calendar_row(
                    "廚電日鋪底贈",
                    "品牌鋪底活動",
                    "2026-05-01",
                    "2026-05-10",
                ),
            ]
        )

        bundles = detect_unconditional_bundles(calendar)

        assert bundles.empty

    def test_empty_calendar_returns_empty_bundle_table(self) -> None:
        bundles = detect_unconditional_bundles(
            pd.DataFrame(
                columns=[
                    "campaign_name",
                    "campaign_level",
                    "campaign_start_date",
                    "campaign_end_date",
                ]
            )
        )

        assert bundles.empty


class TestDetectBundleDateMismatches:
    def test_keyword_match_with_overlapping_but_unequal_dates_is_flagged(
        self,
    ) -> None:
        """
        對應真實四月範本的「平台日」情況：檔期「平台日」
        3/19-3/22，鋪底「平台日原廠鋪底贈」3/18-3/26，名稱
        明顯相關（都含「平台日」）、日期也有重疊，但不完全
        一致——不會被 detect_unconditional_bundles() 合併，
        但應該被標註成提醒。
        """

        calendar = pd.DataFrame(
            [
                _calendar_row(
                    "平台日", "平台檔期", "2026-03-19", "2026-03-22"
                ),
                _calendar_row(
                    "平台日原廠鋪底贈",
                    "品牌鋪底活動",
                    "2026-03-18",
                    "2026-03-26",
                ),
            ]
        )

        mismatches = detect_bundle_date_mismatches(calendar)

        assert len(mismatches) == 1
        row = mismatches.iloc[0]
        assert row["mother_name"] == "平台日"
        assert row["child_name"] == "平台日原廠鋪底贈"
        assert row["issue_type"] == "活動組合關鍵字相符但日期未完全對齊"

        # 這種情況不應該同時出現在正式的 bundle_rules 裡。
        bundles = detect_unconditional_bundles(calendar)
        assert bundles.empty

    def test_exact_date_match_is_not_flagged(
        self, march_calendar: pd.DataFrame
    ) -> None:
        """
        日期完全一致的女王節正式組合已經被正式合併，
        不應該再被標註成日期不一致的提醒。
        """

        mismatches = detect_bundle_date_mismatches(march_calendar)

        assert not (
            (mismatches["mother_name"] == "女王節正式")
            & (mismatches["child_name"] == "女王節送平台幣")
        ).any()

    def test_no_date_overlap_is_not_flagged(self) -> None:
        """
        名稱剛好用到相同關鍵字，但日期完全不重疊（不同時間點），
        比較像是巧合而非填寫落差，不應該被標註。
        """

        calendar = pd.DataFrame(
            [
                _calendar_row(
                    "平台日", "平台檔期", "2026-03-19", "2026-03-22"
                ),
                _calendar_row(
                    "平台日鋪底贈",
                    "品牌鋪底活動",
                    "2026-04-01",
                    "2026-04-05",
                ),
            ]
        )

        mismatches = detect_bundle_date_mismatches(calendar)

        assert mismatches.empty

    def test_no_keyword_match_is_not_flagged(self) -> None:
        """
        日期重疊但名稱完全無關，不應該被標註
        （避免母親節／廚電日這種巧合重疊被誤標）。
        """

        calendar = pd.DataFrame(
            [
                _calendar_row(
                    "母親節", "平台檔期", "2026-05-01", "2026-05-10"
                ),
                _calendar_row(
                    "廚電日鋪底贈",
                    "品牌鋪底活動",
                    "2026-05-03",
                    "2026-05-08",
                ),
            ]
        )

        mismatches = detect_bundle_date_mismatches(calendar)

        assert mismatches.empty

    def test_empty_calendar_returns_empty_frame(self) -> None:
        mismatches = detect_bundle_date_mismatches(
            pd.DataFrame(
                columns=[
                    "campaign_name",
                    "campaign_level",
                    "campaign_start_date",
                    "campaign_end_date",
                ]
            )
        )

        assert mismatches.empty


class TestCollapseActivitySetWithBundles:
    def test_bundle_members_collapse_into_one_atomic_token(
        self, brand_day_calendar: pd.DataFrame
    ) -> None:
        """
        收合後要用「{母活動名稱}組合」命名，當成單一活動名稱
        使用，不再逐一把被合併的子機制名稱串接起來顯示。
        """

        bundles = detect_unconditional_bundles(brand_day_calendar)

        activity_set = frozenset(
            {
                "品牌日",
                "品牌日-登記送平台幣",
                "品牌日-原廠鋪底贈",
                "品牌日-下單抽",
                "品牌日-夜貓加碼",
                "品牌日-限量折價券",
                "平台日",
                "廚電日",
            }
        )

        collapsed = collapse_activity_set_with_bundles(
            activity_set, pd.Timestamp("2026-04-20"), bundles
        )

        assert collapsed == frozenset(
            {"平台日", "廚電日", "品牌日組合"}
        )

    def test_unrelated_tag_outside_any_window_passes_through(
        self, brand_day_calendar: pd.DataFrame
    ) -> None:
        bundles = detect_unconditional_bundles(brand_day_calendar)

        collapsed = collapse_activity_set_with_bundles(
            frozenset({"某個不相干活動"}),
            pd.Timestamp("2026-04-20"),
            bundles,
        )

        assert collapsed == frozenset({"某個不相干活動"})

    def test_no_bundle_rules_is_a_no_op(self) -> None:
        activity_set = frozenset({"品牌日", "廚電日"})

        collapsed = collapse_activity_set_with_bundles(
            activity_set,
            pd.Timestamp("2026-04-20"),
            pd.DataFrame(
                columns=[
                    "mother_name",
                    "mother_start_date",
                    "mother_end_date",
                    "child_name",
                    "child_start_date",
                    "child_end_date",
                ]
            ),
        )

        assert collapsed == activity_set


class TestBuildWaterfallPairingTableWithBundles:
    def _unit_overview_row(
        self,
        *,
        product_id: str,
        unit_code: str,
        month: int,
        start_date: str,
        days: int,
        label: str,
        unit_avg_sales: float,
        unit_avg_price: float,
        net_revenue_effect_per_day: float,
    ) -> dict[str, object]:
        return {
            "product_id": product_id,
            "product_name": product_id,
            "unit_code": unit_code,
            "month": month,
            "start_date": pd.Timestamp(start_date),
            "days": days,
            "corresponding_activities_label": label,
            "unit_avg_sales": unit_avg_sales,
            "unit_avg_price": unit_avg_price,
            "net_revenue_effect_per_day": net_revenue_effect_per_day,
            "net_revenue_effect_total": (
                net_revenue_effect_per_day * days
            ),
        }

    def test_bundled_unit_produces_a_single_row_not_one_per_mechanism(
        self, brand_day_calendar: pd.DataFrame
    ) -> None:
        bundles = detect_unconditional_bundles(brand_day_calendar)

        bundled_label = (
            "品牌日、品牌日-原廠鋪底贈、品牌日-夜貓加碼、"
            "品牌日-下單抽、品牌日-限量折價券、品牌日-登記送平台幣"
        )

        unit_overview = pd.DataFrame(
            [
                self._unit_overview_row(
                    product_id="191788",
                    unit_code="A10",
                    month=4,
                    start_date="2026-04-20",
                    days=1,
                    label=bundled_label,
                    unit_avg_sales=168,
                    unit_avg_price=7999,
                    net_revenue_effect_per_day=1678320,
                )
            ]
        )

        quiet_period_units = pd.DataFrame(
            columns=[
                "product_id",
                "month",
                "days",
                "unit_avg_sales",
                "unit_avg_price",
                "unit_code",
            ]
        )

        pairing_no_bundle = build_waterfall_pairing_table(
            unit_overview, quiet_period_units
        )
        pairing_with_bundle = build_waterfall_pairing_table(
            unit_overview, quiet_period_units, bundles
        )

        assert len(pairing_no_bundle) == 6
        assert len(pairing_with_bundle) == 1
        assert (
            pairing_with_bundle.iloc[0]["net_gain_total"] == 1678320
        )

    def test_bundle_rules_do_not_affect_non_bundled_units(
        self, brand_day_calendar: pd.DataFrame
    ) -> None:
        bundles = detect_unconditional_bundles(brand_day_calendar)

        unit_overview = pd.DataFrame(
            [
                self._unit_overview_row(
                    product_id="191788",
                    unit_code="M7",
                    month=3,
                    start_date="2026-03-13",
                    days=2,
                    label="全站活動、廚電日",
                    unit_avg_sales=0,
                    unit_avg_price=8990,
                    net_revenue_effect_per_day=-71920,
                )
            ]
        )

        quiet_period_units = pd.DataFrame(
            columns=[
                "product_id",
                "month",
                "days",
                "unit_avg_sales",
                "unit_avg_price",
                "unit_code",
            ]
        )

        pairing_no_bundle = build_waterfall_pairing_table(
            unit_overview, quiet_period_units
        )
        pairing_with_bundle = build_waterfall_pairing_table(
            unit_overview, quiet_period_units, bundles
        )

        assert len(pairing_no_bundle) == len(pairing_with_bundle) == 2
