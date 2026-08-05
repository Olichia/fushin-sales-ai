import unittest

import pandas as pd

from src.analysis_pipeline import (
    AnalysisSettings,
    coerce_arrow_strings_to_object,
    generate_strategy_report,
    safe_unique_text_list,
)


class StrategyRecommendationTests(unittest.TestCase):
    def setUp(self) -> None:
        common = {
            "activity_start_date": pd.Timestamp("2026-03-12"),
            "activity_end_date": pd.Timestamp("2026-03-17"),
            "activity_days": 6,
            "campaign_price": 1_000,
            "baseline_average_daily_sales": 10,
            "campaign_average_daily_sales": 15,
            "post_average_daily_sales": 11,
            "post_change_rate": -0.27,
            "estimated_revenue": 90_000,
            "all_periods_complete": True,
            "baseline_complete": True,
            "campaign_complete": True,
            "post_complete": True,
            "overlapping_campaigns": None,
            "overlapping_benefits": None,
            "data_confidence": "較高",
            "activity_tag": None,
            "activity_gift": None,
        }

        rows = [
            {
                **common,
                "product_id": "A",
                "product_name": "高效調理機",
                "uplift_rate": 0.50,
                "campaign_total_sales": 90,
            },
            {
                **common,
                "product_id": "B",
                "product_name": "穩定果汁機",
                "uplift_rate": 0.10,
                "campaign_total_sales": 66,
                "campaign_average_daily_sales": 11,
            },
            {
                **common,
                "product_id": "C",
                "product_name": "待檢討電子鍋",
                "uplift_rate": -0.20,
                "campaign_total_sales": 48,
                "campaign_average_daily_sales": 8,
                "post_average_daily_sales": 12,
            },
            {
                **common,
                "product_id": "D",
                "product_name": "小量測試品",
                "uplift_rate": 0.60,
                "campaign_total_sales": 5,
                "campaign_average_daily_sales": 0.83,
            },
        ]

        self.performance = pd.DataFrame(rows)
        self.settings = AnalysisSettings(
            high_uplift_threshold=0.20,
            low_uplift_threshold=0.0,
            minimum_campaign_sales=10,
        )

    def test_three_categories_cover_every_valid_activity(self) -> None:
        strategy, _ = generate_strategy_report(
            self.performance,
            self.settings,
        )

        self.assertEqual(len(strategy), 4)
        self.assertEqual(
            strategy["策略分類"].value_counts().to_dict(),
            {
                "建議優化": 2,
                "建議延續": 1,
                "建議檢討": 1,
            },
        )

        low_volume_high_uplift = strategy[
            strategy["商品活動"].str.startswith("D｜")
        ].iloc[0]
        self.assertEqual(
            low_volume_high_uplift["策略分類"],
            "建議優化",
        )
        self.assertIn(
            "總銷量未達最低規模",
            low_volume_high_uplift["判斷依據"],
        )

    def test_recommendations_are_activity_specific(self) -> None:
        strategy, _ = generate_strategy_report(
            self.performance,
            self.settings,
        )

        self.assertEqual(strategy["建議"].nunique(), 4)

        for _, row in strategy.iterrows():
            product_name = row["商品活動"].split("｜")[1]
            self.assertIn(product_name, row["建議"])
            self.assertIn("【績效診斷】", row["建議"])
            self.assertIn("【建議決策】", row["建議"])
            self.assertIn("【下一檔執行】", row["建議"])
            self.assertIn("【驗證方式】", row["建議"])
            self.assertIn(
                "白色情人節",
                row["可能影響檔期／活動"],
            )
            self.assertIn("關聯性推估", row["檔期／歸因判讀"])
            self.assertEqual(
                row["資料完整度"],
                "完整（活動前、中、後皆齊）",
            )

    def test_operator_metrics_are_calculated(self) -> None:
        strategy, _ = generate_strategy_report(
            self.performance,
            self.settings,
        )

        continue_row = strategy[
            strategy["策略分類"] == "建議延續"
        ].iloc[0]

        self.assertAlmostEqual(
            continue_row["活動增量銷量"],
            30.0,
        )
        self.assertAlmostEqual(
            continue_row["推估增量營收"],
            30_000.0,
        )
        self.assertAlmostEqual(
            continue_row["活動後銷量延續率"],
            11 / 15,
        )

    def test_excel_campaign_names_take_priority_over_date_guess(self) -> None:
        performance = self.performance.iloc[[0]].copy()
        performance.loc[:, "overlapping_campaigns"] = (
            "平台日、廚電日"
        )
        performance.loc[:, "overlapping_benefits"] = "滿額贈"

        strategy, _ = generate_strategy_report(
            performance,
            self.settings,
        )

        row = strategy.iloc[0]
        self.assertEqual(row["檔期判讀來源"], "活動 Excel")
        self.assertIn("平台日", row["可能影響檔期／活動"])
        self.assertIn("廚電日", row["可能影響檔期／活動"])
        self.assertNotIn("白色情人節", row["可能影響檔期／活動"])
        self.assertIn("活動 Excel 顯示", row["檔期／歸因判讀"])

    def test_incomplete_activity_is_kept_with_missing_reason(self) -> None:
        incomplete = self.performance.iloc[[0]].copy()
        incomplete.loc[:, "product_id"] = "E"
        incomplete.loc[:, "product_name"] = "待補資料商品"
        incomplete.loc[:, "all_periods_complete"] = False
        incomplete.loc[:, "baseline_complete"] = False
        incomplete.loc[:, "campaign_complete"] = True
        incomplete.loc[:, "post_complete"] = True
        incomplete.loc[:, "baseline_start_date"] = pd.Timestamp(
            "2026-03-05"
        )
        incomplete.loc[:, "baseline_end_date"] = pd.Timestamp(
            "2026-03-11"
        )
        incomplete.loc[:, "post_start_date"] = pd.Timestamp(
            "2026-03-18"
        )
        incomplete.loc[:, "post_end_date"] = pd.Timestamp(
            "2026-03-24"
        )

        combined = pd.concat(
            [self.performance, incomplete],
            ignore_index=True,
        )
        strategy, report = generate_strategy_report(
            combined,
            self.settings,
        )

        self.assertEqual(len(strategy), 5)
        row = strategy[
            strategy["商品活動"].str.startswith("E｜")
        ].iloc[0]
        self.assertEqual(
            row["策略分類"],
            "資料不足／待補資料",
        )
        self.assertEqual(
            row["資料完整度"],
            "部分（活動期完整，前或後缺漏）",
        )
        self.assertIn("活動前基準", row["資料缺漏說明"])
        self.assertIn("2026-03-05", row["資料缺漏說明"])
        self.assertTrue(pd.isna(row["活動增量銷量"]))
        self.assertIn("資料不足／待補資料：1 筆", report)

    def test_invalid_threshold_order_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "高成效提升率門檻必須大於",
        ):
            generate_strategy_report(
                self.performance,
                AnalysisSettings(
                    high_uplift_threshold=0.0,
                    low_uplift_threshold=0.0,
                ),
            )

    def test_arrow_strings_are_deduplicated_without_arrow_unique(self) -> None:
        values = pd.Series(
            ["建議延續", "建議延續", None, "建議檢討"],
            dtype="string[pyarrow]",
        )

        self.assertEqual(
            safe_unique_text_list(values),
            ["建議延續", "建議檢討"],
        )

    def test_arrow_columns_and_values_are_converted_to_object(self) -> None:
        dataframe = pd.DataFrame(
            [["A", "活動"]],
            columns=pd.Index(
                ["product_id", "activity_tag"],
                dtype="string[pyarrow]",
            ),
        ).astype("string[pyarrow]")

        converted = coerce_arrow_strings_to_object(dataframe)

        self.assertEqual(converted.columns.dtype, object)
        self.assertEqual(converted["product_id"].dtype, object)
        self.assertEqual(converted["activity_tag"].dtype, object)


if __name__ == "__main__":
    unittest.main()
