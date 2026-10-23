"""测试用的最小内存版 Mongo（支持本单元用到的查询子集），避免依赖真实数据库。"""
from __future__ import annotations

from bson import ObjectId


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeUpdateResult:
    def __init__(self, modified_count):
        self.modified_count = modified_count
        self.matched_count = modified_count


class FakeDeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


def _get_path(doc, key):
    if "." not in key:
        return doc.get(key)
    current = doc
    for part in key.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def _match(doc, query):
    if not query:
        return True
    if "$or" in query:
        rest = {k: v for k, v in query.items() if k != "$or"}
        if rest and not _match(doc, rest):
            return False
        return any(_match(doc, sub) for sub in query["$or"])
    for key, expected in query.items():
        actual = _get_path(doc, key)
        if isinstance(expected, dict) and any(op.startswith("$") for op in expected):
            for op, value in expected.items():
                if op == "$gt":
                    if actual is None or not (actual > value):
                        return False
                elif op == "$in":
                    if isinstance(actual, list):
                        if not any(item in value for item in actual):
                            return False
                    elif actual not in value:
                        return False
                elif op == "$exists":
                    if (key in doc) != bool(value):
                        return False
                elif op == "$ne":
                    if actual == value:
                        return False
                elif op == "$regex":
                    import re
                    if actual is None or not re.search(value, str(actual), re.I):
                        return False
                else:
                    return False
        else:
            if isinstance(actual, list):
                if expected not in actual:
                    return False
            elif actual != expected:
                return False
    return True


def _apply_update(doc, update):
    if "$set" in update:
        doc.update(update["$set"])
    if "$unset" in update:
        for key in update["$unset"]:
            doc.pop(key, None)
    if "$inc" in update:
        for key, amount in update["$inc"].items():
            doc[key] = (doc.get(key) or 0) + amount


class FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key, direction=1):
        self._docs.sort(key=lambda d: (d.get(key) is None, d.get(key)), reverse=direction < 0)
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return dict(next(self._iter))
        except StopIteration:
            raise StopAsyncIteration


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [dict(item) for item in (docs or [])]

    async def find_one(self, query=None, projection=None):
        for doc in self.docs:
            if _match(doc, query or {}):
                return dict(doc)
        return None

    def find(self, query=None, projection=None):
        return FakeCursor([d for d in self.docs if _match(d, query or {})])

    async def count_documents(self, query=None):
        return sum(1 for d in self.docs if _match(d, query or {}))

    async def insert_one(self, doc):
        stored = dict(doc)
        if "_id" not in stored:
            stored["_id"] = ObjectId()
        self.docs.append(stored)
        return FakeInsertResult(stored["_id"])

    async def update_one(self, query, update):
        for doc in self.docs:
            if _match(doc, query):
                _apply_update(doc, update)
                return FakeUpdateResult(1)
        return FakeUpdateResult(0)

    async def update_many(self, query, update):
        count = 0
        for doc in self.docs:
            if _match(doc, query):
                _apply_update(doc, update)
                count += 1
        return FakeUpdateResult(count)

    async def delete_one(self, query):
        for i, doc in enumerate(self.docs):
            if _match(doc, query):
                del self.docs[i]
                return FakeDeleteResult(1)
        return FakeDeleteResult(0)

    async def create_index(self, *args, **kwargs):
        return "ok"


class FakeDB:
    def __init__(self, reports=None, tasks=None):
        self.analysis_reports = FakeCollection(reports)
        self.analysis_tasks = FakeCollection(tasks)
        self.report_shares = FakeCollection()

    def __getitem__(self, name):
        return getattr(self, name)
