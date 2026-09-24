from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument

from app.settings import settings

log = logging.getLogger("teradrop.storage")
_client: MongoClient | None = None
_db = None
_lock = threading.RLock()

DEFAULT_PLANS: dict[str, dict[str, Any]] = {
    "r": {
        "key": "r",
        "label": "regular premium",
        "short_label": "regular",
        "price": 69,
        "duration_days": 14,
        "batch_limit": 5,
        "total_links": 50,
        "active": True,
    },
    "s": {
        "key": "s",
        "label": "super premium",
        "short_label": "super",
        "price": 149,
        "duration_days": 30,
        "batch_limit": 10,
        "total_links": 150,
        "active": True,
    },
    "v": {
        "key": "v",
        "label": "vip premium",
        "short_label": "vip",
        "price": 249,
        "duration_days": 30,
        "batch_limit": 20,
        "total_links": 0,
        "active": True,
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mongo():
    global _client, _db
    if _db is not None:
        return _db
    uri = (settings.mongodb_uri or "").strip()
    if not uri:
        raise RuntimeError("MONGODB_URI is required. Add it as a project secret.")
    _client = MongoClient(
        uri,
        appname="multi-user-downloader-bot",
        maxPoolSize=max(50, settings.max_concurrent * 12),
        minPoolSize=5,
        serverSelectionTimeoutMS=10_000,
        connectTimeoutMS=10_000,
        retryWrites=True,
    )
    _db = _client[settings.mongodb_database]
    return _db


def init() -> None:
    db = _mongo()
    db.users.create_index("user_id", unique=True)
    db.admins.create_index("user_id", unique=True)
    db.bans.create_index("user_id", unique=True)
    db.auth.create_index("user_id", unique=True)
    db.users.create_index([("seen_at", DESCENDING)])
    db.logs.create_index([("created_at", DESCENDING)])
    db.orders.create_index("order_id", unique=True)
    db.orders.create_index([("status", ASCENDING), ("expires_at", ASCENDING)])
    db.plans.create_index("key", unique=True)
    db.force_subs.create_index("chat_id", unique=True)
    db.transactions.create_index("txn_id", unique=True, sparse=True)
    for key, plan in DEFAULT_PLANS.items():
        db.plans.update_one({"key": key}, {"$setOnInsert": plan}, upsert=True)
    for raw in (settings.force_sub_channel or "").replace(";", ",").split(","):
        value = raw.strip()
        if value:
            db.force_subs.update_one(
                {"chat_id": value},
                {"$setOnInsert": {"chat_id": value, "invite_url": ""}},
                upsert=True,
            )


def close() -> None:
    global _client, _db
    if _client:
        _client.close()
    _client = None
    _db = None


def touch_user(user_id: int, username: str | None, first_name: str | None) -> None:
    _mongo().users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "username": username or "",
                "first_name": first_name or "",
                "seen_at": _now(),
            },
            "$setOnInsert": {
                "downloads": 0,
                "send_file_count": 0,
                "free_links_used": 0,
                "free_window_started_at": None,
                "plan_links_used": 0,
            },
        },
        upsert=True,
    )


def bump_download(user_id: int) -> None:
    _mongo().users.update_one({"user_id": user_id}, {"$inc": {"downloads": 1}})


def is_banned(user_id: int) -> bool:
    return bool(_mongo().bans.find_one({"user_id": user_id}, {"_id": 1}))


def ban(user_id: int) -> None:
    _mongo().bans.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)


def unban(user_id: int) -> None:
    _mongo().bans.delete_one({"user_id": user_id})


def is_authorized(user_id: int) -> bool:
    if user_id in settings.authorized_ids:
        return True
    return bool(_mongo().auth.find_one({"user_id": user_id}, {"_id": 1}))


def authorize(user_id: int) -> None:
    _mongo().auth.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)


def unauthorize(user_id: int) -> None:
    _mongo().auth.delete_one({"user_id": user_id})


def is_admin(user_id: int) -> bool:
    return settings.is_owner(user_id) or bool(
        _mongo().admins.find_one({"user_id": user_id}, {"_id": 1})
    )


def add_admin(user_id: int) -> None:
    _mongo().admins.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)


def remove_admin(user_id: int) -> None:
    _mongo().admins.delete_one({"user_id": user_id})


def admin_ids() -> list[int]:
    ids = set(settings.owner_ids)
    ids.update(int(row["user_id"]) for row in _mongo().admins.find({}, {"user_id": 1}))
    return sorted(ids)


