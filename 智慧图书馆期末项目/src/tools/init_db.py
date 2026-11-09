"""初始化脚本：创建数据库与集合、导入三份数据文件、核对文档数量。

用法：python tools/init_db.py
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pymongo.database import Database             # noqa: E402

from config import CONFIG                         # noqa: E402
from db import LibraryDB                          # noqa: E402


def load_json_array(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_date(value):
    """把 ISO 8601 字符串转成 datetime；MongoDB 司机默认按 UTC 存储，
    这里统一保留时区偏移语义后转为 naive UTC 时间，避免 +08:00 与本地时间混用。"""
    if isinstance(value, str) and "T" in value:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    return value


def create_schema(db: Database):
    existing = set(db.list_collection_names())
    for name in ("books", "readers"):
        if name in existing:
            db.drop_collection(name)
        db.create_collection(name)

    # borrow_logs：时间序列集合（写入密集、按时间范围查询为主）
    if "borrow_logs" in existing:
        db.drop_collection("borrow_logs")
    db.create_collection(
        "borrow_logs",
        timeseries={
            "timeField": "borrow_date",
            "metaField": "reader_card",
            "granularity": "hours",
        },
    )

    # audit_logs：固定容量集合（只追加、按时间倒序查询最近 N 条）
    for name in ("audit_logs", "category_stats"):
        if name in existing:
            db.drop_collection(name)
    db.create_collection("audit_logs", capped=True, size=16 * 1024 * 1024, max=200000)
    db.create_collection("category_stats")
    print("[集合] 已创建：books / readers / borrow_logs(时序) / audit_logs(固定容量) / category_stats")


def main():
    with LibraryDB() as db:
        create_schema(db.db)
        data_dir = CONFIG["paths"]["data_dir"]

        books = load_json_array(os.path.join(data_dir, "books.txt"))
        for b in books:
            b["publish_date"] = to_date(b["publish_date"])
        db.books.insert_many(books)

        readers = load_json_array(os.path.join(data_dir, "readers.txt"))
        for r in readers:
            r["register_date"] = to_date(r["register_date"])
        db.readers.insert_many(readers)

        logs = load_json_array(os.path.join(data_dir, "borrow_logs.txt"))
        for lg in logs:
            lg["borrow_date"] = to_date(lg["borrow_date"])
            if lg.get("return_date"):
                lg["return_date"] = to_date(lg["return_date"])
        db.borrow_logs.insert_many(logs)

        print("\n[核对] 源文件条目数 vs 集合文档数")
        checks = [("books", "books.txt", len(books)),
                  ("readers", "readers.txt", len(readers)),
                  ("borrow_logs", "borrow_logs.txt", len(logs))]
        ok = True
        for coll, fname, src_count in checks:
            n = db.db[coll].count_documents({})
            flag = "一致" if n == src_count else "不一致"
            ok = ok and n == src_count
            print("  %-12s %-16s 源 %4d  库 %4d  %s" % (coll, fname, src_count, n, flag))

        print("\n[集合类型]")
        for info in db.db.list_collections():
            opt = info.get("options", {})
            print("  %-26s type=%-9s timeseries=%s capped=%s"
                  % (info["name"], info.get("type"),
                     bool(opt.get("timeseries")), bool(opt.get("capped"))))

        print("\n[数据抽样] books 缺 tags 的条目：%d"
              % db.books.count_documents({"tags": {"$exists": False}}))
        print("[数据抽样] readers 缺 fav_categories：%d"
              % db.readers.count_documents({"fav_categories": {"$exists": False}}))
        print("\n导入完成，结果：%s" % ("全部一致" if ok else "存在差异"))
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
