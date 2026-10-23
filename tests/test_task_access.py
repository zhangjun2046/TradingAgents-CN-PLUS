#!/usr/bin/env python3
"""P1.6 分析任务归属校验：status / result / mark-failed / delete 按 user_id 校验，
tasks/all 与僵尸任务接口仅管理员可访问（本地桩 _require_admin_local）。"""
from __future__ import annotations

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

from app.routers import analysis as analysis_router
from app.routers.auth_db import get_current_user
from tests.fake_mongo_helper import FakeDB

USER_A = {"id": "uid-a", "username": "test_user_a", "is_admin": False, "roles": ["user"]}
USER_B = {"id": "uid-b", "username": "test_user_b", "is_admin": False, "roles": ["user"]}
ADMIN = {"id": "uid-admin", "username": "admin", "is_admin": True, "roles": ["admin"]}
# 用户名不是 "admin" 但具备管理员标记：验证语义已由 username 判断改为 is_admin
OPS_ADMIN = {"id": "uid-ops", "username": "ops", "is_admin": True, "roles": ["admin"]}

OID_USER = ObjectId("507f1f77bcf86cd799439021")
USER_OID = {"id": str(OID_USER), "username": "oid_user", "is_admin": False, "roles": ["user"]}
USER_INT = {"id": "123", "username": "int_user", "is_admin": False, "roles": ["user"]}


class _FakeMemoryManager:
    def __init__(self):
        self.removed = []

    async def remove_task(self, task_id):
        self.removed.append(task_id)

    async def update_task_status(self, **kwargs):
        return None


class _FakeAnalysisService:
    """只记录调用，用来证明归属校验发生在读取任务数据之前。"""

    def __init__(self):
        self.status_calls = []
        self.memory_manager = _FakeMemoryManager()

    async def get_task_status(self, task_id):
        self.status_calls.append(task_id)
        return {"task_id": task_id, "status": "running", "progress": 10}

    async def get_zombie_tasks(self, max_running_hours=2):
        return [{"task_id": "zombie-1"}]

    async def cleanup_zombie_tasks(self, max_running_hours=2):
        return {"total_cleaned": 1}

    async def list_all_tasks(self, status=None, limit=20, offset=0):
        return [{"task_id": "task-a"}, {"task_id": "task-b"}]


def _report(task_id, user_id):
    return {
        "_id": ObjectId(),
        "analysis_id": f"{task_id}_20251014",
        "stock_symbol": "000001",
        "analysis_date": "2025-10-14",
        "status": "completed",
        "created_at": datetime(2025, 10, 14, 4, 0, 0),
        "updated_at": datetime(2025, 10, 14, 4, 30, 0),
        "summary": "摘要",
        "recommendation": "买入",
        "reports": {"market_report": "均线多头排列。"},
        "task_id": task_id,
        "user_id": user_id,
    }


@pytest.fixture()
def env():
    db = FakeDB(
        reports=[
            # 只有报告、没有任务记录：回退到 analysis_reports 归属
            _report("report-only-a", "uid-a"),
        ],
        tasks=[
            {"task_id": "task-a", "user_id": "uid-a", "status": "running", "created_at": datetime(2025, 10, 14)},
            {"task_id": "task-b", "user_id": "uid-b", "status": "running", "created_at": datetime(2025, 10, 14)},
            # user_id 以 ObjectId / 整数存储，比对必须统一转字符串
            {"task_id": "task-oid", "user_id": OID_USER, "status": "running", "created_at": datetime(2025, 10, 14)},
            {"task_id": "task-int", "user_id": 123, "status": "running", "created_at": datetime(2025, 10, 14)},
        ],
    )
    # task-a 的结果存在报告集合里，用于 result 接口
    db.analysis_reports.docs.append(_report("task-a", "uid-a"))

    service = _FakeAnalysisService()
    current = {"user": USER_A}

    app = FastAPI()
    app.include_router(analysis_router.router, prefix="/api/analysis")
    app.dependency_overrides[get_current_user] = lambda: current["user"]

    with patch("app.core.database.get_mongo_db", return_value=db), \
         patch("app.routers.analysis.get_simple_analysis_service", return_value=service):
        with TestClient(app) as client:
            yield client, db, service, current


def _as(current, user):
    current["user"] = user


# ---------- 本人访问 ----------

