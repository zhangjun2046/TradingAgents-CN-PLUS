#!/usr/bin/env python3
"""
统一新闻工具港股分支烟雾测试

验证：
1. _sync_hk_news_from_akshare 不会对 stock_code 做 zfill（保持 06030 5 位代码，不变成 006030）
2. _get_hk_share_news 在数据库命中时直接返回，不再调用其他下游
3. _get_hk_share_news 在数据库未命中时会触发 _sync_hk_news_from_akshare 并重新查库
4. 新增的工具描述中包含港股的"数据库 + AKShare"关键字
5. 港股代码归一为 5 位，公司名优先的多关键词检索
6. 01810 / 1810 / 01810.HK 三种输入等价，且 A 股 000001 / 600519 行为未被改坏

不依赖真实 AKShare、MongoDB、外网、pandas。所有外部调用都用 mock，
DataFrame 用最小 fake 对象代替（实现 .empty / .head / .iterrows）。
"""

import sys
import types
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 相关性闸门在被测代码里是延迟导入的，这里先导入一次，
# 避免它在 patch.dict("sys.modules") 块内首次加载后被连带清除
import tradingagents.utils.news_filter  # noqa: E402,F401
from tradingagents.tools.unified_news_tool import (  # noqa: E402
    UnifiedNewsAnalyzer,
    create_unified_news_tool,
)


@contextmanager
def _patch_external_deps(fake_ak_module, fake_news_service):
    """统一 patch akshare 模块 + app.services.news_data_service.NewsDataService。

    用 sys.modules 注入伪模块的方式，避免目标模块尚未 import 时 patch 不到属性。
    """
    fake_news_module = types.ModuleType("app.services.news_data_service")
    fake_news_module.NewsDataService = lambda: fake_news_service

    # 同时注入 app / app.services 命名空间，避免 from app.services.news_data_service import 失败
    fake_app = sys.modules.get("app") or types.ModuleType("app")
    fake_app_services = sys.modules.get("app.services") or types.ModuleType("app.services")

    overrides = {
        "akshare": fake_ak_module,
        "app": fake_app,
        "app.services": fake_app_services,
        "app.services.news_data_service": fake_news_module,
    }
    with patch.dict("sys.modules", overrides):
        yield


class FakeDataFrame:
    """最小化 DataFrame 替身，仅实现 _sync_hk_news_from_akshare 用到的接口。"""

    def __init__(self, rows):
        self._rows = rows

    @property
    def empty(self):
        return len(self._rows) == 0

    def __len__(self):
        return len(self._rows)

    def head(self, n):
        return FakeDataFrame(self._rows[:n])

    def iterrows(self):
        for i, row in enumerate(self._rows):
            yield i, row


def _make_fake_news_df(rows=3, company="中信证券"):
    return FakeDataFrame(
        [
            {
                "新闻标题": f"{company}港股动态第{i}条这是足够长的标题",
                "新闻内容": f"内容{i}：港股市场出现重大消息……",
                "新闻链接": f"https://example.com/hk/{i}",
                "发布时间": "2026-05-08 10:00:00",
                "文章来源": "东方财富",
            }
            for i in range(rows)
        ]
    )


