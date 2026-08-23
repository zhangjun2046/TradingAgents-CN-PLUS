#!/usr/bin/env python3
"""
新闻落库与查询的市场隔离测试

验证：
1. _standardize_news_data 同时维护 symbols / markets 数组
2. 写入改用 UpdateOne + $addToSet：同一 URL 被不同股票命中时只累加关联，不产生重复文档、不触发 E11000
3. 过滤条件仍是 (url, title, publish_time)，与既有唯一索引一致
4. unified_news_tool 的数据库查询带上市场维度，market=HK 不会命中 CN 数据
5. 数据库查询不再保留"不限时间"的宽松兜底查询，避免捞出历史脏数据

全部使用 mock，不连接真实 MongoDB。
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.news_data_service import NewsDataService  # noqa: E402
from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer  # noqa: E402


def _make_news(symbol, title="小米集团回购公司股份", url="https://example.com/a"):
    return {
        "symbol": symbol,
        "title": title,
        "content": "小米集团公告称……",
        "url": url,
        "source": "东方财富",
        "publish_time": "2026-08-20 10:00:00",
    }


def test_standardize_keeps_symbols_and_markets_arrays():
    """标准化结果必须同时含 symbols 与 markets 数组"""
    service = NewsDataService()
    now = datetime.utcnow()

    doc = service._standardize_news_data(_make_news("01810"), "akshare", "HK", now)

    assert doc["symbol"] == "01810"
    assert doc["market"] == "HK"
    assert doc["symbols"] == ["01810"], f"symbols 应含主代码，实际 {doc['symbols']}"
    assert doc["markets"] == ["HK"], f"markets 应含真实市场，实际 {doc.get('markets')}"


def test_standardize_merges_existing_arrays():
    """已带 symbols / markets 的数据不应丢失原有关联"""
    service = NewsDataService()
    now = datetime.utcnow()

    news = _make_news("01810")
    news["symbols"] = ["00700"]
    news["markets"] = ["CN"]

    doc = service._standardize_news_data(news, "akshare", "HK", now)

    assert doc["symbols"] == ["01810", "00700"]
    assert doc["markets"] == ["HK", "CN"]


def test_upsert_uses_addtoset_and_stable_filter():
    """写操作必须是 UpdateOne + $addToSet，过滤条件保持 (url, title, publish_time)"""
    service = NewsDataService()
    now = datetime.utcnow()

    doc = service._standardize_news_data(_make_news("01810"), "akshare", "HK", now)
    operation = service._build_upsert_operation(doc, now)

    filter_query = operation._filter
    update = operation._doc

    assert set(filter_query.keys()) == {"url", "title", "publish_time"}, \
        f"过滤条件必须与既有唯一索引一致，实际 {list(filter_query.keys())}"
    assert operation._upsert is True

    assert "$addToSet" in update, "必须用 $addToSet 累加关联数组"
    assert update["$addToSet"]["symbols"] == {"$each": ["01810"]}
    assert update["$addToSet"]["markets"] == {"$each": ["HK"]}

    # 关联数组不能同时出现在 $set 中，否则会覆盖其他股票的关联
    assert "symbols" not in update["$set"]
    assert "markets" not in update["$set"]
    assert update["$set"]["market"] == "HK"
    assert "created_at" in update["$setOnInsert"]


def test_same_url_across_stocks_does_not_duplicate():
    """同一篇新闻被 A 股与港股分别命中时，只更新同一文档并累加关联"""
    service = NewsDataService()
    now = datetime.utcnow()

    hk_doc = service._standardize_news_data(_make_news("01810"), "akshare", "HK", now)
    cn_doc = service._standardize_news_data(_make_news("600519"), "akshare", "CN", now)

    hk_op = service._build_upsert_operation(hk_doc, now)
    cn_op = service._build_upsert_operation(cn_doc, now)

    assert hk_op._filter == cn_op._filter, "同一 URL/标题/时间应命中同一文档，不产生重复"
    assert hk_op._doc["$addToSet"]["symbols"] == {"$each": ["01810"]}
    assert cn_op._doc["$addToSet"]["symbols"] == {"$each": ["600519"]}
    assert cn_op._doc["$addToSet"]["markets"] == {"$each": ["CN"]}


def test_save_news_data_sync_uses_bulk_update():
    """save_news_data_sync 应提交 UpdateOne 批量操作，且不抛 E11000"""
    from pymongo import UpdateOne

    service = NewsDataService()

    fake_collection = MagicMock()
    fake_result = MagicMock()
    fake_result.upserted_count = 1
    fake_result.modified_count = 1
    fake_collection.bulk_write.return_value = fake_result

    fake_db = MagicMock()
    fake_db.stock_news = fake_collection

    with patch("app.core.database.get_mongo_db_sync", return_value=fake_db):
        saved = service.save_news_data_sync(
            news_data=[_make_news("01810"), _make_news("01810", url="https://example.com/b")],
            data_source="akshare",
            market="HK",
        )

    assert saved == 2
    operations = fake_collection.bulk_write.call_args.args[0]
    assert len(operations) == 2
    assert all(isinstance(op, UpdateOne) for op in operations), "必须使用 UpdateOne 而非 ReplaceOne"
    assert all(op._doc["$addToSet"]["markets"] == {"$each": ["HK"]} for op in operations)


def _capture_db_queries(analyzer, stock_code, market, docs):
    """跑一遍数据库查询分支，返回实际发出的 query 列表"""
    queries = []

    class FakeCursor:
        def __init__(self, result):
            self._result = result

        def sort(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def __iter__(self):
            return iter(self._result)

    class FakeCollection:
        def find(self, query):
            queries.append(query)
            return FakeCursor(docs)

    fake_db = MagicMock()
    fake_db.stock_news = FakeCollection()
    fake_client = MagicMock()
    fake_client.get_database.return_value = fake_db

    with patch(
        "tradingagents.dataflows.cache.app_adapter.get_mongodb_client",
        return_value=fake_client,
    ):
        report = analyzer._get_news_from_database(
            stock_code, max_news=5, market=market, company_name="小米集团"
        )

    return queries, report


def test_database_query_includes_market_dimension():
    """数据库查询必须带市场维度，并且不含无时间限制的兜底查询"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    queries, _ = _capture_db_queries(analyzer, "01810.HK", "HK", [])

    assert queries, "应至少发起一次查询"
    for query in queries:
        assert "publish_time" in query, f"查询必须带时间范围，实际 {query}"
        assert "$or" in query, f"查询必须带市场维度，实际 {query}"
        assert query["$or"] == [{"markets": "HK"}, {"market": "HK"}]

    symbol_values = [q.get("symbol") or q.get("symbols") for q in queries]
    assert all(value == "01810" for value in symbol_values), \
        f"港股查询码应为 01810，实际 {symbol_values}"


