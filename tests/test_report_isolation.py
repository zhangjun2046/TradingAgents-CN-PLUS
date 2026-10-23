#!/usr/bin/env python3
"""报告按用户隔离：列表、详情、模块、下载、删除、分享均按 user_id 校验。"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime
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
from tests.fake_mongo_helper import FakeDB

USER_A = {"id": "uid-a", "username": "test_user_a", "is_admin": False, "roles": ["user"]}
USER_B = {"id": "uid-b", "username": "test_user_b", "is_admin": False, "roles": ["user"]}
ADMIN = {"id": "uid-admin", "username": "admin", "is_admin": True, "roles": ["admin"]}

OID_A = ObjectId("507f1f77bcf86cd799439011")
OID_B = ObjectId("507f1f77bcf86cd799439012")
OID_LEGACY = ObjectId("507f1f77bcf86cd799439013")


def _report(oid, analysis_id, task_id, user_id, **extra):
    doc = {
        "_id": oid,
        "analysis_id": analysis_id,
        "stock_symbol": "000001",
        "stock_name": "平安银行",
        "analysis_date": "2025-10-14",
        "status": "completed",
        "created_at": datetime(2025, 10, 14, 4, 0, 0),
        "updated_at": datetime(2025, 10, 14, 4, 30, 0),
        "summary": "摘要",
        "recommendation": "买入",
        "risk_level": "中等",
        "confidence_score": 0.7,
        "key_points": [],
        "task_id": task_id,
        "user_id": user_id,
        "reports": {"market_report": "均线多头排列。", "final_trade_decision": "买入"},
    }
    doc.update(extra)
    return doc


@pytest.fixture()
def env():
    db = FakeDB(
        reports=[
            _report(OID_A, "A_20251014", "task-a", "uid-a"),
            _report(OID_B, "B_20251014", "task-b", "uid-b"),
            # 无法回填的历史报告：仅管理员可见
            _report(OID_LEGACY, "L_20251014", "task-l", None, owner_unknown=True),
        ],
        tasks=[
            {"task_id": "task-a", "user_id": "uid-a"},
            {"task_id": "task-b", "user_id": "uid-b"},
        ],
    )
    current = {"user": USER_A}

    app = FastAPI()
    app.include_router(reports_router.router)
    app.dependency_overrides[get_current_user] = lambda: current["user"]

    with patch("app.services.report_share_service.get_mongo_db", return_value=db), \
         patch("app.routers.reports.get_mongo_db", return_value=db), \
         patch("app.routers.reports.get_stock_name", return_value="平安银行"):
        with TestClient(app) as client:
            yield client, db, current


def _as(current, user):
    current["user"] = user


def _list_ids(client):
    resp = client.get("/api/reports/list")
    assert resp.status_code == 200
    data = resp.json()["data"]
    return {r["analysis_id"] for r in data["reports"]}, data["total"]


def test_list_only_shows_own_reports(env):
    client, _db, current = env
    _as(current, USER_A)
    ids, total = _list_ids(client)
    assert ids == {"A_20251014"} and total == 1

    _as(current, USER_B)
    ids, total = _list_ids(client)
    assert ids == {"B_20251014"} and total == 1


def test_admin_sees_all_including_owner_unknown(env):
    client, _db, current = env
    _as(current, ADMIN)
    ids, total = _list_ids(client)
    assert ids == {"A_20251014", "B_20251014", "L_20251014"}
    assert total == 3


def test_owner_unknown_hidden_from_normal_users(env):
    client, _db, current = env
    _as(current, USER_A)
    assert client.get(f"/api/reports/{OID_LEGACY}/detail").status_code == 404
    _as(current, ADMIN)
    assert client.get(f"/api/reports/{OID_LEGACY}/detail").status_code == 200


@pytest.mark.parametrize("report_ref", [str(OID_A), "A_20251014", "task-a"])
def test_owner_can_read_own_report_by_any_id(env, report_ref):
    client, _db, current = env
    _as(current, USER_A)
    assert client.get(f"/api/reports/{report_ref}/detail").status_code == 200
    assert client.get(f"/api/reports/{report_ref}/content/market_report").status_code == 200
    assert client.get(f"/api/reports/{report_ref}/download?format=markdown").status_code == 200


@pytest.mark.parametrize("report_ref", [str(OID_A), "A_20251014", "task-a"])
def test_other_user_gets_404_everywhere(env, report_ref):
    client, db, current = env
    _as(current, USER_B)
    assert client.get(f"/api/reports/{report_ref}/detail").status_code == 404
    assert client.get(f"/api/reports/{report_ref}/content/market_report").status_code == 404
    assert client.get(f"/api/reports/{report_ref}/download?format=markdown").status_code == 404
    assert client.get(f"/api/reports/{report_ref}/download?format=json").status_code == 404
    assert client.post(f"/api/reports/{report_ref}/share", json={}).status_code == 404
    assert client.get(f"/api/reports/{report_ref}/share").status_code == 404
    assert client.delete(f"/api/reports/{report_ref}/share").status_code == 404
    assert client.delete(f"/api/reports/{report_ref}").status_code == 404
    # 他人的报告没有被误删
    assert any(d["_id"] == OID_A for d in db.analysis_reports.docs)


def test_delete_own_report_only_removes_it(env):
    client, db, current = env
    _as(current, USER_A)
    assert client.delete(f"/api/reports/{OID_A}").status_code == 200
    remaining = {d["_id"] for d in db.analysis_reports.docs}
    assert remaining == {OID_B, OID_LEGACY}


def test_share_flow_for_owner_and_isolation_for_others(env):
    client, _db, current = env
    _as(current, USER_A)
    created = client.post(f"/api/reports/{OID_A}/share", json={})
    assert created.status_code == 200
    token = created.json()["data"]["token"]
    assert client.get(f"/api/reports/{OID_A}/share").json()["data"]["token"] == token

    # 他人不能查询 / 撤销 / 重新生成
    _as(current, USER_B)
    assert client.get(f"/api/reports/{OID_A}/share").status_code == 404
    assert client.post(f"/api/reports/{OID_A}/share", json={"regenerate": True}).status_code == 404
    assert client.delete(f"/api/reports/{OID_A}/share").status_code == 404

    # 已有分享链接免登录仍可读取（公开路径不做归属校验）
    public_app = FastAPI()
    public_app.include_router(reports_router.router)
    with patch("app.services.report_share_service.get_mongo_db", return_value=_db), \
         patch("app.routers.reports.get_stock_name", return_value="平安银行"):
        with TestClient(public_app) as public_client:
            assert public_client.get(f"/api/reports/share/{token}").status_code == 200


def test_admin_can_share_any_report(env):
    client, _db, current = env
    _as(current, ADMIN)
    assert client.post(f"/api/reports/{OID_LEGACY}/share", json={}).status_code == 200


def test_task_fallback_respects_owner(env):
    """报告文档缺失、仅 analysis_tasks 里有结果时，同样按任务归属校验。"""
    client, db, current = env
    db.analysis_tasks.docs.append({
        "task_id": "task-only",
        "user_id": ObjectId("507f1f77bcf86cd799439099"),  # 旧数据可能存 ObjectId
        "stock_code": "000002",
        "created_at": datetime(2025, 10, 15),
        "result": {"analysis_id": "T_20251015", "reports": {"market_report": "内容"}},
    })
    _as(current, {"id": "507f1f77bcf86cd799439099", "username": "legacy", "is_admin": False})
    assert client.get("/api/reports/task-only/detail").status_code == 200
    _as(current, USER_B)
    assert client.get("/api/reports/task-only/detail").status_code == 404
    _as(current, ADMIN)
    assert client.get("/api/reports/task-only/detail").status_code == 200


# ---- 写入侧：新报告带 user_id ----

def _fake_result():
    return {
        "stock_code": "000001",
        "stock_symbol": "000001",
        "state": {"market_report": "x" * 50},
        "summary": "s",
        "decision": {},
    }


def test_save_report_writes_user_id_from_argument():
    from app.services.simple_analysis_service import SimpleAnalysisService

    db = FakeDB(tasks=[{"task_id": "t1", "user_id": "uid-task"}])
    service = SimpleAnalysisService.__new__(SimpleAnalysisService)
    with patch("app.services.simple_analysis_service.get_mongo_db", return_value=db):
        asyncio.run(service._save_analysis_result_web_style("t1", _fake_result(), user_id="uid-a"))
    saved = db.analysis_reports.docs[0]
    assert saved["user_id"] == "uid-a"
    assert "owner_unknown" not in saved


def test_save_report_falls_back_to_task_owner_then_unknown():
    from app.services.simple_analysis_service import SimpleAnalysisService

    db = FakeDB(tasks=[{"task_id": "t1", "user_id": "uid-task"}])
    service = SimpleAnalysisService.__new__(SimpleAnalysisService)

    class _NoMemory:
        async def get_task(self, _task_id):
            return None

    service.memory_manager = _NoMemory()
    async def _save_both():
        await service._save_analysis_result_web_style("t1", _fake_result())
        await service._save_analysis_result_web_style("t-missing", _fake_result())

    with patch("app.services.simple_analysis_service.get_mongo_db", return_value=db):
        asyncio.run(_save_both())

    by_task = {d["task_id"]: d for d in db.analysis_reports.docs}
    assert by_task["t1"]["user_id"] == "uid-task"
    assert by_task["t-missing"]["user_id"] is None
    assert by_task["t-missing"]["owner_unknown"] is True