def log(level: str, message: str) -> None:
    db = _mongo()
    db.logs.insert_one({"created_at": _now(), "level": level, "message": str(message)[:2000]})
    old = list(
        db.logs.find({}, {"_id": 1}).sort("created_at", DESCENDING).skip(100).limit(1000)
    )
    if old:
        db.logs.delete_many({"_id": {"$in": [row["_id"] for row in old]}})


def recent_logs(limit: int = 12) -> list[str]:
    rows = _mongo().logs.find().sort("created_at", DESCENDING).limit(limit)
    return [f"{row.get('level', 'info')}: {row.get('message', '')}" for row in rows]


def stats() -> dict[str, int]:
    db = _mongo()
    users = int(db.users.estimated_document_count())
    bans = int(db.bans.estimated_document_count())
    downloads_row = list(
        db.users.aggregate(
            [{"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$downloads", 0]}}}}]
        )
    )
    downloads = int(downloads_row[0]["total"]) if downloads_row else 0
    premium = db.users.count_documents(
        {"plan_key": {"$exists": True}, "plan_expires_at": {"$gt": _now()}}
    )
    return {"users": users, "downloads": downloads, "bans": bans, "premium": premium}


def user_ids() -> list[int]:
    return [int(row["user_id"]) for row in _mongo().users.find({}, {"user_id": 1})]


def recent_users(limit: int = 15) -> list[str]:
    rows = _mongo().users.find().sort("seen_at", DESCENDING).limit(limit)
    out: list[str] = []
    for row in rows:
        name = row.get("username") or row.get("first_name") or "user"
        plan = row.get("plan_key") or "free"
        out.append(f"{row['user_id']} · {name} · {row.get('downloads', 0)} files · {plan}")
    return out


def list_users(limit: int = 40) -> list[dict[str, Any]]:
    rows = _mongo().users.find().sort("seen_at", DESCENDING).limit(limit)
    out: list[dict[str, Any]] = []
    for row in rows:
        expires = row.get("plan_expires_at")
        out.append(
            {
                "user_id": int(row["user_id"]),
                "username": row.get("username") or "",
                "first_name": row.get("first_name") or "",
                "downloads": int(row.get("downloads") or 0),
                "plan_key": row.get("plan_key") or "free",
                "plan_expires_at": expires.isoformat() if expires else None,
                "banned": is_banned(int(row["user_id"])),
            }
        )
    return out


def kv_get(key: str, default: str = "") -> str:
    row = _mongo().kv.find_one({"k": key})
    return str(row.get("v", default)) if row else default


def kv_set(key: str, value: str) -> None:
    _mongo().kv.update_one({"k": key}, {"$set": {"k": key, "v": value}}, upsert=True)


def kv_delete(key: str) -> None:
    _mongo().kv.delete_one({"k": key})


def list_force_subs() -> list[dict[str, str]]:
    return [
        {"chat_id": str(row["chat_id"]), "invite_url": str(row.get("invite_url") or "")}
        for row in _mongo().force_subs.find().sort("chat_id", ASCENDING)
    ]


def add_force_sub(chat_id: str, invite_url: str = "") -> None:
    _mongo().force_subs.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "invite_url": invite_url}},
        upsert=True,
    )


def remove_force_sub(chat_id: str) -> None:
    _mongo().force_subs.delete_one({"chat_id": chat_id})


def get_plan(key: str) -> dict[str, Any] | None:
    row = _mongo().plans.find_one({"key": key, "active": True}, {"_id": 0})
    return dict(row) if row else None


def list_plans(active_only: bool = False) -> list[dict[str, Any]]:
    query = {"active": True} if active_only else {}
    return [dict(row) for row in _mongo().plans.find(query, {"_id": 0}).sort("price", ASCENDING)]


def upsert_plan(plan: dict[str, Any]) -> None:
    _mongo().plans.update_one({"key": plan["key"]}, {"$set": plan}, upsert=True)


def delete_plan(key: str) -> None:
    _mongo().plans.update_one({"key": key}, {"$set": {"active": False}})


def _active_plan(user: dict[str, Any]) -> dict[str, Any] | None:
    key = user.get("plan_key")
    expires = user.get("plan_expires_at")
    if not key or not expires:
        return None
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= _now():
        return None
    return get_plan(str(key))


def entitlement(user_id: int) -> dict[str, Any]:
    user = _mongo().users.find_one({"user_id": user_id}) or {"user_id": user_id}
    plan = _active_plan(user)
    if plan:
        used = int(user.get("plan_links_used", 0))
        total = int(plan.get("total_links", 0))
        remaining = None if total <= 0 else max(0, total - used)
        return {
            "premium": True,
            "plan": plan,
            "plan_key": plan["key"],
            "batch_limit": int(plan.get("batch_limit", 1)),
            "remaining_links": remaining,
            "send_file_remaining": None,
            "expires_at": user.get("plan_expires_at"),
        }
    started = user.get("free_window_started_at")
    used = int(user.get("free_links_used", 0))
    if started and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if not started or started + timedelta(hours=24) <= _now():
        used = 0
        started = None
    return {
        "premium": False,
        "plan": None,
        "plan_key": None,
        "batch_limit": 1,
        "remaining_links": max(0, settings.free_links_per_24h - used),
        "send_file_remaining": max(0, settings.free_send_file_lifetime - int(user.get("send_file_count", 0))),
        "expires_at": None,
        "free_window_started_at": started,
    }


