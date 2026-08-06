import pandas as pd
import pytest

from src.action_generator import (
    build_fallback_action_content,
    build_platform_campaign_name_set,
    build_unit_action_evidence,
    build_unit_activity_composition_note,
    build_whatif_action_evidence,
    classify_activity_type,
)
from src.whatif_simulation import WhatIfScenarioResult


# =========================================================
# 平台檔期 vs 商品優惠 分類
# =========================================================

def _sample_calendar() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "campaign_name": ["女王節", "廚電日", "買二送一"],
            "campaign_level": ["平台檔期", "平台檔期", "品牌鋪底活動"],
        }
    )


def test_build_platform_campaign_name_set_only_keeps_platform_level():
    names = build_platform_campaign_name_set(_sample_calendar())

    assert names == {"女王節", "廚電日"}


def test_build_platform_campaign_name_set_missing_calendar_returns_empty():
    assert build_platform_campaign_name_set(None) == set()
    assert build_platform_campaign_name_set(pd.DataFrame()) == set()


def test_classify_activity_type_matches_substring_for_merged_names():
    platform_names = {"女王節"}

    # 子階段合併後名稱是「女王節正式」，仍應判斷為平台檔期。
    assert (
        classify_activity_type("女王節正式", platform_names)
        == "平台檔期"
    )


def test_classify_activity_type_product_promotion():
    platform_names = {"女王節"}

    assert (
        classify_activity_type("買二送一", platform_names)
        == "商品/品牌活動"
    )


def test_classify_activity_type_unknown_when_calendar_missing():
    assert (
        classify_activity_type("買二送一", set())
        == "無法判斷（缺活動日曆資料）"
    )


# =========================================================
# 活動組成說明
# =========================================================

def _sample_unit_row(label: str) -> pd.Series:
    return pd.Series(
        {
            "product_id": "P1",
            "product_name": "測試商品",
            "unit_code": "U1",
            "corresponding_activities_label": label,
            "days": 5,
            "net_revenue_effect_per_day": 100.0,
        }
    )


def test_composition_note_flags_platform_and_product_together():
    unit_row = _sample_unit_row("女王節正式、買二送一")

    note = build_unit_activity_composition_note(
        unit_row,
        _sample_calendar(),
    )

    assert "平台檔期" in note
    assert "商品/品牌活動" in note
    assert "不同方向的優惠" in note


def test_composition_note_single_platform_activity_no_mixed_note():
    unit_row = _sample_unit_row("女王節正式")

    note = build_unit_activity_composition_note(
        unit_row,
        _sample_calendar(),
    )

    assert "平台檔期" in note
    assert "不同方向的優惠" not in note


def test_composition_note_missing_calendar_admits_uncertainty():
    unit_row = _sample_unit_row("女王節正式、買二送一")

    note = build_unit_activity_composition_note(
        unit_row,
        None,
    )

    assert "無法判斷" in note


def test_composition_note_quiet_period_unit():
    unit_row = _sample_unit_row("")

    note = build_unit_activity_composition_note(
        unit_row,
        _sample_calendar(),
    )

    assert "安靜期" in note


# =========================================================
# 證據組裝：活動單位分析
# =========================================================

def _sample_unit_overview() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _sample_unit_row("女王節正式、買二送一"),
        ]
    )


def test_build_unit_action_evidence_includes_composition_section():
    unit_row = _sample_unit_row("女王節正式、買二送一")

    evidence = build_unit_action_evidence(
        unit_row=unit_row,
        pairing_rows=pd.DataFrame(),
        unit_overview=_sample_unit_overview(),
        mechanism_text="",
        strategy_category="建議延續",
        activity_calendar_dataframe=_sample_calendar(),
    )

    assert evidence["source_type"] == "活動單位分析"

    labels = [
        label
        for label, _ in evidence["sections"]
    ]

    assert "【活動組成】" in labels
    assert "平台檔期" in evidence["evidence_text"]
    assert "商品/品牌活動" in evidence["evidence_text"]


# =========================================================
# 證據組裝：情境模擬
# =========================================================

def _sample_scenario_result(
    **overrides,
) -> WhatIfScenarioResult:
    base = {
        "label": "方案 B・您的方案",
        "discount_rate": 0.1,
        "estimated_activity_revenue": 9000.0,
        "expected_revenue_without_activity": 10000.0,
        "net_revenue_gain": -1000.0,
        "total_gift_cost": 200.0,
        "simplified_net_benefit": -1200.0,
        "has_gift": True,
        "platform_overlap": False,
    }

    base.update(overrides)

    return WhatIfScenarioResult(**base)


def test_build_whatif_action_evidence_flags_hypothetical_nature():
    evidence = build_whatif_action_evidence(
        scenario_result=_sample_scenario_result(),
        product_name="測試商品",
    )

    assert evidence["source_type"] == "情境模擬"
    assert "情境試算" in evidence["evidence_text"]
    assert (
        "不是已經發生的真實活動成效"
        in evidence["evidence_text"]
    )


def test_build_whatif_action_evidence_keeps_platform_overlap_caveat():
    evidence = build_whatif_action_evidence(
        scenario_result=_sample_scenario_result(
            platform_overlap=True,
        ),
        product_name="測試商品",
    )

    evidence_text = evidence["evidence_text"]

    assert "平台活動" in evidence_text
    assert "未計入" in evidence_text


def test_build_whatif_action_evidence_no_platform_caveat_when_unchecked():
    evidence = build_whatif_action_evidence(
        scenario_result=_sample_scenario_result(
            platform_overlap=False,
        ),
        product_name="測試商品",
    )

    evidence_text = evidence["evidence_text"]

    assert "平台活動的疊加貢獻" not in evidence_text
    assert "本次試算未計入" not in evidence_text


# =========================================================
# 規則式 fallback（不呼叫任何模型）
# =========================================================

@pytest.mark.parametrize(
    "channel",
    [
        "電話話術",
        "LINE/簡訊",
        "Email",
        "拜訪提綱",
    ],
)
def test_build_fallback_action_content_never_empty(
    channel: str,
):
    sections = [
        ("【績效診斷】", "測試診斷內容。"),
        ("【建議決策】", "測試建議內容。"),
    ]

    content = build_fallback_action_content(
        sections=sections,
        channel=channel,
        tone="專業",
    )

    assert content.strip()

    assert (
        "測試診斷內容" in content
        or "測試建議內容" in content
    )


def test_build_fallback_action_content_email_has_subject_line():
    sections = [
        ("【績效診斷】", "測試診斷內容。"),
    ]

    content = build_fallback_action_content(
        sections=sections,
        channel="Email",
        tone="關係維護",
    )

    assert content.startswith("主旨：")