def test_owner_can_read_own_status_and_result(env):
    client, _db, service, current = env
    _as(current, USER_A)

    status_resp = client.get("/api/analysis/tasks/task-a/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["task_id"] == "task-a"
    assert "task-a" in service.status_calls

    result_resp = client.get("/api/analysis/tasks/task-a/result")
    assert result_resp.status_code == 200
    assert result_resp.json()["data"]["summary"] == "摘要"


# ---------- 越权访问 ----------

def test_other_user_gets_404_for_status_and_result(env):
    client, _db, service, current = env
    _as(current, USER_B)

    assert client.get("/api/analysis/tasks/task-a/status").status_code == 404
    assert client.get("/api/analysis/tasks/task-a/result").status_code == 404
    # 校验必须发生在读取任务数据之前：服务层不应被调用
    assert service.status_calls == []


def test_other_user_cannot_mark_failed_or_delete(env):
    client, db, service, current = env
    _as(current, USER_B)

    assert client.post("/api/analysis/tasks/task-a/mark-failed").status_code == 404
    assert client.delete("/api/analysis/tasks/task-a").status_code == 404

    task = next(d for d in db.analysis_tasks.docs if d["task_id"] == "task-a")
    assert task["status"] == "running"  # 未被标记为失败
    assert service.memory_manager.removed == []  # 未从内存删除


def test_owner_can_mark_failed_and_delete_own_task(env):
    client, db, _service, current = env
    _as(current, USER_B)

    assert client.post("/api/analysis/tasks/task-b/mark-failed").status_code == 200
    task = next(d for d in db.analysis_tasks.docs if d["task_id"] == "task-b")
    assert task["status"] == "failed"

    assert client.delete("/api/analysis/tasks/task-b").status_code == 200
    assert all(d["task_id"] != "task-b" for d in db.analysis_tasks.docs)


def test_unknown_task_returns_404(env):
    client, _db, _service, current = env
    _as(current, USER_A)
    assert client.get("/api/analysis/tasks/not-exist/status").status_code == 404
    assert client.get("/api/analysis/tasks/not-exist/result").status_code == 404


# ---------- 回退与类型兼容 ----------

def test_fallback_to_report_owner_when_task_record_missing(env):
    client, _db, _service, current = env

    _as(current, USER_A)
    assert client.get("/api/analysis/tasks/report-only-a/status").status_code == 200

    _as(current, USER_B)
    assert client.get("/api/analysis/tasks/report-only-a/status").status_code == 404


def test_user_id_type_mismatch_is_normalized(env):
    client, _db, _service, current = env

    _as(current, USER_OID)
    assert client.get("/api/analysis/tasks/task-oid/status").status_code == 200
    assert client.get("/api/analysis/tasks/task-int/status").status_code == 404

    _as(current, USER_INT)
    assert client.get("/api/analysis/tasks/task-int/status").status_code == 200
    assert client.get("/api/analysis/tasks/task-oid/status").status_code == 404


# ---------- 管理员 ----------

def test_admin_can_access_any_task(env):
    client, _db, _service, current = env
    _as(current, ADMIN)

    assert client.get("/api/analysis/tasks/task-a/status").status_code == 200
    assert client.get("/api/analysis/tasks/task-b/status").status_code == 200
    assert client.get("/api/analysis/tasks/task-a/result").status_code == 200
    assert client.post("/api/analysis/tasks/task-b/mark-failed").status_code == 200
    assert client.delete("/api/analysis/tasks/task-a").status_code == 200


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/analysis/tasks/all"),
        ("get", "/api/analysis/admin/zombie-tasks"),
        ("post", "/api/analysis/admin/cleanup-zombie-tasks"),
    ],
)
def test_admin_only_endpoints_reject_normal_user(env, method, path):
    client, _db, _service, current = env
    _as(current, USER_A)
    resp = getattr(client, method)(path)
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/analysis/tasks/all"),
        ("get", "/api/analysis/admin/zombie-tasks"),
        ("post", "/api/analysis/admin/cleanup-zombie-tasks"),
    ],
)
@pytest.mark.parametrize("admin_user", [ADMIN, OPS_ADMIN])
def test_admin_only_endpoints_allow_admin(env, method, path, admin_user):
    client, _db, _service, current = env
    _as(current, admin_user)
    resp = getattr(client, method)(path)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_tasks_all_route_not_shadowed_by_task_id_route(env):
    """/tasks/all 不能被 /tasks/{task_id}/... 吞掉：返回的是任务列表而不是 404。"""
    client, _db, _service, current = env
    _as(current, ADMIN)
    resp = client.get("/api/analysis/tasks/all")
    assert resp.status_code == 200
    assert len(resp.json()["data"]["tasks"]) == 2
