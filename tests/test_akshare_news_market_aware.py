#!/usr/bin/env python3
"""
AKShare Provider 新闻方法市场感知测试

验证三个新闻入口在传入 market 后使用正确的检索代码：
1. _get_stock_news_direct（Docker 环境直连东方财富）
2. get_stock_news_sync（同步 DataFrame）
3. get_stock_news（异步结构化列表）

核心断言：
- market="HK" 时检索码为 01810（5位），绝不能是 001810
- market="CN" 时检索码为 001810 / 600519（6位）
- 港股检索码若出现6位纯数字，必须 fail-fast 抛错
- 落库 symbol 与检索码一致，且带上真实 market

全部使用 mock，不访问外网与数据库。
"""

import asyncio
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tradingagents.dataflows.providers.china.akshare import AKShareProvider  # noqa: E402


class FakeDataFrame:
    """最小 DataFrame 替身，仅实现被测代码用到的接口"""

    def __init__(self, rows):
        self._rows = list(rows)
        self.columns = list(rows[0].keys()) if rows else []
        self.shape = (len(self._rows), len(self.columns))

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


def _make_rows(n=2, title_prefix="小米集团相关新闻"):
    return [
        {
            "新闻标题": f"{title_prefix}第{i}条",
            "新闻内容": f"内容{i}",
            "新闻链接": f"https://example.com/{i}",
            "发布时间": "2026-08-20 10:00:00",
            "文章来源": "东方财富",
        }
        for i in range(n)
    ]


@contextmanager
def _patch_akshare(capture):
    """注入伪 akshare 模块，记录 stock_news_em 收到的 symbol"""
    fake_ak = types.ModuleType("akshare")

    def fake_stock_news_em(symbol):
        capture.append(symbol)
        return FakeDataFrame(_make_rows())

    fake_ak.stock_news_em = fake_stock_news_em
    with patch.dict("sys.modules", {"akshare": fake_ak}):
        yield


def _make_provider():
    """构造 provider 并强制标记为可用，避免真实依赖检查"""
    provider = AKShareProvider()
    provider.is_available = lambda: True
    return provider


def test_sync_news_hk_keeps_five_digits():
    """get_stock_news_sync 在 market=HK 时必须用 01810 检索"""
    provider = _make_provider()
    capture = []

    with _patch_akshare(capture):
        df = provider.get_stock_news_sync(symbol="01810", limit=5, market="HK")

    assert capture == ["01810"], f"港股应使用 01810 检索，实际 {capture}"
    assert df is not None and not df.empty
    assert "001810" not in capture, "港股检索码绝不能是基金代码 001810"


def test_sync_news_hk_accepts_suffixed_and_short_code():
    """01810.HK 与 1810 都应归一为 01810"""
    for raw in ["01810.HK", "1810", "1810.hk"]:
        provider = _make_provider()
        capture = []
        with _patch_akshare(capture):
            provider.get_stock_news_sync(symbol=raw, limit=5, market="HK")
        assert capture == ["01810"], f"输入 {raw} 应检索 01810，实际 {capture}"


def test_sync_news_cn_still_zfills_to_six():
    """A股行为保持不变：补齐到6位"""
    provider = _make_provider()
    capture = []

    with _patch_akshare(capture):
        provider.get_stock_news_sync(symbol="1810", limit=5, market="CN")

    assert capture == ["001810"], f"A股应补零到 001810，实际 {capture}"

    provider2 = _make_provider()
    capture2 = []
    with _patch_akshare(capture2):
        provider2.get_stock_news_sync(symbol="600519", limit=5, market="CN")
    assert capture2 == ["600519"]


def test_sync_news_defaults_to_code_format_detection():
    """不传 market 时按代码格式推断，5位数字视为港股"""
    provider = _make_provider()
    capture = []

    with _patch_akshare(capture):
        provider.get_stock_news_sync(symbol="01810", limit=5)

    assert capture == ["01810"], f"不传 market 时 01810 应被识别为港股，实际 {capture}"


def test_async_news_hk_symbol_and_market_persisted():
    """异步方法的检索码与落库 symbol/market 必须一致"""
    provider = _make_provider()
    capture = []

    with _patch_akshare(capture):
        news_list = asyncio.run(
            provider.get_stock_news(symbol="1810.HK", limit=5, market="HK")
        )

    assert capture == ["01810"], f"异步方法应使用 01810 检索，实际 {capture}"
    assert news_list, "应返回结构化新闻列表"
    for item in news_list:
        assert item["symbol"] == "01810", f"落库 symbol 应为 01810，实际 {item['symbol']}"
        assert item["market"] == "HK", f"落库 market 应为 HK，实际 {item.get('market')}"


def test_direct_news_hk_keyword():
    """_get_stock_news_direct 也必须按市场归一（只验证入参解析，不发请求）"""
    provider = _make_provider()

    query_symbol, market = provider._resolve_news_query("1810.HK", "HK")
    assert query_symbol == "01810"
    assert market == "HK"

    query_symbol_cn, market_cn = provider._resolve_news_query("1810", "CN")
    assert query_symbol_cn == "001810"
    assert market_cn == "CN"


def test_resolve_news_query_fail_fast_on_hk_zfill():
    """港股查询码被补成6位时必须抛错，而不是静默去查基金"""
    provider = _make_provider()

    # 通过打桩 normalize_symbol 模拟"未来某次改动又把港股补零"的回归
    import tradingagents.dataflows.providers.china.akshare as akshare_module

    original_import = akshare_module.AKShareProvider._resolve_news_query

    def broken_normalize(symbol, market):
        return "001810"

    with patch("tradingagents.utils.stock_utils.normalize_symbol", broken_normalize):
        try:
            original_import(provider, "01810", "HK")
        except ValueError as e:
            assert "非法补零" in str(e), f"错误信息应说明非法补零，实际: {e}"
        else:
            raise AssertionError("港股查询码为6位纯数字时必须抛 ValueError")


def test_resolve_news_query_rejects_unknown_market():
    """无法确定市场时必须抛错，不能默认按A股补零"""
    provider = _make_provider()

    try:
        provider._resolve_news_query("不是代码", None)
    except ValueError:
        pass
    else:
        raise AssertionError("无法识别的代码应抛 ValueError")


if __name__ == "__main__":
    tests = [
        test_sync_news_hk_keeps_five_digits,
        test_sync_news_hk_accepts_suffixed_and_short_code,
        test_sync_news_cn_still_zfills_to_six,
        test_sync_news_defaults_to_code_format_detection,
        test_async_news_hk_symbol_and_market_persisted,
        test_direct_news_hk_keyword,
        test_resolve_news_query_fail_fast_on_hk_zfill,
        test_resolve_news_query_rejects_unknown_market,
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
