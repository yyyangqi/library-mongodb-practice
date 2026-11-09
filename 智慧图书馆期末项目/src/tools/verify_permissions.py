"""权限验证（F6 / 任务五、六的认证验证）：同一操作在只读、读写、管理账号下的结果。

用法：
    python tools/verify_permissions.py                       # 单机 27017
    python tools/verify_permissions.py --port 27023 --replset rsLib
"""
import argparse
import os
import sys
from urllib.parse import quote_plus

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pymongo import MongoClient                      # noqa: E402
from pymongo.errors import OperationFailure, PyMongoError   # noqa: E402

from config import CONFIG                            # noqa: E402

HOST = "127.0.0.1"
PORT = 27017
REPLSET = None
DB_NAME = "smart_library"


def connect(user, pwd):
    uri = "mongodb://%s:%s@%s:%s/?authSource=%s" % (
        quote_plus(user), quote_plus(pwd), HOST, PORT, DB_NAME)
    kwargs = {"serverSelectionTimeoutMS": 8000}
    if REPL_SET:
        kwargs["replicaSet"] = REPL_SET
    return MongoClient(uri, **kwargs)


def attempt(db, desc, func):
    try:
        func()
        print("  [允许] %s" % desc)
        return "allowed"
    except OperationFailure as exc:
        print("  [拒绝] %s\n         -> %s" % (desc, str(exc).split(",")[0][:120]))
        return "denied"
    except PyMongoError as exc:
        print("  [失败] %s\n         -> %s" % (desc, str(exc)[:120]))
        return "error"


def main():
    global PORT, REPL_SET, HOST, DB_NAME
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--replset", default=None)
    ap.add_argument("--db", default=DB_NAME)
    args = ap.parse_args()
    HOST, PORT, REPL_SET, DB_NAME = args.host, args.port, args.replset, args.db

    print("=" * 78)
    print("权限验证：同一操作在三种账号下的结果   目标=%s:%s%s"
          % (HOST, PORT, ("  副本集=%s" % REPL_SET) if REPL_SET else ""))
    print("=" * 78)

    print("\n[lib_ro 只读账号]")
    c1 = connect("lib_ro", "Read@2025")
    db1 = c1[DB_NAME]
    print("  [允许] 查询图书条数 -> %d" % db1.books.count_documents({}))
    print("  [允许] 聚合统计分类均价 -> %d 个类别"
          % len(list(db1.books.aggregate([{"$group": {"_id": "$category", "p": {"$avg": "$price"}}}]))))
    attempt(db1, "books.insert_one 新增图书", lambda: db1.books.insert_one({"isbn": "TEST-RO-001", "title": "越权测试"}))
    attempt(db1, "books.delete_one 删除图书", lambda: db1.books.delete_one({"isbn": "TEST-RO-001"}))
    attempt(db1, "audit_logs.insert_one 写操作日志", lambda: db1.audit_logs.insert_one({"action": "INSERT"}))
    attempt(db1, "books.create_index 建索引", lambda: db1.books.create_index([("price", 1)]))
    c1.close()

    print("\n[lib_rw 读写账号]")
    c2 = connect("lib_rw", "Write@2025")
    db2 = c2[DB_NAME]
    attempt(db2, "books.insert_one 插入测试图书",
            lambda: db2.books.insert_one({"isbn": "TEST-RW-001", "title": "读写测试", "price": 1.0}))
    print("  [允许] 查询刚插入的文档 -> %d 条" % db2.books.count_documents({"isbn": "TEST-RW-001"}))
    attempt(db2, "audit_logs.insert_one 写操作日志", lambda: db2.audit_logs.insert_one({"action": "TEST", "operator": "lib_rw"}))
    attempt(db2, "books.delete_one 删除测试图书", lambda: db2.books.delete_one({"isbn": "TEST-RW-001"}))
    attempt(db2, "books.create_index 建索引（readWrite 允许）",
            lambda: db2.books.create_index([("stock", 1)], name="tmp_rw_idx"))
    attempt(db2, "collMod 修改集合校验规则（管理级操作，应被拒绝）",
            lambda: db2.command("collMod", "books", validator={"$jsonSchema": {}}))
    attempt(db2, "createRole 创建自定义角色（管理级操作，应被拒绝）",
            lambda: db2.command("createRole", "tmp_role", privileges=[], roles=[]))
    attempt(db2, "dropDatabase 删除数据库（管理级操作，应被拒绝）",
            lambda: c2.drop_database(DB_NAME))
    c2.close()

    print("\n[lib_admin 管理账号]")
    c3 = connect("lib_admin", "Admin@2025")
    db3 = c3[DB_NAME]
    attempt(db3, "books.create_index 建索引", lambda: db3.books.create_index([("stock", -1)], name="tmp_admin_idx"))
    attempt(db3, "books.drop_index 删除索引", lambda: db3.books.drop_index("tmp_admin_idx"))
    attempt(db3, "create_collection 建集合", lambda: db3.create_collection("tmp_test_coll"))
    attempt(db3, "collMod 修改集合校验规则", lambda: db3.command("collMod", "tmp_test_coll",
                                                                  validator={"$jsonSchema": {"bsonType": "object"}}))
    attempt(db3, "drop_collection 删集合", lambda: db3.drop_collection("tmp_test_coll"))
    c3.close()

    # 清理测试残留（root 账号）
    try:
        c4 = MongoClient("mongodb://%s:%s@%s:%s/?authSource=admin" % (
            quote_plus("root"), quote_plus("Super@2025"), HOST, PORT),
            serverSelectionTimeoutMS=8000,
            **({"replicaSet": REPL_SET} if REPL_SET else {}))
        db4 = c4[DB_NAME]
        n = db4.books.delete_many({"isbn": {"$in": ["TEST-RO-001", "TEST-RW-001"]}}).deleted_count
        db4.audit_logs.delete_many({"action": "TEST"})
        names = [i["name"] for i in db4.books.list_indexes()]
        removed = []
        for name in names:
            if name in ("stock_1", "tmp_stock_idx", "tmp_rw_idx", "tmp_admin_idx", "price_1"):
                try:
                    db4.books.drop_index(name)
                    removed.append(name)
                except PyMongoError:
                    pass
        if n:
            print("\n[清理] 删除测试文档 %d 条" % n)
        if removed:
            print("[清理] 删除测试索引 %s" % "、".join(removed))
        c4.close()
    except PyMongoError as exc:
        print("\n[清理] 跳过（root 账号不可用：%s）" % str(exc)[:80])
    print("\n验证结束。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
