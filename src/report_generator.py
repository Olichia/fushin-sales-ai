from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from src.executive_summary import (
    build_activity_unit_strategy_text,
    compute_discount_bracket_stats,
    compute_product_ranking,
    compute_top_activity_combos,
)
from src.unit_overview_helpers import (
    compute_actual_revenue_total,
    compute_confidence_label,
    compute_risk_mask,
    compute_strategy_category,
    prepare_unit_overview_for_display,
)


# =========================================================
# 中文字型
# =========================================================

PDF_FONT_NAME = "TraditionalChinese"
PDF_BOLD_FONT_NAME = "TraditionalChineseBold"

FALLBACK_FONT_NAME = "MSung-Light"

_pdf_fonts_registered = False


def register_pdf_fonts() -> None:
    """
    註冊 PDF 中文字型。

    優先使用可嵌入的 Windows TrueType 字型。
    若雲端環境的 Noto CJK 字型無法被 ReportLab 載入，
    則退回 ReportLab 內建的繁體 CID 字型，
    避免整個主管報表頁面無法開啟。
    """

    global PDF_FONT_NAME
    global PDF_BOLD_FONT_NAME
    global _pdf_fonts_registered

    if _pdf_fonts_registered:
        return

    registered_fonts = set(
        pdfmetrics.getRegisteredFontNames()
    )

    # -----------------------------------------------------
    # 1. Windows 本機字型
    # -----------------------------------------------------

    windows_regular_candidates = [
        Path(r"C:\Windows\Fonts\kaiu.ttf"),
        Path(r"C:\Windows\Fonts\msjh.ttc"),
        Path(r"C:\Windows\Fonts\mingliu.ttc"),
    ]

    windows_bold_candidates = [
        Path(r"C:\Windows\Fonts\msjhbd.ttc"),
        Path(r"C:\Windows\Fonts\msjh.ttc"),
        Path(r"C:\Windows\Fonts\kaiu.ttf"),
        Path(r"C:\Windows\Fonts\mingliu.ttc"),
    ]

    regular_font_path = next(
        (
            path
            for path in windows_regular_candidates
            if path.exists()
        ),
        None,
    )

    bold_font_path = next(
        (
            path
            for path in windows_bold_candidates
            if path.exists()
        ),
        None,
    )

    if regular_font_path is not None:
        try:
            if PDF_FONT_NAME not in registered_fonts:
                if regular_font_path.suffix.lower() == ".ttc":
                    pdfmetrics.registerFont(
                        TTFont(
                            PDF_FONT_NAME,
                            str(regular_font_path),
                            subfontIndex=0,
                        )
                    )
                else:
                    pdfmetrics.registerFont(
                        TTFont(
                            PDF_FONT_NAME,
                            str(regular_font_path),
                        )
                    )

            if bold_font_path is None:
                bold_font_path = regular_font_path

            if PDF_BOLD_FONT_NAME not in registered_fonts:
                if bold_font_path.suffix.lower() == ".ttc":
                    pdfmetrics.registerFont(
                        TTFont(
                            PDF_BOLD_FONT_NAME,
                            str(bold_font_path),
                            subfontIndex=0,
                        )
                    )
                else:
                    pdfmetrics.registerFont(
                        TTFont(
                            PDF_BOLD_FONT_NAME,
                            str(bold_font_path),
                        )
                    )

            _pdf_fonts_registered = True
            return

        except Exception:
            # Windows 字型註冊失敗時，繼續使用 CID 備援。
            pass

    # -----------------------------------------------------
    # 2. Streamlit Cloud / Linux 備援
    # -----------------------------------------------------

    try:
        if FALLBACK_FONT_NAME not in registered_fonts:
            pdfmetrics.registerFont(
                UnicodeCIDFont(
                    FALLBACK_FONT_NAME
                )
            )

        PDF_FONT_NAME = FALLBACK_FONT_NAME
        PDF_BOLD_FONT_NAME = FALLBACK_FONT_NAME
        _pdf_fonts_registered = True

    except Exception as error:
        raise RuntimeError(
            "PDF 中文字型初始化失敗："
            f"{error}"
        ) from error


# =========================================================
# 格式化工具
# =========================================================

def format_number(
    value: Any,
    decimal_places: int = 0,
) -> str:
    if value is None or pd.isna(value):
        return "-"

    try:
        return f"{float(value):,.{decimal_places}f}"
    except (TypeError, ValueError):
        return str(value)


def format_percentage(
    value: Any,
) -> str:
    if value is None or pd.isna(value):
        return "-"

    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return str(value)


