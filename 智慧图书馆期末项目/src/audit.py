"""操作日志模块：所有新增/删除/导出等关键操作写入 audit_logs。

字段设计：ts(操作时间,倒序查询用)、action(动作类型)、target(操作对象)、
detail(细节)、operator(操作账号)、result(成功/失败)。
"""
from datetime import datetime

from config import CONFIG

ACTIONS = ("INSERT", "UPDATE", "DELETE", "EXPORT", "UPLOAD", "DOWNLOAD", "INDEX")


def write_audit(collection, action, target, detail="", operator=None, result="success"):
    doc = {
        "ts": datetime.now(),
        "action": action,
        "target": target,
        "detail": detail,
        "operator": operator or CONFIG["mongo"].get("username") or "local",
        "result": result,
    }
    collection.insert_one(doc)
    return doc


def recent(collection, limit=100):
    """按时间倒序查询最近 N 条操作，索引 audit_logs.ts:-1 支撑。"""
    return list(collection.find({}, {"_id": 0}).sort("ts", -1).limit(limit))


def summary(collection):
    rows = list(collection.aggregate([
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]))
    return [(r["_id"], r["count"]) for r in rows]
