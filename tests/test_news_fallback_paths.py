#!/usr/bin/env python3
"""
港股新闻六条回退路径的市场一致性测试

覆盖路径：
1. 数据库命中
2. 数据库未命中 -> AKShare 港股同步 -> 重新查库
3. 港股 AKShare 同步失败 -> 实时新闻聚合器
4. 实时中文财经新闻 fallback（_get_chinese_finance_news）
5. Google 新闻 fallback
6. 后台同步服务（news_data_sync_service）

每条路径都必须保持 market=HK 与 symbol=01810，不得出现 001810。
全部使用 mock，不访问外网、MongoDB、pandas。
"""

import asyncio
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.worker.news_data_sync_service import NewsDataSyncService  # noqa: E402
from tradingagents.dataflows.news.realtime_news import RealtimeNewsAggregator  # noqa: E402
from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer  # noqa: E402

FORBIDDEN = "001810"
XIAOMI_NAME = "小米集团"


class FakeDataFrame:
    """最小 DataFrame 替身"""

    def __init__(self, rows):
        self._rows = list(rows)

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


def _hk_rows(n=2):
    return [
        {
            "新闻标题": f"小米集团发布第{i}季度业绩公告",
            "新闻内容": "小米集团营收同比增长……",
            "新闻链接": f"https://example.com/hk/{i}",
            "发布时间": "2026-08-20 10:00:00",
            "文章来源": "东方财富",
        }
        for i in range(n)
    ]


@contextmanager
def _patch_hk_sync_deps(capture, rows=None, news_service=None):
    """注入伪 akshare 与 NewsDataService，记录检索关键词与落库参数"""
    fake_ak = types.ModuleType("akshare")

    def fake_stock_news_em(symbol):
        capture.append(symbol)
        return FakeDataFrame(rows if rows is not None else _hk_rows())

    fake_ak.stock_news_em = fake_stock_news_em

    service = news_service or MagicMock()
    if news_service is None:
        service.save_news_data_sync.return_value = 2

    fake_news_module = types.ModuleType("app.services.news_data_service")
    fake_news_module.NewsDataService = lambda: service

    overrides = {
        "akshare": fake_ak,
        "app": sys.modules.get("app") or types.ModuleType("app"),
        "app.services": sys.modules.get("app.services") or types.ModuleType("app.services"),
        "app.services.news_data_service": fake_news_module,
    }
    with patch.dict("sys.modules", overrides):
        yield service


def test_path1_database_hit_keeps_hk_market():
    """路径1：数据库命中时按 HK 查询并直接返回"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    captured = {}

    def fake_db(stock_code, max_news, market=None, company_name=None):
        captured["market"] = market
        captured["stock_code"] = stock_code
        return "# 01810 最新新闻 (数据库缓存)\n\n小米集团回购公司股份，详细内容……"

    with patch.object(analyzer, "_get_news_from_database", side_effect=fake_db), \
            patch.object(analyzer, "_sync_hk_news_from_akshare") as p_sync:
        result = analyzer._get_hk_share_news("01810.HK", max_news=10, company_name=XIAOMI_NAME)

    assert captured["market"] == "HK", f"数据库查询必须带 market=HK，实际 {captured}"
    assert "数据库缓存(港股)" in result
    p_sync.assert_not_called()


def test_path2_db_miss_then_akshare_sync():
    """路径2：数据库未命中触发港股同步，检索码保持 01810"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    db_calls = {"n": 0}
    markets = []

    def fake_db(stock_code, max_news, market=None, company_name=None):
        db_calls["n"] += 1
        markets.append(market)
        if db_calls["n"] == 1:
            return ""
        return "# 01810 最新新闻 (新同步)\n\n小米集团业绩公告，详细内容……"

    capture = []
    with patch.object(analyzer, "_get_news_from_database", side_effect=fake_db):
        with _patch_hk_sync_deps(capture) as service:
            result = analyzer._get_hk_share_news(
                "01810.HK", max_news=10, company_name=XIAOMI_NAME
            )

    assert db_calls["n"] == 2, f"同步前后应各查库一次，实际 {db_calls['n']}"
    assert markets == ["HK", "HK"]
    assert "数据库缓存(新同步-港股)" in result

    assert capture, "应当发起 AKShare 检索"
    assert capture[0] == XIAOMI_NAME, f"港股应优先按公司名检索，实际 {capture}"
    assert "01810" in capture, f"代码变体检索应使用 01810，实际 {capture}"
    assert FORBIDDEN not in capture, f"绝不能出现补零码 {FORBIDDEN}: {capture}"

    save_kwargs = service.save_news_data_sync.call_args.kwargs
    assert save_kwargs["market"] == "HK"
    assert all(item["symbol"] == "01810" for item in save_kwargs["news_data"])


