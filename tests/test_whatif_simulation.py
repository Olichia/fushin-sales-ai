import pandas as pd
import pytest

from src.whatif_simulation import (
    WhatIfScenarioInput,
    build_whatif_summary_insight,
    build_whatif_summary_short,
    compute_whatif_scenario,
    compute_whatif_scenarios,
    estimate_avg_discount_rate_from_history,
    estimate_baseline_price_from_history,
    estimate_daily_sales_from_history,
    estimate_sales_uplift_rate_from_history,
    select_best_scenario,
)


def _input(**overrides) -> WhatIfScenarioInput:
    base = dict(
        label="測試方案",
        activity_price=90.0,
        baseline_price=100.0,
        estimated_daily_sales=10.0,
        estimated_activity_sales=10.0,
        days=5,
        has_gift=False,
        gift_cost_per_unit=0.0,
        platform_overlap=False,
    )
    base.update(overrides)
    return WhatIfScenarioInput(**base)


def test_compute_whatif_scenario_basic_arithmetic():
    result = compute_whatif_scenario(_input())

    assert result.discount_rate == pytest.approx(0.10)
    assert result.estimated_activity_revenue == pytest.approx(
        90.0 * 10.0 * 5
    )
    assert result.expected_revenue_without_activity == pytest.approx(
        100.0 * 10.0 * 5
    )
    assert result.net_revenue_gain == pytest.approx(
        result.estimated_activity_revenue
        - result.expected_revenue_without_activity
    )
    assert result.total_gift_cost == 0.0
    assert result.simplified_net_benefit == pytest.approx(
        result.net_revenue_gain
    )


def test_compute_whatif_scenario_with_gift_cost_deducted():
    result = compute_whatif_scenario(
        _input(has_gift=True, gift_cost_per_unit=20.0)
    )

    expected_gift_cost = 20.0 * 10.0 * 5
    assert result.total_gift_cost == pytest.approx(expected_gift_cost)
    assert result.simplified_net_benefit == pytest.approx(
        result.net_revenue_gain - expected_gift_cost
    )


def test_compute_whatif_scenario_gift_cost_ignored_when_no_gift():
    result = compute_whatif_scenario(
        _input(has_gift=False, gift_cost_per_unit=999.0)
    )

    assert result.total_gift_cost == 0.0


def test_compute_whatif_scenario_uses_activity_sales_for_activity_side():
    # 預估活動銷量（依歷史提升率換算）跟預估日均銷量（無活動基準）
    # 刻意分開：活動營收／贈品成本吃活動銷量，無活動預期營收吃
    # 日均銷量，兩者不同時公式不能互相污染。
    result = compute_whatif_scenario(
        _input(
            estimated_daily_sales=10.0,
            estimated_activity_sales=15.0,
            has_gift=True,
            gift_cost_per_unit=20.0,
        )
    )

    assert result.estimated_activity_sales == pytest.approx(15.0)
    assert result.estimated_activity_revenue == pytest.approx(
        90.0 * 15.0 * 5
    )
    assert result.expected_revenue_without_activity == pytest.approx(
        100.0 * 10.0 * 5
    )
    assert result.total_gift_cost == pytest.approx(20.0 * 15.0 * 5)


def test_compute_whatif_scenario_zero_baseline_price_has_no_discount_rate():
    result = compute_whatif_scenario(
        _input(baseline_price=0.0, activity_price=50.0)
    )

    assert result.discount_rate is None
    assert result.expected_revenue_without_activity == 0.0


def test_compute_whatif_scenarios_preserves_order_and_labels():
    inputs = [
        _input(label="方案 A", activity_price=90.0),
        _input(label="方案 B", activity_price=80.0),
    ]

    results = compute_whatif_scenarios(inputs)

    assert [result.label for result in results] == ["方案 A", "方案 B"]


def test_select_best_scenario_picks_highest_simplified_net_benefit():
    # 模型刻意不假設「降價會帶動銷量」——同一份預估日均銷量下，
    # 價格離基準價越遠（不論漲跌），淨營收增益離 0 越遠；這裡用
    # 漲價（正增益）對比深折扣（負增益）驗證挑選邏輯本身正確，
    # 不是驗證「哪個定價策略比較好」。
    inputs = [
        _input(label="漲價", activity_price=110.0),
        _input(label="深折扣", activity_price=60.0),
    ]

    results = compute_whatif_scenarios(inputs)
    best = select_best_scenario(results)

    assert best is not None
    assert best.label == "漲價"


def test_select_best_scenario_empty_list_returns_none():
    assert select_best_scenario([]) is None


# =========================================================
# 歷史預設值
# =========================================================

def _sample_unit_overview() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_id": ["P1", "P1", "P2"],
            "unit_avg_sales": [10, 20, 5],
            "baseline_price": [100, 120, 50],
        }
    )


def test_estimate_daily_sales_from_history_returns_median():
    value = estimate_daily_sales_from_history(
        _sample_unit_overview(), "P1"
    )

    assert value == pytest.approx(15.0)


