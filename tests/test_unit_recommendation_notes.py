import unittest

import pandas as pd

from src.unit_recommendation_notes import (
    build_unit_attribution_note,
    build_unit_history_note,
    build_unit_mechanism_plan,
    build_unit_personalized_recommendation,
    build_unit_personalized_recommendation_sections,
    format_signed_currency,
)


class FormatSignedCurrencyTests(unittest.TestCase):
    def test_positive_value_has_plus_sign(self) -> None:
        self.assertEqual(format_signed_currency(12800), "+12,800 元")

    def test_negative_value_has_minus_sign(self) -> None:
        self.assertEqual(format_signed_currency(-5000), "-5,000 元")

    def test_missing_value_returns_placeholder(self) -> None:
        self.assertEqual(format_signed_currency(pd.NA), "無法估算")


class BuildUnitAttributionNoteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit_row = pd.Series(
            {
                "product_id": "P1",
                "unit_code": "A5",
                "net_revenue_effect_per_day": 27000,
            }
        )

    def test_splittable_activity_cites_matched_pair_number(self) -> None:
        pairing_rows = pd.DataFrame(
            [
                {
                    "activity_type": "母親節檔",
                    "split_status": "可拆分",
                    "candidate_units": "A3(3天)",
                    "net_gain_per_day": 12800,
                    "net_gain_total": 64000,
                    "target_unit_days": 5,
                    "remainder_corresponding_activities": "滿千折百",
                }
            ]
        )

        note = build_unit_attribution_note(self.unit_row, pairing_rows)

        self.assertIn("母親節檔", note)
        self.assertIn("+12,800", note)
        self.assertIn("A3(3天)", note)
        self.assertIn("+64,000", note)

    def test_unsplittable_activity_falls_back_with_caveat(self) -> None:
        pairing_rows = pd.DataFrame(
            [
                {
                    "activity_type": "滿千折百",
                    "split_status": (
                        "無法拆分(以整體對應活動對安靜期估算)"
                    ),
                    "candidate_units": (
                        "(無同月同組合對照期，已對安靜期估算)"
                    ),
                    "net_gain_per_day": 27000,
                    "net_gain_total": 135000,
                    "target_unit_days": 5,
                    "remainder_corresponding_activities": "母親節檔",
                }
            ]
        )

        note = build_unit_attribution_note(self.unit_row, pairing_rows)

        self.assertIn("滿千折百", note)
        self.assertIn("找不到", note)
        self.assertIn("母親節檔", note)
        self.assertIn("+27,000", note)

    def test_two_overlapping_activities_each_get_own_sentence(self) -> None:
        pairing_rows = pd.DataFrame(
            [
                {
                    "activity_type": "母親節檔",
                    "split_status": "可拆分",
                    "candidate_units": "A3(3天)",
                    "net_gain_per_day": 12800,
                    "net_gain_total": 64000,
                    "target_unit_days": 5,
                    "remainder_corresponding_activities": "滿千折百",
                },
                {
                    "activity_type": "滿千折百",
                    "split_status": (
                        "無法拆分(以整體對應活動對安靜期估算)"
                    ),
                    "candidate_units": (
                        "(無同月同組合對照期，已對安靜期估算)"
                    ),
                    "net_gain_per_day": 27000,
                    "net_gain_total": 135000,
                    "target_unit_days": 5,
                    "remainder_corresponding_activities": "母親節檔",
                },
            ]
        )

        note = build_unit_attribution_note(self.unit_row, pairing_rows)

        self.assertIn("母親節檔", note)
        self.assertIn("滿千折百", note)
        self.assertEqual(note.count("。"), 2)

    def test_no_pairing_data_falls_back_to_unit_level_effect(self) -> None:
        note = build_unit_attribution_note(
            self.unit_row, pd.DataFrame()
        )

        self.assertIn("沒有瀑布法配對比較資料", note)
        self.assertIn("+27,000", note)


