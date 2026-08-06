from __future__ import annotations

import pandas as pd
import streamlit as st

from src.sales_processing import FIELD_LABELS as SALES_FIELD_LABELS


# =========================================================
# 全站共用：資料欄位中文標籤對照表
#
# 涵蓋銷量、活動、平台檔期、優惠內容、整合資料
# 與活動成效分析等各階段產出的欄位名稱。
#
# 銷量核心 4 欄位沿用 src.sales_processing.FIELD_LABELS，
# 避免跟資料上傳頁面既有的標籤定義不一致。
# =========================================================

COLUMN_LABELS: dict[str, str] = {
    # -----------------------------
    # 銷量資料
    # -----------------------------
    **SALES_FIELD_LABELS,
    "source_record_count": "原始資料筆數",
    "had_exact_duplicate": "含完全重複列",
    "had_same_day_multiple": "含同日多筆",
    "exact_duplicate": "完全重複列",
    "same_day_product_multiple": "同日同商品多筆",
    "has_quality_issue": "有品質問題",
    "quality_issue_description": "問題說明",
    "missing_sale_date": "日期缺漏",
    "missing_product_id": "商品編號缺漏",
    "missing_product_name": "商品名稱缺漏",
    "missing_quantity": "銷量缺漏",
    "negative_quantity": "銷量為負數",
    "zero_quantity": "銷量為零",
    "original_sale_date": "原始銷售日期",
    "original_product_id": "原始商品編號",
    "original_quantity": "原始銷量",

    # -----------------------------
    # 商品活動
    # -----------------------------
    "activity_start_date": "活動起始日",
    "activity_end_date": "活動結束日",
    "activity_days": "活動天數",
    "campaign_price": "活動價",
    "activity_tag": "活動類型",
    "activity_gift": "贈品",
    "bonus_gift_name": "贈品品名",
    "promotion_period_raw": "促銷時間（原始）",
    "bonus_period_raw": "加碼期間（原始）",
    "remark": "備註",
    "source_file": "來源檔案",
    "source_row_number": "來源列號",
    "source_sheet": "來源工作表",
    "activity_source_file": "來源檔案",
    "activity_source_row": "來源列號",
    "product_category": "品類",
    "bonus_gift_text": "加碼送",
    "bonus_campaign_text": "加碼活動",
    "is_pre_split": "新模板已預先拆分",

    # -----------------------------
    # 活動單位分析（新方法論，對應參考報表工作表3-7）
    # -----------------------------
    "unit_code": "活動單位",
    "corresponding_activities_label": "對應活動",
    "corresponding_activities": "對應活動",
    "start_date": "開始日期",
    "end_date": "結束日期",
    "days": "天數",
    "month": "月份",
    "discount_rate": "折扣率",
    "note": "備註",
    "is_participating": "本品項是否參與",
    "is_quiet_period": "是否為安靜期",
    "baseline_avg_sales": "基準平均銷量(同月)",
    "baseline_price": "基準售價",
    "unit_avg_sales": "單位平均銷量",
    "unit_avg_price": "活動售價",
    "sales_increment": "銷量增量",
    "volume_effect_per_day": "量增量效應/日",
    "price_effect_per_day": "存量降價效應/日",
    "net_revenue_effect_per_day": "淨營收效應/日",
    "net_revenue_effect_total": "淨營收效應(合計)",
    "total_actual_revenue": "總營收(合計)",
    "classification": "分類",
    "sample_size_note": "樣本量提示",
    "proxy_price_note": "代理牌價提示",
    "price": "售價",
    "price_source": "售價來源",
    "gift": "贈品",
    "activity_type": "活動類型",
    "target_unit": "目標單位",
    "target_unit_days": "目標單位天數",
    "target_unit_corresponding_activities": "目標單位對應活動",
    "remainder_corresponding_activities": "扣除後剩餘對應活動",
    "candidate_units": "對照候選單位",
    "target_unit_avg_sales": "目標單位平均銷量",
    "target_unit_avg_price": "目標單位平均售價",
    "candidate_weighted_avg_daily_revenue": "對照組加權平均日營收",
    "actual_daily_revenue": "實際日營收",
    "net_gain_per_day": "淨增益/日",
    "net_gain_total": "淨增益(合計)",
    "split_status": "拆分狀態",
    "interval_count": "區間數",
    "total_days": "涵蓋天數",
    "total_gain": "增益合計",

    # -----------------------------
    # 母子活動不可分割群組
    # -----------------------------
    "mother_name": "母活動名稱",
    "mother_start_date": "母活動開始日期",
    "mother_end_date": "母活動結束日期",
    "child_name": "子機制名稱",
    "child_start_date": "子機制開始日期",
    "child_end_date": "子機制結束日期",

    # -----------------------------
    # 平台檔期
    # -----------------------------
    "campaign_name": "活動名稱",
    "campaign_level": "活動等級",
    "campaign_start_date": "活動起始日",
    "campaign_end_date": "活動結束日",
    "calendar_activity_count": "活動重疊筆數",

    # -----------------------------
    # 優惠內容
    # -----------------------------
    "scope": "優惠範圍",
    "benefit_type": "優惠類型",
    "benefit_content": "優惠內容",
    "benefit_start_date": "優惠起始日",
    "benefit_end_date": "優惠結束日",
    "threshold_amount": "門檻金額",
    "reward_percentage": "回饋比例",
    "reward_amount": "回饋金額",
    "reward_limit_amount": "回饋上限金額",
    "quota": "名額上限",
    "activity_price": "折價前活動價",
    "discounted_price": "折價後價格",
    "product_benefit_type": "商品優惠類型",
    "product_benefit_content": "商品優惠內容",
    "product_benefit_campaign": "商品優惠活動",
    "product_benefit_count": "商品優惠筆數",
    "global_benefit_type": "全站優惠類型",
    "global_benefit_content": "全站優惠內容",
    "global_benefit_campaign": "全站優惠活動",
    "global_benefit_count": "全站優惠筆數",

    # -----------------------------
    # 整合資料
    # -----------------------------
    "is_product_activity_day": "為商品活動日",
    "is_calendar_activity_day": "為平台檔期日",
    "has_product_benefit": "有商品優惠",
    "has_global_benefit": "有全站優惠",
    "has_any_activity": "當日有任一活動",
    "estimated_revenue": "推估營收",
    "product_activity_count": "商品活動重疊筆數",

    # -----------------------------
    # 活動成效分析
    # -----------------------------
    "baseline_start_date": "基準期起始日",
    "baseline_end_date": "基準期結束日",
    "post_start_date": "活動後起始日",
    "post_end_date": "活動後結束日",
    "baseline_average_daily_sales": "基準期日均銷量",
    "campaign_average_daily_sales": "活動期日均銷量",
    "post_average_daily_sales": "活動後日均銷量",
    "campaign_total_sales": "活動期總銷量",
    "uplift_rate": "活動提升率",
    "post_change_rate": "活動後變化率",
    "baseline_expected_days": "基準期應有天數",
    "baseline_recorded_days": "基準期實際天數",
    "campaign_expected_days": "活動期應有天數",
    "campaign_recorded_days": "活動期實際天數",
    "post_expected_days": "活動後應有天數",
    "post_recorded_days": "活動後實際天數",
    "baseline_complete": "基準期資料完整",
    "campaign_complete": "活動期資料完整",
    "post_complete": "活動後資料完整",
    "all_periods_complete": "前中後皆完整",
    "overlapping_campaigns": "重疊檔期",
    "overlapping_benefits": "重疊優惠",
    "data_confidence": "資料信心",
    "performance_category": "成效分類",

    # -----------------------------
    # 品質檢查／問題清單
    # -----------------------------
    "issue_type": "問題類型",
    "count": "筆數",
    "problem_text": "問題內容",
    "row_number": "資料列號",
}


def label_for(column_name: str) -> str:
    """取得單一欄位的中文標籤，找不到對照時原樣回傳。"""

    return COLUMN_LABELS.get(column_name, column_name)


def default_column_config(
    dataframe: pd.DataFrame,
    exclude: object = (),
) -> dict[str, object]:
    """
    依共用中文標籤對照表，
    為 dataframe 中尚未特別設定格式的欄位
    補上純標籤（label-only）的 column_config。

    exclude 用來排除呼叫端已自行設定
    NumberColumn／DateColumn 等特殊格式的欄位，
    避免在這裡被覆蓋。
    """

    excluded = set(exclude)

    # width 不特別指定（None）時，Streamlit 會依欄位實際內容
    # 自動調整寬度（見官方文件：width=None 預設會 "sized to fit
    # the cell contents"），比起統一寫死 "large" 更符合「依文字
    # 長度調整欄寬」的需求，短欄位不會被拉寬、長欄位也不會被
    # 硬性限制在同一個寬度。
    return {
        column: st.column_config.Column(label=label_for(column))
        for column in dataframe.columns
        if column not in excluded
    }
