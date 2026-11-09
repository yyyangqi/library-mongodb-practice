"""统一数据库连接模块（被图书、读者、借阅、统计、文件等所有模块调用）。"""
from pymongo import MongoClient, ReadPreference
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError
from gridfs import GridFS

from config import CONFIG, build_uri

READ_PREF_MAP = {
    "primary": ReadPreference.PRIMARY,
    "primarypreferred": ReadPreference.PRIMARY_PREFERRED,
    "secondary": ReadPreference.SECONDARY,
    "secondarypreferred": ReadPreference.SECONDARY_PREFERRED,
    "nearest": ReadPreference.NEAREST,
}


class LibraryDB:
    """平台数据库门面：集中管理客户端、集合与 GridFS 桶。"""

    def __init__(self, read_preference=None):
        m = CONFIG["mongo"]
        self.uri = build_uri(m)
        rp_name = (read_preference or m.get("read_preference") or "primary").lower()
        self.read_preference_name = rp_name
        kwargs = {
            "serverSelectionTimeoutMS": 5000,
            "appname": "smart-library-platform",
        }
        if m.get("replica_set"):
            kwargs["replicaSet"] = m["replica_set"]
        self.client = MongoClient(self.uri, read_preference=READ_PREF_MAP.get(rp_name, ReadPreference.PRIMARY), **kwargs)
        self.db = self.client[m["db_name"]]
        self.books = self.db["books"]
        self.readers = self.db["readers"]
        self.borrow_logs = self.db["borrow_logs"]
        self.audit_logs = self.db["audit_logs"]
        self.category_stats = self.db["category_stats"]
        self.fs = GridFS(self.db)

    # ---- 健康检查 -------------------------------------------------
    def ping(self):
        return self.client.admin.command("ping").get("ok", 0) == 1

    def server_info(self):
        return self.client.server_info().get("version")

    def topology(self):
        """返回当前连接看到的节点角色，用于副本集/分片集群验证。"""
        info = []
        try:
            hello = self.client.admin.command("hello")
            info.append(("isWritablePrimary", hello.get("isWritablePrimary")))
            info.append(("setName", hello.get("setName")))
            info.append(("msg", hello.get("msg")))
            info.append(("me", hello.get("me")))
        except PyMongoError as exc:
            info.append(("error", str(exc)))
        return info

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def check_connection() -> bool:
    """程序启动时的连通性自检，失败时给出明确提示而不是抛出堆栈。"""
    try:
        with LibraryDB() as db:
            if db.ping():
                print("[连接成功] MongoDB %s  数据库=%s  读取偏好=%s"
                      % (db.server_info(), CONFIG["mongo"]["db_name"], db.read_preference_name))
                return True
    except OperationFailure as exc:
        print("[连接失败] 认证或权限错误：%s" % exc)
    except ConnectionFailure as exc:
        print("[连接失败] 无法连接数据库：%s" % exc)
    except PyMongoError as exc:
        print("[连接失败] %s" % exc)
    return False


if __name__ == "__main__":
    check_connection()
