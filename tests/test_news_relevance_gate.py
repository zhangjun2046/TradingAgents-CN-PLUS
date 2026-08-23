#!/usr/bin/env python3
"""
新闻相关性闸门测试

验证：
1. 基金代码 001810 的公告不会被当成港股 01810（小米集团）的新闻
2. A股泛市场稿（指数/板块/ETF）被拦截
3. 小米回购、小米汽车等真实相关新闻被保留
4. 全部不相关时返回空列表，并给出可用于失败文案的统计信息
5. 公司名解析失败时降级为"只拦噪声"，不会误杀全部新闻
6. 港股公司名走港股映射，而不是只收录A股的 STOCK_COMPANY_MAPPING

全部使用 mock，不依赖外网、MongoDB。
"""

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tradingagents.utils.news_filter import (  # noqa: E402
    create_news_filter,
    filter_news_items,
    get_company_name,
)

XIAOMI_NAME = "小米集团－Ｗ"

# 与目标股票真正相关的新闻
RELEVANT_NEWS = [
    {
        "title": "小米集团获准回购公司股份",
        "content": "小米集团公告，董事会通过回购议案……",
    },
    {
        "title": "小米汽车7月交付量突破3万台",
        "content": "小米汽车YU7持续放量……",
    },
    {
        "title": "小米集团（01810.HK）午后涨超3%",
        "content": "港股科技股集体走强。",
    },
]

# 需要被拦截的无关新闻：基金 001810 与 A 股泛市场稿
IRRELEVANT_NEWS = [
    {
        "title": "中欧潜力价值灵活配置混合A(001810)基金份额净值公告",
        "content": "该基金今日单位净值为1.2345元，基金经理表示……",
    },
    {
        "title": "上证180ETF指数基金（530280）自带杠铃策略",
        "content": "上证180指数前十大权重股分别为贵州茅台、招商银行……",
    },
    {
        "title": "沪指涨0.5% 银行板块领涨",
        "content": "A股三大指数集体收涨，板块轮动加快。",
    },
]


def test_fund_news_is_rejected_for_hk_stock():
    """001810 基金新闻不能进入 01810 的新闻池"""
    kept, stats = filter_news_items(
        IRRELEVANT_NEWS, "01810", market="HK", company_name=XIAOMI_NAME
    )

    assert kept == [], f"基金/指数类新闻应全部被拦截，实际保留 {[k['title'] for k in kept]}"
    assert stats["original_count"] == 3
    assert stats["rejected_count"] == 3
    assert stats["strict_mode"] is True, "公司名已知时应走严格模式"


def test_relevant_news_is_kept():
    """真实相关新闻必须保留，并按评分降序"""
    kept, stats = filter_news_items(
        RELEVANT_NEWS, "01810", market="HK", company_name=XIAOMI_NAME
    )

    assert len(kept) == 3, f"3条相关新闻都应保留，实际 {len(kept)}"
    scores = [item["relevance_score"] for item in kept]
    assert scores == sorted(scores, reverse=True), f"应按相关性降序排列: {scores}"
    assert stats["max_score"] >= 50, f"含公司名的标题评分应不低于50，实际 {stats['max_score']}"


def test_mixed_news_only_keeps_relevant():
    """混合输入时只保留相关新闻"""
    kept, stats = filter_news_items(
        RELEVANT_NEWS + IRRELEVANT_NEWS, "01810", market="HK", company_name=XIAOMI_NAME
    )

    kept_titles = {item["title"] for item in kept}
    for item in RELEVANT_NEWS:
        assert item["title"] in kept_titles, f"相关新闻被误杀: {item['title']}"
    for item in IRRELEVANT_NEWS:
        assert item["title"] not in kept_titles, f"无关新闻未被拦截: {item['title']}"
    assert stats["filtered_count"] == 3 and stats["original_count"] == 6


def test_code_matching_uses_digit_boundary():
    """01810 不能被 001810 命中，这是本次问题的关键"""
    news_filter = create_news_filter("01810", market="HK", company_name="未知公司名占位")
    assert news_filter._match_code("基金代码001810今日净值") is None, \
        "001810 不应被识别为 01810"
    assert news_filter._match_code("小米集团01810今日大涨") is not None
    assert news_filter._match_code("代码 1810.HK 收盘价") is not None