def test_database_query_filters_out_other_market_docs():
    """即使数据库返回了 CN 的脏数据，相关性闸门也会把它拦掉"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    dirty_docs = [
        {
            "title": "中欧潜力价值灵活配置混合A(001810)基金份额净值公告",
            "content": "该基金今日单位净值……",
            "symbol": "001810",
            "market": "CN",
            "source": "东方财富",
            "publish_time": datetime(2026, 8, 20, 10, 0, 0),
        }
    ]

    _, report = _capture_db_queries(analyzer, "01810.HK", "HK", dirty_docs)

    assert report == "", "命中的基金脏数据应被相关性闸门拦掉，不能生成报告"
    assert analyzer._last_gate_stats["original_count"] == 1
    assert analyzer._last_gate_stats["filtered_count"] == 0


def test_database_query_keeps_relevant_docs():
    """真实相关的港股新闻应正常生成报告"""
    analyzer = UnifiedNewsAnalyzer(toolkit=MagicMock())

    docs = [
        {
            "title": "小米集团获准回购公司股份",
            "content": "小米集团公告，董事会通过回购议案。",
            "symbol": "01810",
            "market": "HK",
            "markets": ["HK"],
            "source": "东方财富",
            "publish_time": datetime(2026, 8, 20, 10, 0, 0),
            "sentiment": "positive",
        }
    ]

    _, report = _capture_db_queries(analyzer, "01810.HK", "HK", docs)

    assert "小米集团获准回购公司股份" in report
    assert analyzer._last_gate_stats["filtered_count"] == 1


if __name__ == "__main__":
    tests = [
        test_standardize_keeps_symbols_and_markets_arrays,
        test_standardize_merges_existing_arrays,
        test_upsert_uses_addtoset_and_stable_filter,
        test_same_url_across_stocks_does_not_duplicate,
        test_save_news_data_sync_uses_bulk_update,
        test_database_query_includes_market_dimension,
        test_database_query_filters_out_other_market_docs,
        test_database_query_keeps_relevant_docs,
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