def try_reserve_links(user_id: int, count: int) -> tuple[bool, dict[str, Any]]:
    count = max(1, int(count))
    db = _mongo()
    now = _now()
    user = db.users.find_one({"user_id": user_id}) or {"user_id": user_id}
    plan = _active_plan(user)
    if plan:
        total = int(plan.get("total_links", 0))
        if total <= 0:
            db.users.update_one(
                {"user_id": user_id},
                {"$inc": {"plan_links_used": count}, "$setOnInsert": {"user_id": user_id}},
                upsert=True,
            )
            return True, entitlement(user_id)
        updated = db.users.find_one_and_update(
            {
                "user_id": user_id,
                "$or": [
                    {"plan_links_used": {"$lte": total - count}},
                    {"plan_links_used": {"$exists": False}},
                ],
            },
            {"$inc": {"plan_links_used": count}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            return False, entitlement(user_id)
        return True, entitlement(user_id)

    window_start = now
    started = user.get("free_window_started_at")
    if started and getattr(started, "tzinfo", None) is None:
        started = started.replace(tzinfo=timezone.utc)
    if started and started + timedelta(hours=24) > now:
        window_start = started
        used = int(user.get("free_links_used", 0))
        if used + count > settings.free_links_per_24h:
            return False, entitlement(user_id)
        updated = db.users.find_one_and_update(
            {
                "user_id": user_id,
                "free_window_started_at": started,
                "free_links_used": {"$lte": settings.free_links_per_24h - count},
            },
            {"$inc": {"free_links_used": count}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            return False, entitlement(user_id)
        return True, entitlement(user_id)

    updated = db.users.find_one_and_update(
        {"user_id": user_id},
        {
            "$set": {"free_window_started_at": window_start, "free_links_used": count},
            "$setOnInsert": {"user_id": user_id},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        return False, entitlement(user_id)
    return True, entitlement(user_id)


def reserve_send_file(user_id: int) -> tuple[bool, dict[str, Any]]:
    access = entitlement(user_id)
    if access["premium"]:
        return True, access
    with _lock:
        updated = _mongo().users.find_one_and_update(
            {
                "user_id": user_id,
                "$or": [
                    {"send_file_count": {"$lt": settings.free_send_file_lifetime}},
                    {"send_file_count": {"$exists": False}},
                ],
            },
            {"$inc": {"send_file_count": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            return False, entitlement(user_id)
        return True, entitlement(user_id)


def create_order(order: dict[str, Any]) -> None:
    _mongo().orders.insert_one(order)


def get_order(order_id: str) -> dict[str, Any] | None:
    return _mongo().orders.find_one({"order_id": order_id})


def claim_transaction(txn_id: str) -> bool:
    if not txn_id:
        return False
    try:
        _mongo().transactions.insert_one({"txn_id": txn_id, "created_at": _now()})
        return True
    except Exception:
        return False


def mark_order_success(order_id: str, txn_id: str) -> bool:
    updated = _mongo().orders.find_one_and_update(
        {"order_id": order_id, "status": "pending"},
        {"$set": {"status": "success", "txn_id": txn_id, "paid_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    return bool(updated)


def update_order_status(order_id: str, status: str) -> None:
    _mongo().orders.update_one(
        {"order_id": order_id, "status": "pending"},
        {"$set": {"status": status, "updated_at": _now()}},
    )


def activate_plan(user_id: int, key: str, days: int) -> datetime:
    now = _now()
    user = _mongo().users.find_one({"user_id": user_id}) or {}
    current = user.get("plan_expires_at")
    if current and current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    start = current if current and current > now else now
    expiry = start + timedelta(days=max(1, days))
    _mongo().users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "plan_key": key,
                "plan_expires_at": expiry,
                "plan_links_used": 0,
                "send_file_count": 0,
            }
        },
        upsert=True,
    )
    return expiry


def remove_premium(user_id: int) -> None:
    _mongo().users.update_one(
        {"user_id": user_id},
        {"$unset": {"plan_key": "", "plan_expires_at": "", "plan_links_used": ""}},
    )


def dump_json(path) -> None:
    path.write_text(str(stats()))