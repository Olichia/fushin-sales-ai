import unittest

import pandas as pd

from src.ai_strategy_center import (
    build_decision_queue,
    build_executive_brief,
    build_next_period_plan,
    prepare_ai_strategy_data,
)


class AiStrategyCenterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = pd.DataFrame(
            {
                "product_id": ["A", "B", "C", "D"],
                "product_name": ["風險品", "觀察品", "機會品", "明星品"],
                "unit_code": ["U1", "U2", "U3", "U4"],
                "corresponding_activities_label": [
                    "深折扣",
                    "短促",
                    "贈品",
                    "品牌日",
                ],
                "classification": ["單一活動"] * 4,
                "unit_avg_sales": [10, 10, 12, 20],
                "baseline_avg_sales": [12, 10, 10, 10],
                "baseline_price": [1000, 1000, 1000, 1000],
                "unit_avg_price": [700, 1000, 950, 950],
                "sales_increment": [-2, 0, 2, 10],
                "volume_effect_per_day": [50, 0, 30, 150],
                "price_effect_per_day": [-150, 0, -10, -50],
                "net_revenue_effect_per_day": [-100, 0, 20, 100],
                "net_revenue_effect_total": [-300, 0, 60, 300],
                "days": [3, 3, 3, 3],
                "month": [3, 3, 3, 3],
                "sample_size_note": ["", "", "", ""],
                "proxy_price_note": ["", "", "", ""],
            }
        )
        self.strategy = prepare_ai_strategy_data(self.raw)

    def test_prepare_data_uses_existing_strategy_rules(self) -> None:
        categories = dict(
            zip(
                self.strategy["product_name"],
                self.strategy["strategy_category"],
            )
        )

        self.assertEqual(categories["風險品"], "建議檢討")
        self.assertEqual(categories["觀察品"], "持續觀察")
        self.assertEqual(categories["明星品"], "建議延續")
        self.assertTrue(bool(self.strategy.iloc[0]["is_risky"]))

    def test_decision_queue_contains_traceable_evidence(self) -> None:
        queue = build_decision_queue(self.strategy, limit=4)

        self.assertEqual(len(queue), 4)
        self.assertEqual(queue[0]["product_name"], "風險品")
        self.assertIn("淨增益/日 -100", queue[0]["evidence"])
        self.assertIn("商品編號 A", queue[0]["prompt"])

    def test_brief_prioritizes_risk_without_fabricated_metrics(self) -> None:
        brief = build_executive_brief(self.strategy)

        self.assertEqual(brief["tone"], "risk")
        self.assertIn("風險品", brief["finding"])
        self.assertIn("-100", brief["evidence"])

    def test_next_period_plan_uses_current_counts(self) -> None:
        plan = build_next_period_plan(self.strategy)

        self.assertEqual(len(plan), 3)
        self.assertIn("2 個", plan[0]["description"])
        self.assertIn("1 個", plan[2]["description"])


if __name__ == "__main__":
    unittest.main()
