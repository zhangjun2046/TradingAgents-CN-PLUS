"""报告导出降级路径测试：不依赖 pandoc 也能生成 Word，并在引擎可用时生成 PDF。"""

import os
import sys
from pathlib import Path

# 确保项目根目录在 path 中
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.report_exporter import ReportExporter, MODULE_TITLES


SAMPLE_REPORT = {
    "stock_symbol": "1810.HK",
    "stock_name": "小米集团",
    "analysis_date": "2026-09-07",
    "analysts": ["market", "fundamentals"],
    "research_depth": 3,
    "summary": "综合来看，小米集团基本面稳健，建议谨慎买入。",
    "reports": {
        "market_report": "## 技术面\n\n当前价格位于均线上方，**趋势偏多**。\n\n| 指标 | 数值 |\n|------|------|\n| MA20 | 18.5 |\n| RSI | 62 |\n",
        "fundamentals_report": "营收同比增长，毛利率改善。\n\n- 现金充裕\n- 研发投入上升",
        "news_report": "近期发布新机，市场关注度提升。",
        "trader_investment_plan": "建议分批买入，止损设于 16.8。",
        "final_trade_decision": "买入，目标价 22.0。",
    },
}


def test_markdown_uses_chinese_module_titles():
    exporter = ReportExporter()
    md = exporter.generate_markdown_report(SAMPLE_REPORT)
    assert "小米集团 分析报告" in md
    assert MODULE_TITLES["market_report"] in md
    assert MODULE_TITLES["fundamentals_report"] in md
    assert MODULE_TITLES["news_report"] in md
    assert MODULE_TITLES["trader_investment_plan"] in md
    assert MODULE_TITLES["final_trade_decision"] in md
    assert "## market_report" not in md


def test_docx_python_docx_fallback_without_pandoc():
    exporter = ReportExporter()
    assert exporter.python_docx_available, "python-docx 必须可用才能降级导出 Word"
    exporter.pandoc_available = False
    content = exporter.generate_docx_report(SAMPLE_REPORT)
    assert content[:2] == b"PK"
    assert len(content) > 2000


def test_pdf_html_contains_chinese_titles():
    exporter = ReportExporter()
    md = exporter.generate_markdown_report(SAMPLE_REPORT)
    html = exporter._markdown_to_html(md)
    assert "小米集团" in html
    assert MODULE_TITLES["market_report"] in html
    assert "<table>" in html


def test_pdf_when_engine_available():
    exporter = ReportExporter()
    if not exporter.pdf_available:
        import pytest
        pytest.skip("PDF 引擎不可用")
    content = exporter.generate_pdf_report(SAMPLE_REPORT)
    assert content[:4] == b"%PDF"
    assert len(content) > 1000


def test_pdf_nested_td_and_html_table_does_not_crash():
    """真实分析报告常含 HTML 表格/单元格内再套表格，fpdf2 write_html 会报 nested td"""
    exporter = ReportExporter()
    if not exporter.fpdf_available:
        import pytest
        pytest.skip("fpdf2 不可用")
    report = {
        **SAMPLE_REPORT,
        "reports": {
            "market_report": (
                "| 指标 | 说明 |\n"
                "|------|------|\n"
                "| A | 含 <td> 文本 |\n"
                "| B | 内嵌表格 |\n\n"
                "<table><tr><th>项</th><th>值</th></tr>"
                "<tr><td>外层<td>错误嵌套</td></td>"
                "<td><table><tr><td>内表</td></tr></table></td></tr></table>\n"
            ),
            "fundamentals_report": "营收同比增长。",
        },
    }
    content = exporter._generate_pdf_with_fpdf(exporter.generate_markdown_report(report))
    assert content[:4] == b"%PDF"
    assert len(content) > 1000
