import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.clean_activities import (
    explode_promotion_periods,
    prepare_activity_dataframe,
)
from src.clean_other_activities import (
    parse_march_product_gifts,
)


class ActivityInputCompatibilityTests(unittest.TestCase):
    def test_explicit_date_aliases_and_gifts_are_preserved(
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

    def test_two_column_march_gift_sheet_is_accepted(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "3月活動.xlsx"
            dataframe = pd.DataFrame(
                {
                    "商品編號": [191788],
                    "贈品": ["即享券"],
                }
            )
            dataframe.to_excel(
                file_path,
                sheet_name="0308-0312滿額贈即享券",
                index=False,
                engine="openpyxl",
            )

            benefits, issues = parse_march_product_gifts(
                file_path
            )

        self.assertEqual(len(benefits), 1)
        self.assertFalse(issues)
        self.assertIsNone(benefits[0]["activity_price"])


if __name__ == "__main__":
    unittest.main()