def test_full_width_company_name_is_matched():
    """港股名称常带全角后缀，必须能匹配正文里的半角写法"""
    news_filter = create_news_filter("01810", market="HK", company_name=XIAOMI_NAME)
    assert "小米集团" in news_filter.company_aliases, \
        f"应从 {XIAOMI_NAME} 派生出 小米集团，实际 {news_filter.company_aliases}"
    assert "小米" in news_filter.company_aliases, \
        f"应派生出简称 小米，实际 {news_filter.company_aliases}"


def test_all_irrelevant_returns_empty_with_stats():
    """全部不相关时返回空列表，统计信息可用于生成失败文案"""
    kept, stats = filter_news_items(
        IRRELEVANT_NEWS, "01810", market="HK", company_name=XIAOMI_NAME
    )

    assert not kept
    assert stats["original_count"] > 0, "统计里必须保留候选数量，否则无法区分'没新闻'和'全不相关'"
    assert stats["company_name"] == XIAOMI_NAME


def test_unknown_company_name_degrades_to_noise_filter():
    """公司名解析失败时不能误杀全部新闻，只拦明显噪声"""
    ambiguous_news = [
        {"title": "某港股公司发布中期业绩", "content": "营收同比增长10%"},
        {"title": "上证180ETF指数基金份额变动", "content": "该指数基金今日……"},
    ]

    kept, stats = filter_news_items(
        ambiguous_news, "09999", market="HK", company_name="港股09999"
    )

    assert stats["strict_mode"] is False, "占位公司名应触发降级模式"
    kept_titles = {item["title"] for item in kept}
    assert "某港股公司发布中期业绩" in kept_titles, "降级模式下普通新闻不应被误杀"
    assert "上证180ETF指数基金份额变动" not in kept_titles, "降级模式下仍需拦截基金噪声"


def test_a_share_gate_still_works():
    """A股相关性判定行为不被改坏"""
    news = [
        {"title": "招商银行发布2024年第三季度业绩报告", "content": "净利润同比增长8%"},
        {"title": "银行ETF指数(512730)多只成分股上涨", "content": "银行板块今日表现强势"},
    ]

    kept, stats = filter_news_items(news, "600036", market="CN")

    kept_titles = {item["title"] for item in kept}
    assert "招商银行发布2024年第三季度业绩报告" in kept_titles
    assert "银行ETF指数(512730)多只成分股上涨" not in kept_titles
    assert stats["company_name"] == "招商银行", f"A股应走内置映射，实际 {stats['company_name']}"


def test_hk_company_name_uses_hk_mapping():
    """港股公司名必须走港股映射，而不是A股映射表"""
    with patch(
        "tradingagents.dataflows.providers.hk.improved_hk.get_hk_company_name_improved",
        return_value="腾讯控股",
    ):
        name = get_company_name("00700", market="HK")

    assert name == "腾讯控股", f"港股应返回真实公司名，实际 {name}"


def test_hk_company_name_falls_back_to_placeholder():
    """港股公司名获取失败时返回占位名，交由降级逻辑处理"""
    with patch(
        "tradingagents.dataflows.providers.hk.improved_hk.get_hk_company_name_improved",
        side_effect=RuntimeError("network down"),
    ):
        name = get_company_name("08888", market="HK")

    assert name == "港股08888", f"应返回占位名，实际 {name}"
    assert create_news_filter("08888", market="HK", company_name=name).has_company_name is False


if __name__ == "__main__":
    tests = [
        test_fund_news_is_rejected_for_hk_stock,
        test_relevant_news_is_kept,
        test_mixed_news_only_keeps_relevant,
        test_code_matching_uses_digit_boundary,
        test_full_width_company_name_is_matched,
        test_all_irrelevant_returns_empty_with_stats,
        test_unknown_company_name_degrades_to_noise_filter,
        test_a_share_gate_still_works,
        test_hk_company_name_uses_hk_mapping,
        test_hk_company_name_falls_back_to_placeholder,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{'=' * 60}")
    print(f"result: {passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