def format_date(
    value: Any,
) -> str:
    if value is None or pd.isna(value):
        return "-"

    parsed_date = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed_date):
        return str(value)

    return parsed_date.strftime(
        "%Y-%m-%d"
    )


def clean_text(
    value: Any,
    default: str = "-",
) -> str:
    if value is None or pd.isna(value):
        return default

    text = str(value).strip()

    return text if text else default


# =========================================================
# 樣式
# =========================================================

def create_pdf_styles() -> dict[str, ParagraphStyle]:
    sample_styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "TraditionalChineseTitle",
            parent=sample_styles["Title"],
            fontName=PDF_BOLD_FONT_NAME,
            fontSize=22,
            leading=30,
            textColor=colors.HexColor("#172033"),
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "TraditionalChineseSubtitle",
            parent=sample_styles["Normal"],
            fontName=PDF_FONT_NAME,
            fontSize=10,
            leading=16,
            textColor=colors.HexColor("#667085"),
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "heading1": ParagraphStyle(
            "TraditionalChineseHeading1",
            parent=sample_styles["Heading1"],
            fontName=PDF_BOLD_FONT_NAME,
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#173A71"),
            spaceBefore=8,
            spaceAfter=10,
        ),
        "heading2": ParagraphStyle(
            "TraditionalChineseHeading2",
            parent=sample_styles["Heading2"],
            fontName=PDF_BOLD_FONT_NAME,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#25344A"),
            spaceBefore=6,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "TraditionalChineseBody",
            parent=sample_styles["BodyText"],
            fontName=PDF_FONT_NAME,
            fontSize=9.5,
            leading=16,
            textColor=colors.HexColor("#273142"),
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "TraditionalChineseSmall",
            parent=sample_styles["BodyText"],
            fontName=PDF_FONT_NAME,
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#667085"),
            alignment=TA_LEFT,
        ),
        "table_header": ParagraphStyle(
            "TraditionalChineseTableHeader",
            parent=sample_styles["BodyText"],
            fontName=PDF_BOLD_FONT_NAME,
            fontSize=8,
            leading=11,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "table_body": ParagraphStyle(
            "TraditionalChineseTableBody",
            parent=sample_styles["BodyText"],
            fontName=PDF_FONT_NAME,
            fontSize=7.5,
            leading=11,
            textColor=colors.HexColor("#273142"),
            alignment=TA_LEFT,
        ),
        "kpi_label": ParagraphStyle(
            "TraditionalChineseKpiLabel",
            parent=sample_styles["BodyText"],
            fontName=PDF_FONT_NAME,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#667085"),
            alignment=TA_CENTER,
        ),
        "kpi_value": ParagraphStyle(
            "TraditionalChineseKpiValue",
            parent=sample_styles["BodyText"],
            fontName=PDF_BOLD_FONT_NAME,
            fontSize=15,
            leading=20,
            textColor=colors.HexColor("#173A71"),
            alignment=TA_CENTER,
        ),
    }


# =========================================================
# 頁首頁尾
# =========================================================

def draw_page_header_footer(
    canvas,
    document,
) -> None:
    canvas.saveState()

    page_width, page_height = A4

    canvas.setFont(
        PDF_FONT_NAME,
        8,
    )

    canvas.setFillColor(
        colors.HexColor("#667085")
    )

    canvas.drawString(
        18 * mm,
        page_height - 12 * mm,
        "富信新零售資料分析系統",
    )

    canvas.drawRightString(
        page_width - 18 * mm,
        10 * mm,
        f"第 {document.page} 頁",
    )

    canvas.setStrokeColor(
        colors.HexColor("#E1E7F0")
    )

    canvas.line(
        18 * mm,
        page_height - 15 * mm,
        page_width - 18 * mm,
        page_height - 15 * mm,
    )

    canvas.restoreState()


# =========================================================
# 表格工具
# =========================================================

