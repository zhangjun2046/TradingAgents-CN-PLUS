#!/usr/bin/env python3
"""报告分享链接 API：创建、公开读取、过期与撤销。"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.routers import reports as reports_router
from app.routers.auth_db import get_current_user
from app.services.report_share_service import order_report_modules, serialize_public_report


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeUpdateResult:
    def __init__(self, modified_count):
        self.modified_count = modified_count
        self.matched_count = modified_count


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
            if "$gt" in expected:
                if actual is None or not (actual > expected["$gt"]):
                    return False
            elif "$in" in expected:
                allowed = expected["$in"]
                if isinstance(actual, list):
                    if not any(item in allowed for item in actual):
                        return False
                elif actual not in allowed:
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
    if "$inc" in update:
        for key, amount in update["$inc"].items():
            doc[key] = (doc.get(key) or 0) + amount


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [dict(item) for item in (docs or [])]

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if _match(doc, query):
                return dict(doc)
        return None

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

    async def create_index(self, *args, **kwargs):
        return "ok"


class FakeDB:
    def __init__(self, reports=None):
        self.analysis_reports = FakeCollection(reports)
        self.analysis_tasks = FakeCollection()
        self.report_shares = FakeCollection()

    def __getitem__(self, name):
        return getattr(self, name)


SAMPLE_OID = ObjectId("507f1f77bcf86cd799439011")
SAMPLE_REPORT = {
    "_id": SAMPLE_OID,
    "analysis_id": "000001_20251014_120000",
    "stock_symbol": "000001",
    "stock_name": "平安银行",
    "analysis_date": "2025-10-14",
    "status": "completed",
    "created_at": datetime(2025, 10, 14, 4, 0, 0),
    "updated_at": datetime(2025, 10, 14, 4, 30, 0),
    "summary": "综合偏多，建议关注。",
    "recommendation": "谨慎买入",
    "risk_level": "中等",
    "confidence_score": 0.72,
    "key_points": ["基本面稳健"],
    "tokens_used": 12345,
    "execution_time": 88,
    "task_id": "task-001",
    "reports": {
        "final_trade_decision": "买入，目标价 12.5。",
        "market_report": "均线多头排列。",
        "empty_module": "   ",
    },
}


def create_app(with_auth: bool = True):
    app = FastAPI()
    app.include_router(reports_router.router)
    if with_auth:
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "user-1",
            "username": "tester",
            "is_admin": True,
            "roles": ["admin"],
        }
    return app


@pytest.fixture()
def fake_db():
    return FakeDB([SAMPLE_REPORT])


@pytest.fixture()
def client(fake_db):
    app = create_app(with_auth=True)
    with patch("app.services.report_share_service.get_mongo_db", return_value=fake_db), \
         patch("app.routers.reports.get_stock_name", return_value="平安银行"):
        with TestClient(app) as test_client:
            yield test_client, fake_db


def test_order_report_modules_skips_empty_and_follows_order():
    ordered = order_report_modules(SAMPLE_REPORT["reports"])
    assert list(ordered.keys()) == ["market_report", "final_trade_decision"]
    assert "empty_module" not in ordered


def test_serialize_public_report_strips_sensitive_fields():
    public = serialize_public_report({
        "id": "secret-id",
        "stock_symbol": "000001",
        "stock_name": "平安银行",
        "analysis_date": "2025-10-14",
        "created_at": "2025-10-14T12:00:00+08:00",
        "recommendation": "谨慎买入",
        "risk_level": "中等",
        "confidence_score": 0.72,
        "summary": "摘要",
        "key_points": ["要点"],
        "reports": SAMPLE_REPORT["reports"],
        "tokens_used": 999,
        "execution_time": 10,
        "source": "internal",
        "task_id": "task-001",
    })
    assert "tokens_used" not in public
    assert "execution_time" not in public
    assert "task_id" not in public
    assert "source" not in public
    assert public["stock_symbol"] == "000001"
    assert list(public["reports"].keys()) == ["market_report", "final_trade_decision"]


def test_create_share_and_public_read_without_auth(client):
    auth_client, fake_db = client
    created = auth_client.post(f"/api/reports/{SAMPLE_OID}/share", json={"expires_days": 7})
    assert created.status_code == 200
    body = created.json()
    assert body["success"] is True
    token = body["data"]["token"]
    assert body["data"]["path"] == f"/s/{token}"

    public_app = create_app(with_auth=False)
    with patch("app.services.report_share_service.get_mongo_db", return_value=fake_db), \
         patch("app.routers.reports.get_stock_name", return_value="平安银行"):
        with TestClient(public_app) as public_client:
            resp = public_client.get(f"/api/reports/share/{token}")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["stock_name"] == "平安银行"
            assert data["recommendation"] == "谨慎买入"
            assert "tokens_used" not in data
            assert "execution_time" not in data
            assert "market_report" in data["reports"]


def test_reuse_existing_share_token(client):
    auth_client, _fake_db = client
    first = auth_client.post(f"/api/reports/{SAMPLE_OID}/share", json={}).json()["data"]["token"]
    second = auth_client.post(f"/api/reports/{SAMPLE_OID}/share", json={}).json()["data"]["token"]
    assert first == second


def test_unauthenticated_cannot_create_share(fake_db):
    app = create_app(with_auth=False)
    with patch("app.services.report_share_service.get_mongo_db", return_value=fake_db):
        with TestClient(app) as public_client:
            resp = public_client.post(f"/api/reports/{SAMPLE_OID}/share", json={})
            assert resp.status_code == 401


def test_revoke_makes_public_link_unreadable(client):
    auth_client, fake_db = client
    token = auth_client.post(f"/api/reports/{SAMPLE_OID}/share", json={}).json()["data"]["token"]
    revoked = auth_client.delete(f"/api/reports/{SAMPLE_OID}/share")
    assert revoked.status_code == 200
    assert revoked.json()["data"]["revoked"] >= 1

    with patch("app.services.report_share_service.get_mongo_db", return_value=fake_db), \
         patch("app.routers.reports.get_stock_name", return_value="平安银行"):
        with TestClient(create_app(with_auth=False)) as public_client:
            resp = public_client.get(f"/api/reports/share/{token}")
            assert resp.status_code == 404


def test_expired_share_returns_404(client):
    auth_client, fake_db = client
    token = auth_client.post(f"/api/reports/{SAMPLE_OID}/share", json={}).json()["data"]["token"]
    fake_db.report_shares.docs[0]["expires_at"] = datetime.utcnow() - timedelta(seconds=1)

    with patch("app.services.report_share_service.get_mongo_db", return_value=fake_db), \
         patch("app.routers.reports.get_stock_name", return_value="平安银行"):
        with TestClient(create_app(with_auth=False)) as public_client:
            resp = public_client.get(f"/api/reports/share/{token}")
            assert resp.status_code == 404


def test_regenerate_invalidates_old_token(client):
    auth_client, fake_db = client
    old_token = auth_client.post(f"/api/reports/{SAMPLE_OID}/share", json={}).json()["data"]["token"]
    new_token = auth_client.post(
        f"/api/reports/{SAMPLE_OID}/share",
        json={"regenerate": True},
    ).json()["data"]["token"]
    assert old_token != new_token

    with patch("app.services.report_share_service.get_mongo_db", return_value=fake_db), \
         patch("app.routers.reports.get_stock_name", return_value="平安银行"):
        with TestClient(create_app(with_auth=False)) as public_client:
            assert public_client.get(f"/api/reports/share/{old_token}").status_code == 404
            assert public_client.get(f"/api/reports/share/{new_token}").status_code == 200


def test_missing_report_cannot_create_share(fake_db):
    app = create_app(with_auth=True)
    with patch("app.services.report_share_service.get_mongo_db", return_value=fake_db), \
         patch("app.routers.reports.get_stock_name", return_value="平安银行"):
        with TestClient(app) as auth_client:
            resp = auth_client.post("/api/reports/does-not-exist/share", json={})
            assert resp.status_code == 404