def test_estimate_daily_sales_from_history_missing_product_returns_none():
    value = estimate_daily_sales_from_history(
        _sample_unit_overview(), "NOT_FOUND"
    )

    assert value is None


def test_estimate_daily_sales_from_history_empty_dataframe_returns_none():
    value = estimate_daily_sales_from_history(
        pd.DataFrame(), "P1"
    )

    assert value is None


def test_estimate_baseline_price_from_history_returns_median():
    value = estimate_baseline_price_from_history(
        _sample_unit_overview(), "P1"
    )

    assert value == pytest.approx(110.0)


# =========================================================
# 摘要卡片內容
# =========================================================

def test_build_whatif_summary_insight_empty_results():
    summary = build_whatif_summary_insight([])

    assert "尚無模擬結果" in summary["finding"]


def test_build_whatif_summary_insight_names_best_and_worst():
    results = compute_whatif_scenarios(
        [
            _input(label="漲價", activity_price=110.0),
            _input(label="深折扣", activity_price=60.0),
        ]
    )

    summary = build_whatif_summary_insight(results)

    assert "漲價" in summary["finding"]
    assert "深折扣" in summary["finding"]


def test_build_whatif_summary_insight_flags_platform_overlap():
    results = compute_whatif_scenarios(
        [
            _input(label="A", platform_overlap=True),
            _input(label="B", activity_price=70.0),
        ]
    )

    summary = build_whatif_summary_insight(results)

    assert "平台活動" in summary["reason"]


def test_build_whatif_summary_insight_no_overlap_note_when_unchecked():
    results = compute_whatif_scenarios(
        [
            _input(label="A"),
            _input(label="B", activity_price=70.0),
        ]
    )

    summary = build_whatif_summary_insight(results)

    assert "平台活動" not in summary["reason"]


def test_build_whatif_summary_short_is_single_line_finding():
    results = compute_whatif_scenarios(
        [
            _input(label="漲價", activity_price=110.0),
            _input(label="深折扣", activity_price=60.0),
        ]
    )

    summary = build_whatif_summary_short(results)

    assert "\n" not in summary
    assert "漲價" in summary
    assert "深折扣" in summary


def test_build_whatif_summary_short_empty_results():
    summary = build_whatif_summary_short([])

    assert "尚無模擬結果" in summary


# =========================================================
# 折扣率 / 銷量提升率的歷史換算
# =========================================================

def test_estimate_avg_discount_rate_from_history_returns_mean():
    unit_overview = pd.DataFrame(
        {
            "product_id": ["P1", "P1", "P2"],
            "discount_rate": [0.10, 0.20, 0.50],
        }
    )

    value = estimate_avg_discount_rate_from_history(
        unit_overview, "P1"
    )

    assert value == pytest.approx(0.15)


def test_estimate_avg_discount_rate_from_history_missing_product_returns_none():
    unit_overview = pd.DataFrame(
        {
            "product_id": ["P1"],
            "discount_rate": [0.10],
        }
    )

    value = estimate_avg_discount_rate_from_history(
        unit_overview, "NOT_FOUND"
    )

    assert value is None


def _sample_uplift_overview() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_id": ["P1", "P1", "P2"],
            "discount_rate": [0.12, 0.13, 0.12],
            "unit_avg_sales": [20, 15, 12],
            "baseline_avg_sales": [10, 10, 10],
        }
    )


def test_estimate_sales_uplift_rate_from_history_uses_same_product_same_bracket():
    # P1 在 10-15% 折扣區間有兩筆：uplift = 20/10-1=1.0、15/10-1=0.5，
    # 平均提升率 0.75。
    rate, note = estimate_sales_uplift_rate_from_history(
        _sample_uplift_overview(), "P1", 0.12
    )

    assert rate == pytest.approx(0.75)
    assert "同折扣區間" in note


def test_estimate_sales_uplift_rate_from_history_falls_back_to_all_products():
    # P3 沒有歷史資料，退回全商品同折扣區間平均：
    # (1.0 + 0.5 + 0.2) / 3。
    rate, note = estimate_sales_uplift_rate_from_history(
        _sample_uplift_overview(), "P3", 0.12
    )

    assert rate == pytest.approx((1.0 + 0.5 + 0.2) / 3)
    assert "全商品" in note


def test_estimate_sales_uplift_rate_from_history_no_bracket_data_returns_zero():
    rate, note = estimate_sales_uplift_rate_from_history(
        _sample_uplift_overview(), "P1", -0.5
    )

    assert rate == 0.0
    assert "無歷史" in note


def test_estimate_sales_uplift_rate_from_history_none_discount_rate_returns_zero():
    rate, note = estimate_sales_uplift_rate_from_history(
        _sample_uplift_overview(), "P1", None
    )

    assert rate == 0.0


def test_estimate_sales_uplift_rate_from_history_empty_dataframe_returns_zero():
    rate, note = estimate_sales_uplift_rate_from_history(
        pd.DataFrame(), "P1", 0.12
    )

    assert rate == 0.0