def test_path3_sync_failure_falls_back_to_realtime():
    """路径3：同步失败时回退到实时新闻聚合器"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    analyzer.toolkit.get_realtime_stock_news.invoke.return_value = (
        "# 01810 东方财富新闻报告\n\n" + "小米集团相关新闻内容。" * 20
    )

    with patch.object(analyzer, "_get_news_from_database", return_value=""), \
            patch.object(analyzer, "_sync_hk_news_from_akshare", return_value=False):
        result = analyzer._get_hk_share_news("01810.HK", max_news=10, company_name=XIAOMI_NAME)

    assert "实时港股新闻" in result
    invoke_args = analyzer.toolkit.get_realtime_stock_news.invoke.call_args.args[0]
    assert invoke_args["ticker"] == "01810.HK", f"传给实时源的代码不应被改写: {invoke_args}"


def test_path4_realtime_chinese_news_routes_by_market():
    """路径4：实时中文财经新闻按市场分流，港股不走A股补零路径"""
    aggregator = RealtimeNewsAggregator()
    captured = {}

    class FakeProvider:
        def get_stock_news_sync(self, symbol, limit=10, market=None):
            captured["symbol"] = symbol
            captured["market"] = market
            return FakeDataFrame([])

    fake_module = types.ModuleType("tradingagents.dataflows.providers.china.akshare")
    fake_module.AKShareProvider = FakeProvider

    with patch.dict(
        "sys.modules",
        {"tradingagents.dataflows.providers.china.akshare": fake_module},
    ):
        aggregator._get_chinese_finance_news("01810", hours_back=24)

    assert captured["market"] == "HK", f"港股应以 market=HK 调用，实际 {captured}"
    assert captured["symbol"] == "01810", f"港股检索码应为 01810，实际 {captured}"

    captured.clear()
    with patch.dict(
        "sys.modules",
        {"tradingagents.dataflows.providers.china.akshare": fake_module},
    ):
        aggregator._get_chinese_finance_news("600519.SH", hours_back=24)

    assert captured["market"] == "CN"
    assert captured["symbol"] == "600519", f"A股应剥离后缀并补齐6位，实际 {captured}"


def test_path5_google_news_fallback():
    """路径5：Google 新闻兜底，query 使用原始港股代码"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    analyzer.toolkit.get_realtime_stock_news.invoke.return_value = ""
    analyzer.toolkit.get_google_news.invoke.return_value = (
        "小米集团相关的港股新闻内容。" * 10
    )

    with patch.object(analyzer, "_get_news_from_database", return_value=""), \
            patch.object(analyzer, "_sync_hk_news_from_akshare", return_value=False):
        result = analyzer._get_hk_share_news("01810.HK", max_news=10, company_name=XIAOMI_NAME)

    assert "Google港股新闻" in result
    query = analyzer.toolkit.get_google_news.invoke.call_args.args[0]["query"]
    assert "01810" in query and FORBIDDEN not in query, f"Google query 异常: {query}"


