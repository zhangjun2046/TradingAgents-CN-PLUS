#!/usr/bin/env python3
"""
统一新闻工具港股分支烟雾测试

验证：
1. _sync_hk_news_from_akshare 不会对 stock_code 做 zfill（保持 06030 5 位代码原样传递）
2. _get_hk_share_news 在数据库命中时直接返回，不再调用其他下游
3. _get_hk_share_news 在数据库未命中时会触发 _sync_hk_news_from_akshare 并重新查库
4. 新增的工具描述中包含港股的"数据库 + AKShare"关键字
5. 港股代码标准化只剥离 .HK，不改变位数

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


def _make_fake_news_df(rows=3):
    return FakeDataFrame(
        [
            {
                "新闻标题": f"中信证券港股动态第{i}条这是足够长的标题",
                "新闻内容": f"内容{i}：港股市场出现重大消息……",
                "新闻链接": f"https://example.com/hk/{i}",
                "发布时间": "2026-05-08 10:00:00",
                "文章来源": "东方财富",
            }
            for i in range(rows)
        ]
    )


def test_clean_code_keeps_5_digits():
    """港股 06030.HK 应该被剥离成 06030（不应该被 zfill 到 006030）"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    captured = {}

    def fake_stock_news_em(symbol):
        captured["symbol"] = symbol
        return _make_fake_news_df()

    fake_ak_module = MagicMock()
    fake_ak_module.stock_news_em = fake_stock_news_em

    fake_news_service = MagicMock()
    fake_news_service.save_news_data_sync.return_value = 3

    with _patch_external_deps(fake_ak_module, fake_news_service):
        ok = analyzer._sync_hk_news_from_akshare("06030.HK", max_news=10)

    assert ok is True, "应当成功同步"
    assert captured["symbol"] == "06030", (
        f"港股代码应保持原样 5 位 06030，但被传成了 {captured['symbol']}（说明走了 zfill）"
    )

    call_kwargs = fake_news_service.save_news_data_sync.call_args.kwargs
    assert call_kwargs["market"] == "HK", "港股新闻保存时 market 必须为 HK"
    assert call_kwargs["data_source"] == "akshare"
    saved_news = call_kwargs["news_data"]
    assert len(saved_news) == 3
    assert all(item["symbol"] == "06030" for item in saved_news), \
        "保存到 DB 时所有 symbol 字段都应是 06030"


def test_clean_code_keeps_4_digits():
    """4 位港股代码 0700.HK 应保持 4 位，不被 zfill"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    captured = {}

    def fake_stock_news_em(symbol):
        captured["symbol"] = symbol
        return _make_fake_news_df(2)

    fake_ak_module = MagicMock()
    fake_ak_module.stock_news_em = fake_stock_news_em

    fake_news_service = MagicMock()
    fake_news_service.save_news_data_sync.return_value = 2

    with _patch_external_deps(fake_ak_module, fake_news_service):
        ok = analyzer._sync_hk_news_from_akshare("0700.HK", max_news=10)

    assert ok is True
    assert captured["symbol"] == "0700", (
        f"4 位港股代码应保持 0700，但被传成 {captured['symbol']}"
    )


def test_short_titles_filtered():
    """标题 < 5 字符的噪声新闻应被过滤掉，避免污染数据库"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    df = FakeDataFrame(
        [
            {"新闻标题": "公告", "新闻内容": "内容1", "新闻链接": "u1", "发布时间": "2026-05-08", "文章来源": "东方财富"},
            {"新闻标题": "短", "新闻内容": "内容2", "新闻链接": "u2", "发布时间": "2026-05-08", "文章来源": "东方财富"},
            {"新闻标题": "正常长度的港股新闻标题", "新闻内容": "内容3", "新闻链接": "u3", "发布时间": "2026-05-08", "文章来源": "东方财富"},
        ]
    )

    fake_ak_module = MagicMock()
    fake_ak_module.stock_news_em = lambda symbol: df

    fake_news_service = MagicMock()
    fake_news_service.save_news_data_sync.return_value = 1

    with _patch_external_deps(fake_ak_module, fake_news_service):
        ok = analyzer._sync_hk_news_from_akshare("06030.HK", max_news=10)

    assert ok is True
    saved_news = fake_news_service.save_news_data_sync.call_args.kwargs["news_data"]
    assert len(saved_news) == 1, f"只应保存 1 条长标题新闻，实际 {len(saved_news)}"
    assert saved_news[0]["title"] == "正常长度的港股新闻标题"


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

    def fake_get_db(stock_code, max_news):
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
    assert analyzer._identify_stock_type("600519") == "A股"
    assert analyzer._identify_stock_type("AAPL") == "美股"


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


if __name__ == "__main__":
    tests = [
        test_clean_code_keeps_5_digits,
        test_clean_code_keeps_4_digits,
        test_short_titles_filtered,
        test_empty_dataframe_returns_false,
        test_get_hk_news_db_hit_short_circuits,
        test_get_hk_news_triggers_sync_when_db_empty,
        test_tool_description_mentions_db_and_akshare,
        test_identify_hk_stock,
        test_a_share_branch_unchanged,
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