def build_kpi_table(
    kpi_items: list[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    cells = []

    for label, value in kpi_items:
        cell_content = [
            Paragraph(
                label,
                styles["kpi_label"],
            ),
            Spacer(1, 3),
            Paragraph(
                value,
                styles["kpi_value"],
            ),
        ]

        cells.append(cell_content)

    table = Table(
        [cells],
        colWidths=[
            34 * mm
            for _ in cells
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F4F7FB"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor("#DDE4EE"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#DDE4EE"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    return table


def build_activity_table(
    dataframe: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
    maximum_rows: int = 5,
) -> Table | None:
    if dataframe is None or dataframe.empty:
        return None

    display_dataframe = (
        dataframe.head(maximum_rows).copy()
    )

    header_row = [
        Paragraph(
            "商品活動",
            styles["table_header"],
        ),
        Paragraph(
            "提升率",
            styles["table_header"],
        ),
        Paragraph(
            "活動總銷量",
            styles["table_header"],
        ),
        Paragraph(
            "推估營收",
            styles["table_header"],
        ),
        Paragraph(
            "資料信心",
            styles["table_header"],
        ),
    ]

    table_data = [header_row]

    for _, row in display_dataframe.iterrows():
        product_activity = row.get(
            "商品活動"
        )

        if product_activity is None:
            product_id = clean_text(
                row.get("product_id")
            )

            product_name = clean_text(
                row.get("product_name")
            )

            start_date = format_date(
                row.get(
                    "activity_start_date"
                )
            )

            end_date = format_date(
                row.get(
                    "activity_end_date"
                )
            )

            product_activity = (
                f"{product_id}｜{product_name}"
                f"<br/>{start_date} 至 {end_date}"
            )

        uplift_rate = row.get(
            "活動提升率",
            row.get("uplift_rate"),
        )

        campaign_sales = row.get(
            "活動總銷量",
            row.get("campaign_total_sales"),
        )

        estimated_revenue = row.get(
            "推估營收",
            row.get("estimated_revenue"),
        )

        data_confidence = row.get(
            "資料信心",
            row.get("data_confidence"),
        )

        table_data.append(
            [
                Paragraph(
                    clean_text(
                        product_activity
                    ),
                    styles["table_body"],
                ),
                Paragraph(
                    format_percentage(
                        uplift_rate
                    ),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(
                        campaign_sales
                    ),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(
                        estimated_revenue
                    ),
                    styles["table_body"],
                ),
                Paragraph(
                    clean_text(
                        data_confidence
                    ),
                    styles["table_body"],
                ),
            ]
        )

    table = Table(
        table_data,
        colWidths=[
            72 * mm,
            23 * mm,
            27 * mm,
            29 * mm,
            25 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#173A71"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#DDE4EE"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
                ),
            ]
        )
    )

    return table


# =========================================================
# 表格工具（活動單位分析新方法論）
# =========================================================

def default_data_table_style() -> TableStyle:
    """
    共用表格樣式：深藍表頭、淺格線、交錯列背景。
    跟 build_activity_table() 現有樣式保持一致。
    """

    return TableStyle(
        [
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#173A71"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#DDE4EE"),
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP",
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6,
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F8FAFC"),
                ],
            ),
        ]
    )


def build_product_ranking_table(
    ranking_dataframe: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
) -> Table | None:
    """商品表現排行表（依淨增益合計排序）。"""

    if ranking_dataframe is None or ranking_dataframe.empty:
        return None

    header_labels = [
        "商品",
        "單位數",
        "淨增益合計",
        "延續/觀察/檢討",
        "風險檔數",
    ]

    table_data = [
        [
            Paragraph(label, styles["table_header"])
            for label in header_labels
        ]
    ]

    for _, row in ranking_dataframe.iterrows():
        table_data.append(
            [
                Paragraph(
                    clean_text(row.get("product_name")),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(row.get("unit_count")),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(row.get("net_gain_total")),
                    styles["table_body"],
                ),
                Paragraph(
                    f"{format_number(row.get('continue_count'))} / "
                    f"{format_number(row.get('observe_count'))} / "
                    f"{format_number(row.get('review_count'))}",
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(row.get("risk_count")),
                    styles["table_body"],
                ),
            ]
        )

    table = Table(
        table_data,
        colWidths=[52 * mm, 20 * mm, 32 * mm, 38 * mm, 22 * mm],
        repeatRows=1,
    )

    table.setStyle(default_data_table_style())

    return table