def test_clean_code_keeps_5_digits():
    """港股 06030.HK 的代码检索词应为 06030（绝不能被 zfill 到 006030）"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    captured = []

    def fake_stock_news_em(symbol):
        captured.append(symbol)
        return _make_fake_news_df()

    fake_ak_module = MagicMock()
    fake_ak_module.stock_news_em = fake_stock_news_em

    fake_news_service = MagicMock()
    fake_news_service.save_news_data_sync.return_value = 3

    with _patch_external_deps(fake_ak_module, fake_news_service):
        ok = analyzer._sync_hk_news_from_akshare(
            "06030.HK", max_news=10, company_name="中信证券"
        )

    assert ok is True, "应当成功同步"
    assert "06030" in captured, f"代码检索词应为 5 位 06030，实际检索词: {captured}"
    assert "006030" not in captured, f"出现了 zfill 补零的检索词: {captured}"
    assert captured[0] == "中信证券", f"港股应优先按公司名检索，实际 {captured}"

    call_kwargs = fake_news_service.save_news_data_sync.call_args.kwargs
    assert call_kwargs["market"] == "HK", "港股新闻保存时 market 必须为 HK"
    assert call_kwargs["data_source"] == "akshare"
    saved_news = call_kwargs["news_data"]
    assert len(saved_news) == 3
    assert all(item["symbol"] == "06030" for item in saved_news), \
        "保存到 DB 时所有 symbol 字段都应是 06030"


def test_clean_code_keeps_4_digits():
    """4 位港股代码 0700.HK 归一为 00700，同时保留原始 4 位写法作为兜底检索词"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    captured = []

    def fake_stock_news_em(symbol):
        captured.append(symbol)
        return _make_fake_news_df(2, company="腾讯控股")

    fake_ak_module = MagicMock()
    fake_ak_module.stock_news_em = fake_stock_news_em

    fake_news_service = MagicMock()
    fake_news_service.save_news_data_sync.return_value = 2

    with _patch_external_deps(fake_ak_module, fake_news_service):
        ok = analyzer._sync_hk_news_from_akshare(
            "0700.HK", max_news=10, company_name="腾讯控股"
        )

    assert ok is True
    assert "00700" in captured, f"应包含归一后的 5 位代码 00700，实际 {captured}"
    assert "0700" in captured, f"应保留原始 4 位写法 0700，实际 {captured}"
    assert "000700" not in captured, f"出现了 zfill 补零的检索词: {captured}"

    saved_news = fake_news_service.save_news_data_sync.call_args.kwargs["news_data"]
    assert all(item["symbol"] == "00700" for item in saved_news), \
        f"落库 symbol 应统一为 00700，实际 {[i['symbol'] for i in saved_news]}"


def test_short_titles_filtered():
    """标题 < 5 字符的噪声新闻应被过滤掉，避免污染数据库"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    df = FakeDataFrame(
        [
            {"新闻标题": "公告", "新闻内容": "中信证券公告", "新闻链接": "u1", "发布时间": "2026-05-08", "文章来源": "东方财富"},
            {"新闻标题": "短", "新闻内容": "中信证券快讯", "新闻链接": "u2", "发布时间": "2026-05-08", "文章来源": "东方财富"},
            {"新闻标题": "中信证券发布中期业绩报告", "新闻内容": "内容3", "新闻链接": "u3", "发布时间": "2026-05-08", "文章来源": "东方财富"},
        ]
    )

    fake_ak_module = MagicMock()
    fake_ak_module.stock_news_em = lambda symbol: df

    fake_news_service = MagicMock()
    fake_news_service.save_news_data_sync.return_value = 1

    with _patch_external_deps(fake_ak_module, fake_news_service):
        ok = analyzer._sync_hk_news_from_akshare(
            "06030.HK", max_news=10, company_name="中信证券"
        )

    assert ok is True
    saved_news = fake_news_service.save_news_data_sync.call_args.kwargs["news_data"]
    assert len(saved_news) == 1, f"只应保存 1 条长标题新闻，实际 {len(saved_news)}"
    assert saved_news[0]["title"] == "中信证券发布中期业绩报告"


def test_irrelevant_news_not_saved():
    """与该港股无关的新闻（如同名基金公告）不应落库"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    df = FakeDataFrame(
        [
            {
                "新闻标题": "中欧潜力价值灵活配置混合A(001810)基金份额净值公告",
                "新闻内容": "该基金今日单位净值为1.2345元",
                "新闻链接": "u1",
                "发布时间": "2026-05-08",
                "文章来源": "东方财富",
            }
        ]
    )

    fake_ak_module = MagicMock()
    fake_ak_module.stock_news_em = lambda symbol: df

    fake_news_service = MagicMock()

    with _patch_external_deps(fake_ak_module, fake_news_service):
        ok = analyzer._sync_hk_news_from_akshare(
            "01810.HK", max_news=10, company_name="小米集团"
        )

    assert ok is False, "全部新闻不相关时应返回 False"
    fake_news_service.save_news_data_sync.assert_not_called()