def test_path6_worker_sync_routes_by_market():
    """路径6：后台同步服务按真实市场抓取并落库"""
    service = NewsDataSyncService()
    captured = {}

    async def fake_akshare(symbol, hours_back, max_news, market="CN"):
        captured["akshare_symbol"] = symbol
        captured["akshare_market"] = market
        return [
            {
                "symbol": symbol,
                "market": market,
                "title": "小米集团发布中期业绩公告",
                "content": "小米集团营收同比增长……",
                "url": "https://example.com/hk/1",
                "publish_time": "2026-08-20 10:00:00",
            }
        ]

    async def fake_realtime(symbol, hours_back, max_news, market="CN"):
        return []

    async def fake_tushare(symbol, hours_back, max_news, market="CN"):
        captured["tushare_called"] = True
        return []

    fake_news_service = MagicMock()

    async def fake_save(news_list, data_source, market):
        captured["save_market"] = market
        captured["save_symbols"] = [item["symbol"] for item in news_list]
        return len(news_list)

    fake_news_service.save_news_data = fake_save

    async def fake_get_service():
        return fake_news_service

    with patch.object(service, "_sync_akshare_news", side_effect=fake_akshare), \
            patch.object(service, "_sync_realtime_news", side_effect=fake_realtime), \
            patch.object(service, "_sync_tushare_news", side_effect=fake_tushare), \
            patch.object(service, "_get_news_service", side_effect=fake_get_service):
        stats = asyncio.run(service.sync_stock_news("1810.HK", market="HK"))

    assert captured["akshare_symbol"] == "01810", f"港股应归一为 01810，实际 {captured}"
    assert captured["akshare_market"] == "HK"
    assert captured["save_market"] == "HK", "落库 market 不能硬编码为 CN"
    assert captured["save_symbols"] == ["01810"]
    assert "tushare_called" not in captured, "港股不应调用只覆盖A股的 Tushare 新闻接口"
    assert stats.successful_saves == 1


def test_worker_sync_a_share_unchanged():
    """后台同步的A股路径保持原有行为"""
    service = NewsDataSyncService()
    captured = {}

    async def fake_source(symbol, hours_back, max_news, market="CN"):
        captured.setdefault("markets", []).append(market)
        captured["symbol"] = symbol
        return []

    async def fake_get_service():
        return MagicMock()

    with patch.object(service, "_sync_akshare_news", side_effect=fake_source), \
            patch.object(service, "_sync_realtime_news", side_effect=fake_source), \
            patch.object(service, "_sync_tushare_news", side_effect=fake_source), \
            patch.object(service, "_get_news_service", side_effect=fake_get_service):
        asyncio.run(service.sync_stock_news("600519"))

    assert captured["symbol"] == "600519"
    assert captured["markets"] == ["CN", "CN", "CN"], \
        f"A股应调用全部三个数据源且 market=CN，实际 {captured['markets']}"


def test_gate_failure_message_is_short_enough_to_downgrade():
    """全部新闻不相关时返回的失败文案必须足够短，以触发新闻分析师的降级判断"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())
    analyzer.toolkit.get_realtime_stock_news.invoke.return_value = ""
    analyzer.toolkit.get_google_news.invoke.return_value = ""
    analyzer.toolkit.get_global_news_openai.invoke.return_value = ""

    def fake_db(stock_code, max_news, market=None, company_name=None):
        analyzer._last_gate_stats = {
            "original_count": 12,
            "filtered_count": 0,
            "company_name": XIAOMI_NAME,
        }
        return ""

    with patch.object(analyzer, "_get_news_from_database", side_effect=fake_db), \
            patch.object(analyzer, "_sync_hk_news_from_akshare", return_value=False):
        result = analyzer._get_hk_share_news("01810.HK", max_news=10, company_name=XIAOMI_NAME)

    assert "相关性过滤" in result, f"应返回明确的相关性失败文案，实际: {result}"
    assert "12" in result, "文案应包含被拦截的候选数量"
    assert len(result.strip()) < 100, (
        f"文案需短于100字符才能触发新闻分析师降级，实际 {len(result.strip())}"
    )


if __name__ == "__main__":
    tests = [
        test_path1_database_hit_keeps_hk_market,
        test_path2_db_miss_then_akshare_sync,
        test_path3_sync_failure_falls_back_to_realtime,
        test_path4_realtime_chinese_news_routes_by_market,
        test_path5_google_news_fallback,
        test_path6_worker_sync_routes_by_market,
        test_worker_sync_a_share_unchanged,
        test_gate_failure_message_is_short_enough_to_downgrade,
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