class BuildUnitHistoryNoteTests(unittest.TestCase):
    def test_compares_against_median_of_other_units(self) -> None:
        unit_row = pd.Series(
            {
                "product_id": "P1",
                "unit_code": "A5",
                "net_revenue_effect_per_day": 20000,
            }
        )

        unit_overview = pd.DataFrame(
            [
                {
                    "product_id": "P1",
                    "unit_code": "A5",
                    "net_revenue_effect_per_day": 20000,
                },
                {
                    "product_id": "P1",
                    "unit_code": "M2",
                    "net_revenue_effect_per_day": 10000,
                },
                {
                    "product_id": "P1",
                    "unit_code": "M4",
                    "net_revenue_effect_per_day": 14000,
                },
                {
                    "product_id": "P2",
                    "unit_code": "A1",
                    "net_revenue_effect_per_day": 999999,
                },
            ]
        )

        note = build_unit_history_note(unit_row, unit_overview)

        self.assertIn("同商品另有 2 個", note)
        self.assertIn("較中位數高", note)
        self.assertNotIn("999999", note)

    def test_no_history_returns_plain_message(self) -> None:
        unit_row = pd.Series(
            {
                "product_id": "P1",
                "unit_code": "A5",
                "net_revenue_effect_per_day": 20000,
            }
        )

        unit_overview = pd.DataFrame(
            [
                {
                    "product_id": "P1",
                    "unit_code": "A5",
                    "net_revenue_effect_per_day": 20000,
                }
            ]
        )

        note = build_unit_history_note(unit_row, unit_overview)

        self.assertEqual(
            note, "同商品目前沒有其他可比較的活動單位。"
        )


class BuildUnitMechanismPlanTests(unittest.TestCase):
    def test_limited_time_keyword(self) -> None:
        self.assertIn("限搶", build_unit_mechanism_plan("限時搶購"))

    def test_gift_keyword(self) -> None:
        self.assertIn("贈品", build_unit_mechanism_plan("加碼送好禮"))

    def test_bundle_keyword(self) -> None:
        self.assertIn("組合", build_unit_mechanism_plan("超值包套"))

    def test_discount_keyword(self) -> None:
        self.assertIn("折扣", build_unit_mechanism_plan("滿千折百"))

    def test_no_keyword_falls_back_to_generic_plan(self) -> None:
        plan = build_unit_mechanism_plan("")

        self.assertIn("每次只調整", plan)

    def test_none_input_does_not_raise(self) -> None:
        plan = build_unit_mechanism_plan(None)

        self.assertIn("每次只調整", plan)