def test_hk_input_formats_are_equivalent():
    """01810 / 1810 / 01810.HK 三种输入应产生同样的落库代码，且都不出现补零码"""
    saved_symbols = []

    for raw in ["01810", "1810", "01810.HK"]:
        analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
        captured = []

        def fake_stock_news_em(symbol):
            captured.append(symbol)
            return FakeDataFrame(
                [
                    {
                        "新闻标题": "小米集团发布中期业绩报告",
                        "新闻内容": "小米集团营收同比增长",
                        "新闻链接": "u1",
                        "发布时间": "2026-05-08",
                        "文章来源": "东方财富",
                    }
                ]
            )

        fake_ak_module = MagicMock()
        fake_ak_module.stock_news_em = fake_stock_news_em

        fake_news_service = MagicMock()
        fake_news_service.save_news_data_sync.return_value = 1

        with _patch_external_deps(fake_ak_module, fake_news_service):
            ok = analyzer._sync_hk_news_from_akshare(
                raw, max_news=10, company_name="小米集团"
            )

        assert ok is True, f"输入 {raw} 应同步成功"
        assert "001810" not in captured, f"输入 {raw} 产生了基金代码检索词: {captured}"
        assert "小米集团" in captured, f"输入 {raw} 应优先按公司名检索: {captured}"
        assert "01810" in captured, f"输入 {raw} 的代码检索词应含 01810: {captured}"

        saved_news = fake_news_service.save_news_data_sync.call_args.kwargs["news_data"]
        saved_symbols.append(saved_news[0]["symbol"])

    assert saved_symbols == ["01810", "01810", "01810"], \
        f"三种输入的落库代码应完全一致，实际 {saved_symbols}"


def test_empty_dataframe_returns_false():
    """AKShare 返回空 DataFrame 时应该优雅返回 False，不抛异常"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    fake_ak_module = MagicMock()
    fake_ak_module.stock_news_em = lambda symbol: FakeDataFrame([])

    fake_news_service = MagicMock()

    with _patch_external_deps(fake_ak_module, fake_news_service):
        ok = analyzer._sync_hk_news_from_akshare("06030.HK", max_news=10)

    assert ok is False
    fake_news_service.save_news_data_sync.assert_not_called()


def test_get_hk_news_db_hit_short_circuits():
    """数据库命中时应该立即返回，不再触发 sync 或下游工具"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    db_news_text = "# 06030.HK 最新新闻 (数据库缓存)\n\n📅 查询时间: ...\n📊 新闻数量: 3 条\n\n详细内容..."

    with patch.object(analyzer, "_get_news_from_database", return_value=db_news_text) as p_db, \
            patch.object(analyzer, "_sync_hk_news_from_akshare") as p_sync:
        result = analyzer._get_hk_share_news("06030.HK", max_news=10)

    assert "数据库缓存(港股)" in result, "应当走数据库缓存分支"
    p_db.assert_called_once()
    p_sync.assert_not_called()


def test_get_hk_news_triggers_sync_when_db_empty():
    """数据库未命中时应触发 _sync_hk_news_from_akshare 并重新查库"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    db_call_count = {"n": 0}

    def fake_get_db(stock_code, max_news, market=None, company_name=None):
        db_call_count["n"] += 1
        if db_call_count["n"] == 1:
            return ""
        return "# 06030.HK 最新新闻 (新同步)\n\n📊 新闻数量: 3 条\n\n详细内容..."

    with patch.object(analyzer, "_get_news_from_database", side_effect=fake_get_db) as p_db, \
            patch.object(analyzer, "_sync_hk_news_from_akshare", return_value=True) as p_sync:
        result = analyzer._get_hk_share_news("06030.HK", max_news=10)

    assert p_sync.called, "数据库为空时必须触发 AKShare 同步"
    assert p_db.call_count == 2, f"应查询数据库 2 次（同步前后），实际 {p_db.call_count}"
    assert "数据库缓存(新同步-港股)" in result


def test_tool_description_mentions_db_and_akshare():
    """工具描述应反映新的港股优先级（数据库 + AKShare）"""
    fake_toolkit = MagicMock()
    tool = create_unified_news_tool(fake_toolkit)

    desc = tool.description
    assert "港股" in desc and "数据库缓存" in desc and "AKShare" in desc, (
        f"工具描述应明确说明港股新优先级，当前: {desc}"
    )


def test_identify_hk_stock():
    """股票类型识别应正确把 06030.HK 归类为港股"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    assert analyzer._identify_stock_type("06030.HK") == "港股"
    assert analyzer._identify_stock_type("0700.HK") == "港股"
    assert analyzer._identify_stock_type("01810") == "港股"
    assert analyzer._identify_stock_type("1810") == "港股"
    assert analyzer._identify_stock_type("600519") == "A股"
    assert analyzer._identify_stock_type("000001") == "A股"
    assert analyzer._identify_stock_type("AAPL") == "美股"