def build_unit_highlight_pair(
    best_row: pd.Series,
    worst_row: pd.Series,
    styles: dict[str, ParagraphStyle],
) -> Table:
    """表現最佳／較差活動單位並列卡片。"""

    def build_cell(
        eyebrow: str,
        row: pd.Series,
        value_color: str,
    ) -> list:
        return [
            Paragraph(eyebrow, styles["kpi_label"]),
            Spacer(1, 2),
            Paragraph(
                f"{clean_text(row.get('product_name'))}・"
                f"{clean_text(row.get('unit_code'))}",
                styles["table_body"],
            ),
            Paragraph(
                clean_text(
                    row.get("corresponding_activities_label")
                ),
                styles["small"],
            ),
            Spacer(1, 3),
            Paragraph(
                f"<font color='{value_color}'>"
                f"{format_number(row.get('net_revenue_effect_per_day'))}"
                " 元/日</font>",
                styles["kpi_value"],
            ),
        ]

    cells = [
        [
            build_cell("表現最佳", best_row, "#009B73"),
            build_cell("表現較差", worst_row, "#C62828"),
        ]
    ]

    table = Table(
        cells,
        colWidths=[80 * mm, 80 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F4F7FB"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor("#DDE4EE"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#DDE4EE"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    return table


def build_discount_bracket_table(
    bracket_stats_dataframe: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
) -> Table | None:
    """折扣區間 × 平均淨增益對照表。"""

    if (
        bracket_stats_dataframe is None
        or bracket_stats_dataframe.empty
    ):
        return None

    header_labels = ["折扣區間", "平均淨增益/日", "檔數"]

    table_data = [
        [
            Paragraph(label, styles["table_header"])
            for label in header_labels
        ]
    ]

    for _, row in bracket_stats_dataframe.iterrows():
        table_data.append(
            [
                Paragraph(
                    clean_text(row.get("discount_bracket")),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(row.get("avg_net_effect")),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(row.get("unit_count")),
                    styles["table_body"],
                ),
            ]
        )

    table = Table(
        table_data,
        colWidths=[60 * mm, 50 * mm, 30 * mm],
        repeatRows=1,
    )

    table.setStyle(default_data_table_style())

    return table


def build_combo_table(
    combo_dataframe: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
) -> Table | None:
    """疊加活動組合排行表（可拆分／不可拆分）。"""

    if combo_dataframe is None or combo_dataframe.empty:
        return None

    header_labels = ["活動組合", "拆分狀態", "涵蓋區間", "增益合計"]

    table_data = [
        [
            Paragraph(label, styles["table_header"])
            for label in header_labels
        ]
    ]

    for _, row in combo_dataframe.iterrows():
        table_data.append(
            [
                Paragraph(
                    clean_text(
                        row.get("corresponding_activities")
                    ),
                    styles["table_body"],
                ),
                Paragraph(
                    clean_text(row.get("split_status")),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(row.get("interval_count")),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(row.get("total_gain")),
                    styles["table_body"],
                ),
            ]
        )

    table = Table(
        table_data,
        colWidths=[80 * mm, 24 * mm, 24 * mm, 36 * mm],
        repeatRows=1,
    )

    table.setStyle(default_data_table_style())

    return table


def build_risk_table(
    risk_dataframe: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
) -> Table | None:
    """毛利侵蝕風險活動單位清單。"""

    if risk_dataframe is None or risk_dataframe.empty:
        return None

    header_labels = [
        "商品／單位",
        "活動售價",
        "基準售價",
        "折扣率",
        "淨增益/日",
    ]

    table_data = [
        [
            Paragraph(label, styles["table_header"])
            for label in header_labels
        ]
    ]

    for _, row in risk_dataframe.iterrows():
        table_data.append(
            [
                Paragraph(
                    f"{clean_text(row.get('product_name'))}・"
                    f"{clean_text(row.get('unit_code'))}",
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(row.get("unit_avg_price")),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(row.get("baseline_price")),
                    styles["table_body"],
                ),
                Paragraph(
                    format_percentage(row.get("discount_rate")),
                    styles["table_body"],
                ),
                Paragraph(
                    format_number(
                        row.get("net_revenue_effect_per_day")
                    ),
                    styles["table_body"],
                ),
            ]
        )

    table = Table(
        table_data,
        colWidths=[56 * mm, 30 * mm, 30 * mm, 24 * mm, 24 * mm],
        repeatRows=1,
    )

    table.setStyle(default_data_table_style())

    return table


# =========================================================
# PDF 主函式
# =========================================================

def generate_management_pdf(
    sales_dataframe: pd.DataFrame | None,
    performance_dataframe: pd.DataFrame,
    strategy_dataframe: pd.DataFrame | None,
    strategy_report_text: str | None,
    activity_issues_dataframe: pd.DataFrame | None = None,
    integration_issues_dataframe: pd.DataFrame | None = None,
) -> bytes:
    """
    產生主管活動分析 PDF。

    僅使用既有分析結果，不重新計算活動成效。
    字型只在真正產生 PDF 時初始化，
    避免匯入模組時影響整個 Streamlit App。
    """

    register_pdf_fonts()

    if (
        performance_dataframe is None
        or performance_dataframe.empty
    ):
        raise ValueError(
            "目前沒有活動成效資料可產生 PDF。"
        )

    buffer = io.BytesIO()

    document = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="富信新零售活動分析主管報告",
        author="富信新零售資料分析系統",
    )

    content_frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="main_content",
    )

    page_template = PageTemplate(
        id="management_report",
        frames=[content_frame],
        onPage=draw_page_header_footer,
    )

    document.addPageTemplates(
        [page_template]
    )

    styles = create_pdf_styles()
    story = []

    # -----------------------------------------------------
    # 封面標題
    # -----------------------------------------------------

    generated_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )

    story.append(
        Paragraph(
            "活動成效與策略建議主管報告",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            f"產生時間：{generated_time}",
            styles["subtitle"],
        )
    )

    # -----------------------------------------------------
    # 基本資料
    # -----------------------------------------------------

    sales_start_date = None
    sales_end_date = None
    total_quantity = 0
    product_count = 0

    if (
        sales_dataframe is not None
        and not sales_dataframe.empty
    ):
        sales = sales_dataframe.copy()

        if "sale_date" in sales.columns:
            sales["sale_date"] = pd.to_datetime(
                sales["sale_date"],
                errors="coerce",
            )

            sales_start_date = (
                sales["sale_date"].min()
            )

            sales_end_date = (
                sales["sale_date"].max()
            )

        if "quantity" in sales.columns:
            sales["quantity"] = pd.to_numeric(
                sales["quantity"],
                errors="coerce",
            )

            total_quantity = (
                sales["quantity"].sum()
            )

        if "product_id" in sales.columns:
            product_count = (
                sales["product_id"].nunique()
            )

    performance = performance_dataframe.copy()

    if "uplift_rate" not in performance.columns:
        raise ValueError(
            "活動成效資料缺少 uplift_rate 欄位，"
            "請重新執行活動成效分析。"
        )

    performance["uplift_rate"] = pd.to_numeric(
        performance["uplift_rate"],
        errors="coerce",
    )

    activity_count = len(performance)

    high_count = int(
        (
            performance["uplift_rate"]
            >= 0.20
        ).sum()
    )

    low_count = int(
        (
            performance["uplift_rate"]
            < 0
        ).sum()
    )

    median_uplift = (
        performance["uplift_rate"].median()
    )

    complete_rate = pd.NA

    if (
        "all_periods_complete"
        in performance.columns
        and activity_count > 0
    ):
        complete_rate = (
            performance[
                "all_periods_complete"
            ]
            .fillna(False)
            .astype(bool)
            .mean()
        )

    story.append(
        Paragraph(
            "一、分析概況",
            styles["heading1"],
        )
    )

    analysis_period = (
        f"{format_date(sales_start_date)}"
        f" 至 "
        f"{format_date(sales_end_date)}"
    )

    story.append(
        Paragraph(
            f"本報告分析期間為 {analysis_period}。"
            "內容整合銷量資料、商品活動期間、活動前後比較"
            "與規則式策略分類。",
            styles["body"],
        )
    )

    kpi_items = [
        (
            "總銷量",
            format_number(
                total_quantity
            ),
        ),
        (
            "分析商品數",
            format_number(
                product_count
            ),
        ),
        (
            "活動分析數",
            format_number(
                activity_count
            ),
        ),
        (
            "高成效活動",
            format_number(
                high_count
            ),
        ),
        (
            "提升率中位數",
            format_percentage(
                median_uplift
            ),
        ),
    ]

    story.append(
        build_kpi_table(
            kpi_items,
            styles,
        )
    )

    story.append(
        Spacer(1, 12)
    )

    # -----------------------------------------------------
    # 最佳與最差活動
    # -----------------------------------------------------

    valid_performance = (
        performance.dropna(
            subset=["uplift_rate"]
        )
    )

    story.append(
        Paragraph(
            "二、活動成效重點",
            styles["heading1"],
        )
    )

    if valid_performance.empty:
        story.append(
            Paragraph(
                "目前沒有可計算提升率的活動資料。",
                styles["body"],
            )
        )

    else:
        best_activity = (
            valid_performance.sort_values(
                "uplift_rate",
                ascending=False,
            )
            .head(1)
        )

        worst_activity = (
            valid_performance.sort_values(
                "uplift_rate",
                ascending=True,
            )
            .head(1)
        )

        story.append(
            Paragraph(
                "表現最佳活動",
                styles["heading2"],
            )
        )

        best_table = build_activity_table(
            best_activity,
            styles,
            maximum_rows=1,
        )

        if best_table is not None:
            story.append(best_table)

        story.append(
            Spacer(1, 10)
        )

        story.append(
            Paragraph(
                "表現較差活動",
                styles["heading2"],
            )
        )

        worst_table = build_activity_table(
            worst_activity,
            styles,
            maximum_rows=1,
        )

        if worst_table is not None:
            story.append(worst_table)

    story.append(
        Spacer(1, 12)
    )

    # -----------------------------------------------------
    # 策略分類
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "三、策略行動建議",
            styles["heading1"],
        )
    )

    if (
        strategy_dataframe is None
        or strategy_dataframe.empty
    ):
        story.append(
            Paragraph(
                "目前沒有可用的策略建議資料。",
                styles["body"],
            )
        )

    else:
        strategy = strategy_dataframe.copy()

        strategy_categories = [
            (
                "建議延續",
                "建議延續的活動",
            ),
            (
                "建議優化",
                "建議優化的活動",
            ),
            (
                "建議檢討",
                "建議檢討的活動",
            ),
        ]

        for category_value, category_title in (
            strategy_categories
        ):
            category_dataframe = strategy[
                strategy[
                    "策略分類"
                ] == category_value
            ].copy()

            story.append(
                Paragraph(
                    category_title,
                    styles["heading2"],
                )
            )

            if category_dataframe.empty:
                story.append(
                    Paragraph(
                        "目前沒有符合此分類的活動。",
                        styles["body"],
                    )
                )

            else:
                category_dataframe = (
                    category_dataframe
                    .sort_values(
                        "活動提升率",
                        ascending=False,
                        na_position="last",
                    )
                )

                category_table = (
                    build_activity_table(
                        category_dataframe,
                        styles,
                        maximum_rows=5,
                    )
                )

                if category_table is not None:
                    story.append(
                        category_table
                    )

            story.append(
                Spacer(1, 8)
            )

    # -----------------------------------------------------
    # 資料風險
    # -----------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "四、資料品質與判讀限制",
            styles["heading1"],
        )
    )

    activity_issue_count = (
        len(activity_issues_dataframe)
        if activity_issues_dataframe is not None
        else 0
    )

    integration_issue_count = (
        len(integration_issues_dataframe)
        if integration_issues_dataframe is not None
        else 0
    )

    overlap_count = 0

    if (
        "overlapping_campaigns"
        in performance.columns
        or "overlapping_benefits"
        in performance.columns
    ):
        overlap_mask = pd.Series(
            False,
            index=performance.index,
        )

        if (
            "overlapping_campaigns"
            in performance.columns
        ):
            overlap_mask = (
                overlap_mask
                | performance[
                    "overlapping_campaigns"
                ].notna()
            )

        if (
            "overlapping_benefits"
            in performance.columns
        ):
            overlap_mask = (
                overlap_mask
                | performance[
                    "overlapping_benefits"
                ].notna()
            )

        overlap_count = int(
            overlap_mask.sum()
        )

    limitation_items = [
        (
            f"完整前、中、後觀察期間比例為 "
            f"{format_percentage(complete_rate)}。"
        ),
        (
            f"低成效活動共有 "
            f"{format_number(low_count)} 筆。"
        ),
        (
            f"存在其他活動或優惠重疊的活動共有 "
            f"{format_number(overlap_count)} 筆。"
        ),
        (
            f"活動資料待確認問題共有 "
            f"{format_number(activity_issue_count)} 筆。"
        ),
        (
            f"資料整合待確認問題共有 "
            f"{format_number(integration_issue_count)} 筆。"
        ),
        (
            "活動期間銷量上升只能視為關聯，"
            "不能直接證明活動造成銷量提升。"
        ),
        (
            "推估營收尚未納入實際成交折扣、退貨、"
            "平台幣、贈品成本與毛利。"
        ),
        (
            "在缺少成本與毛利資料時，"
            "不能直接判定活動是否獲利。"
        ),
    ]

    for index, limitation in enumerate(
        limitation_items,
        start=1,
    ):
        story.append(
            Paragraph(
                f"{index}. {limitation}",
                styles["body"],
            )
        )

    # -----------------------------------------------------
    # 規則式摘要
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "五、主管策略摘要",
            styles["heading1"],
        )
    )

    if strategy_report_text:
        report_lines = [
            line.strip()
            for line in strategy_report_text.splitlines()
            if line.strip()
        ]

        for line in report_lines:
            if line.startswith("#"):
                cleaned_line = line.lstrip(
                    "#"
                ).strip()

                story.append(
                    Paragraph(
                        cleaned_line,
                        styles["heading2"],
                    )
                )

            elif line.startswith("-"):
                cleaned_line = line.lstrip(
                    "-"
                ).strip()

                story.append(
                    Paragraph(
                        f"• {cleaned_line}",
                        styles["body"],
                    )
                )

            else:
                story.append(
                    Paragraph(
                        line,
                        styles["body"],
                    )
                )

    else:
        story.append(
            Paragraph(
                "目前沒有可用的策略文字摘要。",
                styles["body"],
            )
        )

    # -----------------------------------------------------
    # 文件聲明
    # -----------------------------------------------------

    story.append(
        Spacer(1, 14)
    )

    story.append(
        Paragraph(
            "本報告由系統依既有分析結果自動產生，"
            "應作為決策討論與後續驗證的起點，"
            "不應取代商業負責人的最終判斷。",
            styles["small"],
        )
    )

    document.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


