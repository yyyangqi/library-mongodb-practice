"""创建平台账号（F6）：集群管理账号 root + 只读/读写/管理三种业务角色。

两种执行场景：
1. 引导场景（数据库刚以 --auth 启动、还没有任何用户）：
       python tools/create_users.py
   利用 localhost exception 先建 admin.root，再以 root 身份建业务账号。
2. 已启用认证并有 root 的场景：
       python tools/create_users.py --admin-user root --admin-pass Super@2025

用法补充：
    --host / --port 可覆盖配置，用于副本集或 mongos 上的账号创建；
    --replset 指定副本集名（连副本集时必填，否则驱动无法完成拓扑发现）。
"""
import argparse
import os
import sys
from urllib.parse import quote_plus

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pymongo import MongoClient                      # noqa: E402
from pymongo.errors import OperationFailure          # noqa: E402

from config import CONFIG                            # noqa: E402

PLATFORM_USERS = [
    {"user": "lib_ro", "pwd": "Read@2025", "roles": [{"role": "read", "db": "smart_library"}],
     "note": "只读：检索、统计、下载，不允许任何写入"},
    {"user": "lib_rw", "pwd": "Write@2025",
     "roles": [{"role": "readWrite", "db": "smart_library"}],
     "note": "读写：图书/读者/借阅维护、文件上传、写日志，不允许建索引"},
    {"user": "lib_admin", "pwd": "Admin@2025",
     "roles": [{"role": "dbOwner", "db": "smart_library"}],
     "note": "管理：建集合、建索引、落库统计结果"},
]


def make_client(host, port, user=None, pwd=None, auth_source="admin", replset=None):
    if user:
        uri = "mongodb://%s:%s@%s:%s/?authSource=%s" % (
            quote_plus(user), quote_plus(pwd), host, port, auth_source)
    else:
        uri = "mongodb://%s:%s/" % (host, port)
    kwargs = {"serverSelectionTimeoutMS": 8000, "appname": "create-users"}
    if replset:
        kwargs["replicaSet"] = replset
    return MongoClient(uri, **kwargs)


def create_platform_users(client, db_name):
    db = client[db_name]
    for u in PLATFORM_USERS:
        try:
            db.command("createUser", u["user"], pwd=u["pwd"], roles=u["roles"])
            print("[账号] 已创建 %-10s 角色=%-10s %s"
                  % (u["user"], u["roles"][0]["role"], u["note"]))
        except OperationFailure as exc:
            db.command("updateUser", u["user"], pwd=u["pwd"], roles=u["roles"])
            print("[账号] 已更新 %-10s 角色=%-10s（原账号已存在：%s）"
                  % (u["user"], u["roles"][0]["role"], str(exc)[:60]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin-user", default=None)
    ap.add_argument("--admin-pass", default=None)
    ap.add_argument("--super-user", default="root")
    ap.add_argument("--super-pass", default="Super@2025")
    ap.add_argument("--host", default=None)
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--replset", default=None)
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    m = CONFIG["mongo"]
    host = args.host or m.get("host", "127.0.0.1")
    port = args.port or int(m.get("port", 27017))
    db_name = args.db or m.get("db_name", "smart_library")
    replset = args.replset or m.get("replica_set") or None

    print("=" * 78)
    print("账号创建：%s:%s  数据库=%s  认证源=admin%s"
          % (host, port, db_name, ("  副本集=%s" % replset) if replset else ""))
    print("=" * 78)

    if args.admin_user:
        client = make_client(host, port, args.admin_user, args.admin_pass, "admin", replset)
        create_platform_users(client, db_name)
        client.close()
        print("\n完成：业务账号已就绪。")
        return 0

    # 引导场景：尚无用户，先借 localhost exception 建 root
    client = make_client(host, port, None, None, "admin", replset)
    client["admin"].command("createUser", args.super_user, pwd=args.super_pass,
                            roles=[{"role": "root", "db": "admin"}])
    print("[账号] 已创建 admin.%s（root 角色，具备副本集/分片集群运维权限）" % args.super_user)
    client.close()

    # 改用 root 身份创建业务账号
    client = make_client(host, port, args.super_user, args.super_pass, "admin", replset)
    create_platform_users(client, db_name)
    client.close()

    print("\n完成：管理账号 %s / %s，业务账号 %s"
          % (args.super_user, "、".join(u["user"] for u in PLATFORM_USERS), db_name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
