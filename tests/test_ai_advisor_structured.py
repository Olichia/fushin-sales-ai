import pandas as pd
import pytest

from src.ai_advisor import (
    AdvisorStructuredResponse,
    build_fallback_advisor_response,
    condense_structured_response,
    get_structured_advisor_answer,
)


def _sample_unit_overview() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "unit_avg_sales": [10, 20, 5],
            "baseline_avg_sales": [8, 25, 6],
            "baseline_price": [100, 100, 100],
            "unit_avg_price": [90, 80, 95],
            "sales_increment": [2, -5, -1],
            "volume_effect_per_day": [10, -5, -2],
            "price_effect_per_day": [-5, -20, -1],
            "net_revenue_effect_per_day": [500, -800, 50],
            "net_revenue_effect_total": [2000, -3200, 200],
            "days": [4, 4, 4],
            "month": [3, 3, 3],
            "product_id": ["P1", "P2", "P3"],
            "product_name": ["A", "B", "C"],
            "unit_code": ["M1", "M2", "M3"],
            "corresponding_activities_label": ["x", "y", "z"],
            "classification": [
                "可分離,單一活動",
                "可分離,單一活動",
                "可分離,單一活動",
            ],
            "sample_size_note": ["", "", ""],
            "proxy_price_note": ["", "", ""],
        }
    )


def test_build_fallback_advisor_response_returns_valid_schema():
    response = build_fallback_advisor_response(
        _sample_unit_overview()
    )

    assert isinstance(response, AdvisorStructuredResponse)
    assert response.confidence == "低"
    assert "3" in response.finding
    assert "示範備援" in response.limitations


def test_build_fallback_advisor_response_counts_are_correct():
    response = build_fallback_advisor_response(
        _sample_unit_overview()
    )

    # 淨增益中位數為 50（P3）：500、50 達中位數以上為建議延續（2 個），
    # -800 為負值一律建議檢討；風險判斷（降價效應絕對值 > 量增效應
    # 絕對值）只有 P2（-20 vs -5）成立，共 1 個。
    assert "2 個建議延續" in response.finding
    assert "1 個存在毛利侵蝕風險" in response.finding


def test_condense_structured_response_includes_finding_and_action():
    response = AdvisorStructuredResponse(
        finding="淨增益最高的是 A 商品",
        reason="因為銷量增加",
        evidence="淨增益 +500/日",
        action="下一檔延續此組合",
        alternative="或測試更淺的折扣",
        confidence="高",
        limitations="樣本量有限",
    )

    condensed = condense_structured_response(response)

    assert "淨增益最高的是 A 商品" in condensed
    assert "下一檔延續此組合" in condensed


def test_get_structured_advisor_answer_falls_back_after_two_failures(
    monkeypatch,
):
    call_count = {"n": 0}

    def _always_fail(**kwargs):
        call_count["n"] += 1
        raise ValueError("模擬 API 失敗")

    monkeypatch.setattr(
        "src.ai_advisor.ask_gemini_advisor_structured", _always_fail
    )

    response, is_fallback = get_structured_advisor_answer(
        user_question="下一檔怎麼規劃？",
        advisor_context="（測試背景）",
        chat_messages=[],
        unit_overview_dataframe=_sample_unit_overview(),
    )

    assert is_fallback is True
    assert isinstance(response, AdvisorStructuredResponse)
    assert call_count["n"] == 2


def test_get_structured_advisor_answer_succeeds_on_second_attempt(
    monkeypatch,
):
    call_count = {"n": 0}

    success_response = AdvisorStructuredResponse(
        finding="發現",
        reason="原因",
        evidence="證據",
        action="行動",
        alternative="替代方案",
        confidence="中",
        limitations="限制",
    )

    def _fail_then_succeed(**kwargs):
        call_count["n"] += 1

        if call_count["n"] == 1:
            raise ValueError("第一次模擬失敗")

        return success_response

    monkeypatch.setattr(
        "src.ai_advisor.ask_gemini_advisor_structured",
        _fail_then_succeed,
    )

    response, is_fallback = get_structured_advisor_answer(
        user_question="下一檔怎麼規劃？",
        advisor_context="（測試背景）",
        chat_messages=[],
        unit_overview_dataframe=_sample_unit_overview(),
    )

    assert is_fallback is False
    assert response is success_response
    assert call_count["n"] == 2