# =========================================================
# PDF 主函式（活動單位分析新方法論）
# =========================================================

def generate_activity_unit_management_pdf(
    unit_overview_dataframe: pd.DataFrame,
    waterfall_summary_dataframe: pd.DataFrame,
) -> bytes:
    """
    產生主管活動分析 PDF（活動單位分析新方法論版）。

    取代 generate_management_pdf() 的舊版活動前後比較內容，
    改用同月安靜期基準、量增/降價效應拆解與瀑布法配對結果。
    僅使用既有分析結果，不重新計算活動成效。
    """

    register_pdf_fonts()

    if (
        unit_overview_dataframe is None
        or unit_overview_dataframe.empty
    ):
        raise ValueError(
            "目前沒有活動單位分析資料可產生 PDF。"
        )

    unit_overview = prepare_unit_overview_for_display(
        unit_overview_dataframe
    )
    unit_overview["策略分類"] = compute_strategy_category(
        unit_overview
    )
    unit_overview["is_risky"] = compute_risk_mask(unit_overview)
    unit_overview["資料信心"] = compute_confidence_label(
        unit_overview
    )
    unit_overview["total_actual_revenue"] = (
        compute_actual_revenue_total(unit_overview)
    )

    buffer = io.BytesIO()

    document = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="富信新零售活動單位分析主管報告",
        author="富信新零售資料分析系統",
    )

    content_frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="main_content",
    )

    page_template = PageTemplate(
        id="management_report",
        frames=[content_frame],
        onPage=draw_page_header_footer,
    )

    document.addPageTemplates([page_template])

    styles = create_pdf_styles()
    story = []

    # -----------------------------------------------------
    # 封面標題
    # -----------------------------------------------------

    generated_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )

    story.append(
        Paragraph(
            "活動單位分析與策略建議主管報告",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            f"產生時間：{generated_time}",
            styles["subtitle"],
        )
    )

    # -----------------------------------------------------
    # 一、分析概況
    # -----------------------------------------------------

    total_units = len(unit_overview)
    product_count = unit_overview["product_id"].nunique()
    total_gmv = unit_overview["total_actual_revenue"].sum()
    net_gmv = unit_overview["net_revenue_effect_total"].sum()
    continue_count = int(
        (unit_overview["策略分類"] == "建議延續").sum()
    )
    risk_count = int(unit_overview["is_risky"].sum())

    story.append(
        Paragraph("一、分析概況", styles["heading1"])
    )

    story.append(
        Paragraph(
            "本報告以「活動單位」為顆粒度，比較每個活動單位"
            "相對於同月安靜期基準的淨營收效應，並拆解量增與"
            f"降價兩種效應。共分析 {product_count} 項商品、"
            f"{total_units} 個活動單位。",
            styles["body"],
        )
    )

    kpi_items = [
        ("總GMV合計", format_number(total_gmv)),
        ("淨增益GMV合計", format_number(net_gmv)),
        ("活動單位數", format_number(total_units)),
        ("建議延續數", format_number(continue_count)),
        ("風險檔數", format_number(risk_count)),
    ]

    story.append(build_kpi_table(kpi_items, styles))
    story.append(Spacer(1, 12))

    story.append(
        Paragraph("商品表現排行", styles["heading2"])
    )

    ranking = compute_product_ranking(unit_overview)
    ranking_table = build_product_ranking_table(
        ranking, styles
    )

    if ranking_table is not None:
        story.append(ranking_table)

    story.append(Spacer(1, 12))

    # -----------------------------------------------------
    # 二、活動單位成效重點
    # -----------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph("二、活動單位成效重點", styles["heading1"])
    )

    valid_units = unit_overview.dropna(
        subset=["net_revenue_effect_per_day"]
    )

    if valid_units.empty:
        story.append(
            Paragraph(
                "目前沒有可計算淨增益的活動單位。",
                styles["body"],
            )
        )

    else:
        best_unit = valid_units.sort_values(
            "net_revenue_effect_per_day", ascending=False
        ).iloc[0]

        worst_unit = valid_units.sort_values(
            "net_revenue_effect_per_day", ascending=True
        ).iloc[0]

        story.append(
            build_unit_highlight_pair(
                best_unit, worst_unit, styles
            )
        )

    story.append(Spacer(1, 14))

    story.append(
        Paragraph("折扣率洞察", styles["heading2"])
    )

    bracket_stats = compute_discount_bracket_stats(
        unit_overview
    )
    bracket_table = build_discount_bracket_table(
        bracket_stats, styles
    )

    if bracket_table is not None:
        story.append(bracket_table)

        best_bracket = bracket_stats.loc[
            bracket_stats["avg_net_effect"].idxmax()
        ]

        story.append(
            Paragraph(
                f"「{best_bracket['discount_bracket']}」"
                "區間平均淨增益最高，折扣拉深不必然帶來對應的"
                "營收增幅，深折扣檔期可考慮改以贈品或平台幣"
                "加碼替代直接降價。",
                styles["body"],
            )
        )

    else:
        story.append(
            Paragraph(
                "目前沒有足夠資料計算折扣率洞察。",
                styles["body"],
            )
        )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph("疊加活動組合分析（前5高）", styles["heading2"])
    )

    top_combos = compute_top_activity_combos(
        waterfall_summary_dataframe, top_n=5
    )
    combo_table = build_combo_table(top_combos, styles)

    if combo_table is not None:
        story.append(combo_table)

    else:
        story.append(
            Paragraph(
                "目前沒有可用的疊加活動組合資料。",
                styles["body"],
            )
        )

    # -----------------------------------------------------
    # 三、風險提醒
    # -----------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph("三、風險提醒", styles["heading1"])
    )

    risk_rows = unit_overview[
        unit_overview["is_risky"]
    ].sort_values("net_revenue_effect_per_day")

    if risk_rows.empty:
        story.append(
            Paragraph(
                "目前沒有偵測到明顯的毛利侵蝕風險。",
                styles["body"],
            )
        )

    else:
        story.append(
            Paragraph(
                f"{len(risk_rows)} 個活動單位出現毛利侵蝕風險"
                "（降價效應大於量增效應），建議下檔縮減折扣，"
                "或改以贈品吸引轉換：",
                styles["body"],
            )
        )

        risk_table = build_risk_table(risk_rows, styles)

        if risk_table is not None:
            story.append(risk_table)

    story.append(Spacer(1, 14))

    # -----------------------------------------------------
    # 四、資料信心與判讀限制
    # -----------------------------------------------------

    story.append(
        Paragraph("四、資料信心與判讀限制", styles["heading1"])
    )

    high_confidence_count = int(
        (unit_overview["資料信心"] == "較高").sum()
    )
    low_confidence_count = int(
        (unit_overview["資料信心"] == "較低").sum()
    )

    confidence_kpi_items = [
        ("資料信心較高", format_number(high_confidence_count)),
        ("資料信心較低", format_number(low_confidence_count)),
        ("毛利侵蝕風險", format_number(risk_count)),
    ]

    story.append(
        build_kpi_table(confidence_kpi_items, styles)
    )
    story.append(Spacer(1, 10))

    limitation_items = [
        "活動期間銷量上升只能視為關聯，不能直接證明活動造成銷量提升。",
        "淨增益已扣除同月安靜期基準，但尚未納入實際成交折扣、"
        "退貨、平台幣、贈品成本與毛利。",
        "疊加多種活動機制的活動單位無法拆分個別貢獻，判讀時應更保守。",
        "在缺少成本與毛利資料時，不能直接判定活動是否獲利。",
    ]

    for index, limitation in enumerate(
        limitation_items, start=1
    ):
        story.append(
            Paragraph(
                f"{index}. {limitation}",
                styles["body"],
            )
        )

    # -----------------------------------------------------
    # 五、主管策略摘要
    # -----------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph("五、主管策略摘要", styles["heading1"])
    )

    strategy_text = build_activity_unit_strategy_text(
        unit_overview_dataframe, waterfall_summary_dataframe
    )

    report_lines = [
        line.strip()
        for line in strategy_text.splitlines()
        if line.strip()
    ]

    for line in report_lines:
        if line.startswith("#"):
            cleaned_line = line.lstrip("#").strip()

            story.append(
                Paragraph(cleaned_line, styles["heading2"])
            )

        elif line.startswith("-"):
            cleaned_line = line.lstrip("-").strip()

            story.append(
                Paragraph(
                    f"• {cleaned_line}", styles["body"]
                )
            )

        else:
            story.append(
                Paragraph(line, styles["body"])
            )

    # -----------------------------------------------------
    # 文件聲明
    # -----------------------------------------------------

    story.append(Spacer(1, 14))

    story.append(
        Paragraph(
            "本報告由系統依既有分析結果自動產生，"
            "應作為決策討論與後續驗證的起點，"
            "不應取代商業負責人的最終判斷。",
            styles["small"],
        )
    )

    document.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes