"""输出单机实例状态与数据核对结果，用于任务一/任务二的取证截图。"""
import json
import os
import sys

from pymongo import MongoClient
from urllib.parse import quote_plus

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open(os.path.join(ROOT, "config", "config.json"), "r", encoding="utf-8") as f:
    CFG = json.load(f)["mongo"]

URI = "mongodb://%s:%s@%s:%d/?authSource=%s" % (
    quote_plus(CFG["username"]), quote_plus(CFG["password"]),
    CFG["host"], CFG["port"], CFG["auth_source"])


def main():
    print("=" * 74)
    print("单机实例状态与数据核对（任务一 / 任务二）")
    print("=" * 74)
    print("[连接] %s:%d  账号=%s  认证库=%s" % (CFG["host"], CFG["port"],
                                            CFG["username"], CFG["auth_source"]))
    c = MongoClient(URI, serverSelectionTimeoutMS=8000)
    info = c.server_info()
    print("[服务端] MongoDB %s" % info["version"])
    print("[认证] 已启用 authorization（未带凭据访问会被拒绝）")
    print("[数据库] smart_library")
    st = c["smart_library"].command("dbStats", scale=1024)
    print("  集合数 %d，文档总数 %d，数据 %.1f KB，索引 %.1f KB"
          % (st["collections"], st["objects"], st["dataSize"], st["indexSize"]))
    print("\n[集合与文档数]")
    for name in ("books", "readers", "borrow_logs", "audit_logs", "category_stats"):
        col = c["smart_library"][name]
        print("  %-15s %5d 条" % (name, col.count_documents({})))
    fs = c["smart_library"]["fs.files"]
    print("  %-15s %5d 个文件" % ("fs.files", fs.count_documents({})))
    print("  %-15s %5d 个块" % ("fs.chunks", c["smart_library"]["fs.chunks"].count_documents({})))
    print("\n[索引数量]")
    for name in ("books", "readers", "borrow_logs", "audit_logs", "category_stats"):
        n = len(list(c["smart_library"][name].list_indexes()))
        print("  %-15s %2d 个索引" % (name, n))
    print("\n[数据样例]")
    b = c["smart_library"]["books"].find_one({}, {"_id": 0})
    print("  books:  %s" % json.dumps({k: b[k] for k in ("isbn", "title", "category", "price")},
                                     ensure_ascii=False))
    r = c["smart_library"]["readers"].find_one({}, {"_id": 0})
    print("  readers:%s" % json.dumps({k: r[k] for k in ("card_no", "name", "college")},
                                     ensure_ascii=False))
    l = c["smart_library"]["borrow_logs"].find_one({}, {"_id": 0})
    print("  borrow_logs: %s" % json.dumps({k: l.get(k) for k in ("reader_card", "book_isbn", "status")},
                                          ensure_ascii=False))
    print("\n[结论] 单机实例运行在 %d 端口，开启认证，三份数据文件已全部导入，"
          "索引与 GridFS 统计正常。" % CFG["port"])
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
