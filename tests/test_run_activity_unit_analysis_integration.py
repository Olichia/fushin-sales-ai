from __future__ import annotations

import pandas as pd

from src.activity_unit_analysis import run_activity_unit_analysis


def _sales_rows() -> pd.DataFrame:
    """
    2026年3月1日-3月15日的銷量：3/8-3/12（女王節正式期間）
    銷量明顯高於其他安靜期天數，作為vs基準比較的基礎。
    """

    rows: list[dict[str, object]] = []

    for day in pd.date_range("2026-03-01", "2026-03-15", freq="D"):
        in_campaign = pd.Timestamp("2026-03-08") <= day <= pd.Timestamp(
            "2026-03-12"
        )

        rows.append(
            {
                "sale_date": day,
                "product_id": "191788",
                "product_name": "【品牌】高速調理機",
                "quantity": 12 if in_campaign else 5,
            }
        )

    return pd.DataFrame(rows)


def _activity_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_id": "191788",
                "product_name": "【品牌】高速調理機",
                "activity_start_date": "2026-03-08",
                "activity_end_date": "2026-03-12",
                "campaign_price": 7999,
                "activity_gift": "無",
                "bonus_gift_text": "無",
                "bonus_campaign_text": "8%平台幣",
                "product_category": "廚房家電",
            }
        ]
    )


def _calendar_rows() -> pd.DataFrame:
    """
    對應真實三月範本的「女王節」結構：檔期層有根活動
    「女王節」跟子階段「正式」，子階段合併後 effective_name
    為「女王節正式」；鋪底層兩個子機制「女王節送平台幣」
    「女王節原廠鋪底贈」跟「正式」日期完全一致，且名稱都
    包含根活動關鍵字「女王節」，應該被判定成不可分割組合。
    """

    return pd.DataFrame(
        [
            {
                "campaign_name": "女王節",
                "campaign_level": "平台檔期",
                "campaign_start_date": "2026-02-25",
                "campaign_end_date": "2026-03-12",
            },
            {
                "campaign_name": "正式",
                "campaign_level": "平台檔期",
                "campaign_start_date": "2026-03-08",
                "campaign_end_date": "2026-03-12",
            },
            {
                "campaign_name": "女王節送平台幣",
                "campaign_level": "品牌鋪底活動",
                "campaign_start_date": "2026-03-08",
                "campaign_end_date": "2026-03-12",
            },
            {
                "campaign_name": "女王節原廠鋪底贈",
                "campaign_level": "品牌鋪底活動",
                "campaign_start_date": "2026-03-08",
                "campaign_end_date": "2026-03-12",
            },
        ]
    )


def _unrelated_overlap_calendar_rows() -> pd.DataFrame:
    """
    刻意讓母活動「母親節」跟子活動「廚電日鋪底贈」日期完全
    相同、但名稱完全無關，驗證不會被誤判成同一組合。
    """

    return pd.DataFrame(
        [
            {
                "campaign_name": "母親節",
                "campaign_level": "平台檔期",
                "campaign_start_date": "2026-05-01",
                "campaign_end_date": "2026-05-10",
            },
            {
                "campaign_name": "廚電日鋪底贈",
                "campaign_level": "品牌鋪底活動",
                "campaign_start_date": "2026-05-01",
                "campaign_end_date": "2026-05-10",
            },
        ]
    )


class TestRunActivityUnitAnalysisIntegration:
    def test_same_period_sibling_activities_bundle_into_named_combo(
        self,
    ) -> None:
        """
        女王節正式＋女王節送平台幣＋女王節原廠鋪底贈三個標籤
        完全同期、名稱都含母活動關鍵字「女王節」，應該被判定
        成單一不可分割活動組合，classification 維持固定字串，
        但顯示用的活動名稱要被收合成「女王節正式組合」。
        """

        result = run_activity_unit_analysis(
            _sales_rows(), _activity_rows(), _calendar_rows()
        )

        assert not result.unit_overview.empty

        bundled_unit = result.unit_overview[
            result.unit_overview["corresponding_activities_label"]
            == "女王節正式組合"
        ]

        assert len(bundled_unit) == 1
        assert (
            bundled_unit.iloc[0]["classification"]
            == "不可分割活動組合"
        )

        bundled_unit_code = bundled_unit.iloc[0]["unit_code"]
        pairing_rows = result.waterfall_pairing_table[
            result.waterfall_pairing_table["target_unit"]
            == bundled_unit_code
        ]

        assert len(pairing_rows) == 1

    def test_coincidental_same_date_unrelated_campaigns_do_not_bundle(
        self,
    ) -> None:
        """
        母親節跟廚電日鋪底贈日期剛好完全重疊，但名稱互不相關，
        不應該被判定成同一個不可分割組合。
        """

        from src.activity_unit_analysis import (
            detect_unconditional_bundles,
        )

        bundle_rules = detect_unconditional_bundles(
            _unrelated_overlap_calendar_rows()
        )

        assert bundle_rules.empty
