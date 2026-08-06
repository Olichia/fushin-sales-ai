

# =========================================================
# B2B / B2C audience split tests
# =========================================================

def test_b2c_prompt_blocks_internal_metrics():
    from src.action_generator import build_action_generation_prompt
    prompt = build_action_generation_prompt(
        evidence_text="預估活動營收 100 元",
        channel="Email",
        tone="專業",
        length="標準",
        audience_type="B2C 消費者行銷",
        public_offer={
            "product_name": "高速調理機",
            "activity_price": 3990,
            "gift_name": "隨行杯",
        },
    )
    assert "一般消費者" in prompt
    assert "不得出現預估活動營收" in prompt
    assert "活動價：3,990 元" in prompt


def test_b2c_fallback_does_not_expose_internal_metrics():
    from src.action_generator import build_fallback_action_content
    result = build_fallback_action_content(
        sections=[("【試算結果】", "預估活動營收 100 元")],
        channel="LINE/簡訊",
        tone="促成交易",
        audience_type="B2C 消費者行銷",
        public_offer={
            "product_name": "高速調理機",
            "activity_price": 3990,
            "gift_name": "隨行杯",
            "cta": "立即選購",
        },
    )
    assert "3,990" in result
    assert "預估活動營收" not in result
    assert "立即選購" in result


def test_b2b_prompt_keeps_full_evidence():
    from src.action_generator import build_action_generation_prompt
    prompt = build_action_generation_prompt(
        evidence_text="預估活動營收 100 元",
        channel="Email",
        tone="專業",
        length="標準",
        audience_type="B2B 商務溝通",
    )
    assert "預估活動營收 100 元" in prompt
    assert "完整分析證據" in prompt