def test_identify_stock_type_respects_explicit_market():
    """显式 market 优先于代码格式推断"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    # 被误补零的 001810 在显式 HK 下必须按港股处理
    assert analyzer._identify_stock_type("001810", market="HK") == "港股"
    assert analyzer._identify_stock_type("600519", market="CN") == "A股"
    assert analyzer._identify_stock_type("AAPL", market="US") == "美股"


def test_identify_stock_type_no_longer_defaults_to_a_share():
    """无法识别的代码不再被默认当成A股"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    assert analyzer._identify_stock_type("不是股票代码") == "未知"
    assert analyzer._identify_stock_type("12345678") == "未知"


def test_unknown_market_returns_explicit_error():
    """未知市场时应明确报错，不能悄悄走A股逻辑"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    with patch.object(analyzer, "_get_a_share_news") as p_a, \
            patch.object(analyzer, "_get_hk_share_news") as p_hk:
        result = analyzer.get_stock_news_unified("12345678", max_news=10)

    assert "无法识别股票代码" in result
    p_a.assert_not_called()
    p_hk.assert_not_called()


def test_a_share_branch_unchanged():
    """A 股分支应保持原有行为不变（保留两分支的承诺）"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    db_news_text = "# 600519 A股新闻报告\n\n详细内容..."
    with patch.object(analyzer, "_get_news_from_database", return_value=db_news_text), \
            patch.object(analyzer, "_sync_news_from_akshare") as p_sync_a, \
            patch.object(analyzer, "_sync_hk_news_from_akshare") as p_sync_hk:
        result = analyzer._get_a_share_news("600519", max_news=10)

    assert "数据库缓存" in result and "港股" not in result.split("===")[1], (
        "A 股分支不应混入港股标识"
    )
    p_sync_a.assert_not_called()
    p_sync_hk.assert_not_called(), "A 股分支不能调用港股的同步方法"


def test_a_share_query_uses_cn_market_and_six_digits():
    """A 股查库仍按 6 位代码 + market=CN，行为未被改坏"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    captured = []

    def fake_get_db(stock_code, max_news, market=None, company_name=None):
        captured.append((stock_code, market))
        return "# A股新闻报告\n\n详细内容..."

    for raw in ["000001", "600519"]:
        with patch.object(analyzer, "_get_news_from_database", side_effect=fake_get_db):
            analyzer._get_a_share_news(raw, max_news=10)

    assert captured == [("000001", "CN"), ("600519", "CN")], \
        f"A 股应以原始 6 位代码与 market=CN 查库，实际 {captured}"


def test_a_share_sync_passes_cn_market():
    """A 股同步分支必须显式传 market=CN，且代码补齐到 6 位"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    captured = {}

    class FakeProvider:
        async def get_stock_news(self, symbol, limit, market=None):
            captured["symbol"] = symbol
            captured["market"] = market
            return None

    fake_module = types.ModuleType("tradingagents.dataflows.providers.china.akshare")
    fake_module.AKShareProvider = FakeProvider

    with patch.dict(
        "sys.modules",
        {"tradingagents.dataflows.providers.china.akshare": fake_module},
    ):
        analyzer._sync_news_from_akshare("1", max_news=5)

    assert captured["symbol"] == "000001", f"A 股应补齐到 6 位，实际 {captured}"
    assert captured["market"] == "CN"


if __name__ == "__main__":
    tests = [
        test_clean_code_keeps_5_digits,
        test_clean_code_keeps_4_digits,
        test_short_titles_filtered,
        test_irrelevant_news_not_saved,
        test_hk_input_formats_are_equivalent,
        test_empty_dataframe_returns_false,
        test_get_hk_news_db_hit_short_circuits,
        test_get_hk_news_triggers_sync_when_db_empty,
        test_tool_description_mentions_db_and_akshare,
        test_identify_hk_stock,
        test_identify_stock_type_respects_explicit_market,
        test_identify_stock_type_no_longer_defaults_to_a_share,
        test_unknown_market_returns_explicit_error,
        test_a_share_branch_unchanged,
        test_a_share_query_uses_cn_market_and_six_digits,
        test_a_share_sync_passes_cn_market,
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
    print(f"测试结果: {passed}/{len(tests)} 通过")
    sys.exit(0 if passed == len(tests) else 1)
