#!/usr/bin/env python3
"""历史报告 user_id 回填脚本：回填正确、幂等、dry-run 不写库、无法回填标记。"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest
from bson import ObjectId

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fake_mongo_helper import FakeDB

_SCRIPT = ROOT / "scripts" / "migrations" / "backfill_report_user_id.py"
_spec = importlib.util.spec_from_file_location("backfill_report_user_id", _SCRIPT)
backfill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backfill)

OID_A = ObjectId()
OID_B = ObjectId()
OID_C = ObjectId()
OID_D = ObjectId()
OID_E = ObjectId()


def _make_db():
    reports = [
        # 通过 task_id 关联到 user-a
        {"_id": OID_A, "analysis_id": "r-a", "task_id": "t-a"},
        # 通过 result.analysis_id 反查到 user-b（旧字段 user）
        {"_id": OID_B, "analysis_id": "r-b", "task_id": "missing"},
        # 找不到任务 -> 无法回填
        {"_id": OID_C, "analysis_id": "r-c", "task_id": "nope"},
        # 已有字符串 user_id -> 不动
        {"_id": OID_D, "analysis_id": "r-d", "task_id": "t-d", "user_id": "user-d"},
        # user_id 是 ObjectId -> 规整为字符串
        {"_id": OID_E, "analysis_id": "r-e", "task_id": "t-e", "user_id": ObjectId("507f1f77bcf86cd799439011")},
    ]
    tasks = [
        {"task_id": "t-a", "user_id": "user-a"},
        {"task_id": "t-b", "user": "user-b", "result": {"analysis_id": "r-b"}},
        {"task_id": "t-d", "user_id": "someone-else"},
    ]
    return FakeDB(reports=reports, tasks=tasks)


def _by_id(db, oid):
    return next(d for d in db.analysis_reports.docs if d["_id"] == oid)


def _run(db, dry_run):
    return asyncio.run(backfill.run_backfill(db, dry_run=dry_run))


def test_backfill_fills_owner_and_marks_unknown():
    db = _make_db()
    stats = _run(db, dry_run=False)

    assert stats == {"total": 3, "filled": 2, "unknown": 1, "normalized": 1}
    assert _by_id(db, OID_A)["user_id"] == "user-a"
    assert _by_id(db, OID_B)["user_id"] == "user-b"
    unknown = _by_id(db, OID_C)
    assert unknown["user_id"] is None and unknown["owner_unknown"] is True
    # 已有归属的报告不被覆盖
    assert _by_id(db, OID_D)["user_id"] == "user-d"
    assert _by_id(db, OID_E)["user_id"] == "507f1f77bcf86cd799439011"


def test_dry_run_does_not_write_and_matches_real_stats():
    db = _make_db()
    before = [dict(d) for d in db.analysis_reports.docs]

    dry_stats = _run(db, dry_run=True)
    assert db.analysis_reports.docs == before

    real_stats = _run(db, dry_run=False)
    assert dry_stats == real_stats


def test_backfill_is_idempotent_and_retries_unknown():
    db = _make_db()
    _run(db, dry_run=False)
    snapshot = [dict(d) for d in db.analysis_reports.docs]

    second = _run(db, dry_run=False)
    # 第二次只会重新尝试无法回填的那条，数据不变
    assert second == {"total": 1, "filled": 0, "unknown": 1, "normalized": 0}
    assert db.analysis_reports.docs == snapshot

    # 任务记录后来补上归属后，重试可以回填并清除 owner_unknown
    db.analysis_tasks.docs.append({"task_id": "nope", "user_id": "user-c"})
    third = _run(db, dry_run=False)
    assert third["filled"] == 1
    fixed = _by_id(db, OID_C)
    assert fixed["user_id"] == "user-c"
    assert "owner_unknown" not in fixed