class BuildUnitPersonalizedRecommendationTests(unittest.TestCase):
    def test_output_contains_all_four_sections(self) -> None:
        unit_row = pd.Series(
            {
                "product_id": "P1",
                "product_name": "商品X",
                "unit_code": "A5",
                "corresponding_activities_label": "母親節檔、滿千折百",
                "days": 5,
                "net_revenue_effect_per_day": 27000,
            }
        )

        pairing_rows = pd.DataFrame(
            [
                {
                    "activity_type": "母親節檔",
                    "split_status": "可拆分",
                    "candidate_units": "A3(3天)",
                    "net_gain_per_day": 12800,
                    "net_gain_total": 64000,
                    "target_unit_days": 5,
                    "remainder_corresponding_activities": "滿千折百",
                }
            ]
        )

        unit_overview = pd.DataFrame([unit_row])

        note = build_unit_personalized_recommendation(
            unit_row=unit_row,
            pairing_rows=pairing_rows,
            unit_overview=unit_overview,
            mechanism_text="滿千折百",
            strategy_category="建議延續",
        )

        for section in [
            "【績效診斷】",
            "【檔期歸因】",
            "【建議決策】",
            "【下一檔執行】",
        ]:
            self.assertIn(section, note)

        self.assertIn("商品X", note)
        self.assertIn("A5", note)
        self.assertIn("母親節檔", note)
        self.assertNotIn("。。", note)

    def test_four_sections_are_on_separate_paragraphs(self) -> None:
        unit_row = pd.Series(
            {
                "product_id": "P1",
                "product_name": "商品X",
                "unit_code": "A5",
                "corresponding_activities_label": "母親節檔",
                "days": 5,
                "net_revenue_effect_per_day": 27000,
            }
        )

        unit_overview = pd.DataFrame([unit_row])

        note = build_unit_personalized_recommendation(
            unit_row=unit_row,
            pairing_rows=pd.DataFrame(),
            unit_overview=unit_overview,
            mechanism_text="",
            strategy_category="建議延續",
        )

        paragraphs = note.split("\n\n")

        self.assertEqual(len(paragraphs), 4)
        self.assertTrue(paragraphs[0].startswith("【績效診斷】"))
        self.assertTrue(paragraphs[1].startswith("【檔期歸因】"))
        self.assertTrue(paragraphs[2].startswith("【建議決策】"))
        self.assertTrue(paragraphs[3].startswith("【下一檔執行】"))

    def test_review_category_uses_review_wording(self) -> None:
        unit_row = pd.Series(
            {
                "product_id": "P1",
                "product_name": "商品X",
                "unit_code": "A5",
                "corresponding_activities_label": "母親節檔",
                "days": 5,
                "net_revenue_effect_per_day": -8000,
            }
        )

        unit_overview = pd.DataFrame([unit_row])

        note = build_unit_personalized_recommendation(
            unit_row=unit_row,
            pairing_rows=pd.DataFrame(),
            unit_overview=unit_overview,
            mechanism_text="",
            strategy_category="建議檢討",
        )

        self.assertIn("不建議直接延續原方案", note)


class BuildUnitPersonalizedRecommendationSectionsTests(
    unittest.TestCase
):
    def test_returns_four_label_text_pairs(self) -> None:
        unit_row = pd.Series(
            {
                "product_id": "P1",
                "product_name": "商品X",
                "unit_code": "A5",
                "corresponding_activities_label": "母親節檔",
                "days": 5,
                "net_revenue_effect_per_day": 27000,
            }
        )

        unit_overview = pd.DataFrame([unit_row])

        sections = build_unit_personalized_recommendation_sections(
            unit_row=unit_row,
            pairing_rows=pd.DataFrame(),
            unit_overview=unit_overview,
            mechanism_text="",
            strategy_category="建議延續",
        )

        self.assertEqual(
            [label for label, _ in sections],
            [
                "【績效診斷】",
                "【檔期歸因】",
                "【建議決策】",
                "【下一檔執行】",
            ],
        )

        for _, text in sections:
            self.assertIsInstance(text, str)
            self.assertNotEqual(text.strip(), "")

    def test_joined_sections_match_plain_text_function(self) -> None:
        unit_row = pd.Series(
            {
                "product_id": "P1",
                "product_name": "商品X",
                "unit_code": "A5",
                "corresponding_activities_label": "母親節檔",
                "days": 5,
                "net_revenue_effect_per_day": 27000,
            }
        )

        unit_overview = pd.DataFrame([unit_row])

        sections = build_unit_personalized_recommendation_sections(
            unit_row=unit_row,
            pairing_rows=pd.DataFrame(),
            unit_overview=unit_overview,
            mechanism_text="",
            strategy_category="建議延續",
        )

        plain_text = build_unit_personalized_recommendation(
            unit_row=unit_row,
            pairing_rows=pd.DataFrame(),
            unit_overview=unit_overview,
            mechanism_text="",
            strategy_category="建議延續",
        )

        self.assertEqual(
            plain_text,
            "\n\n".join(f"{label}{text}" for label, text in sections),
        )


if __name__ == "__main__":
    unittest.main()
