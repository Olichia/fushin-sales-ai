import unittest

import pandas as pd

from src.clean_activities import (
    explode_promotion_periods,
    prepare_activity_dataframe,
)


class ActivityInputCompatibilityTests(unittest.TestCase):
    def test_explicit_date_columns_and_two_gifts_are_preserved(
        self,
    ) -> None:
        raw = pd.DataFrame(
            {
                "source_file": ["3月活動.xlsx"],
                "source_sheet": ["活動表"],
                "source_month": [3],
                "source_row_number": [2],
                "商品編號": [191788],
                "商品名稱": ["高速調理機"],
                "活動類型": ["限搶"],
                "起始日期": [pd.Timestamp("2026-03-20")],
                "結束日期": [pd.Timestamp("2026-03-20")],
                "售價(含稅)": [7_999],
                "活動贈品": ["小炒鍋"],
                "加碼贈品": ["平台幣"],
                "備註": ["加碼限搶"],
            }
        )

        prepared = prepare_activity_dataframe(raw)
        activities, issues = explode_promotion_periods(
            prepared
        )

        self.assertTrue(issues.empty)
        self.assertEqual(len(activities), 1)

        activity = activities.iloc[0]
        self.assertEqual(activity["product_id"], "191788")
        self.assertEqual(activity["activity_gift"], "小炒鍋")
        self.assertEqual(
            activity["bonus_gift_name"],
            "平台幣",
        )
        self.assertEqual(
            activity["activity_start_date"],
            pd.Timestamp("2026-03-20"),
        )
        self.assertEqual(
            activity["activity_end_date"],
            pd.Timestamp("2026-03-20"),
        )
        self.assertIn("限搶", activity["activity_tag"])


if __name__ == "__main__":
    unittest.main()
