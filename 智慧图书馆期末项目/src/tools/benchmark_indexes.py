"""索引优化对比（F5）。

由于教学数据集规模很小（books 50 条 / borrow_logs 3000 条），COLLSCAN 本身只需几十微秒，
索引带来的额外 B-Tree 查找反而可能更慢。因此本脚本分两部分：

A. 真实数据集（50 / 30 / 3000）——如实记录耗时，说明小数据量下索引收益不明显的现象；
B. 放大数据集（books_bench 50000 条 / borrow_bench 300000 条）——用相同查询验证
   索引在接近真实馆藏规模（50 万册量级）下的收益，作为 L1 对比数据的补充。

用法：python tools/benchmark_indexes.py
"""
import os
import random
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pymongo import ASCENDING, DESCENDING           # noqa: E402

import books as book_mod                            # noqa: E402
import borrow as borrow_mod                         # noqa: E402
from db import LibraryDB                            # noqa: E402

ITER_A = 300
ITER_B = 50
CATEGORIES = book_mod.CATEGORIES


def timing(coll, query, iters):
    t0 = time.perf_counter()
    for _ in range(iters):
        list(coll.find(query))
    total = (time.perf_counter() - t0) * 1000
    return total, total / iters


def plan(coll, query):
    try:
        ex = coll.database.command({"explain": {"find": coll.name, "filter": query},
                                    "verbosity": "executionStats"})
    except Exception as exc:
        return {"stage": "explain 不支持：%s" % exc, "docs": None, "keys": None, "n": None}
    stats = ex.get("executionStats", {}) or {}
    stages = []

    def walk(node):
        if isinstance(node, dict):
            if "stage" in node:
                stages.append(node["stage"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(ex.get("queryPlanner", {}).get("winningPlan", {}))
    return {
        "stage": " -> ".join(stages[-3:]) if stages else "-",
        "docs": stats.get("totalDocsExamined"),
        "keys": stats.get("totalKeysExamined"),
        "n": stats.get("nReturned"),
    }


def one_case(title, coll, query, index_specs, recreate, iters):
    for name in index_specs:
        try:
            coll.drop_index(name)
        except Exception:
            pass
    t_before, avg_before = timing(coll, query, iters)
    p_before = plan(coll, query)
    recreate(coll)
    t_after, avg_after = timing(coll, query, iters)
    p_after = plan(coll, query)
    print("\n%s（%d 次重复）" % (title, iters))
    print("  无索引：累计 %8.2f ms  单次 %7.3f ms  stage=%-22s 扫描文档=%s 返回=%s"
          % (t_before, avg_before, p_before["stage"], p_before["docs"], p_before["n"]))
    print("  有索引：累计 %8.2f ms  单次 %7.3f ms  stage=%-22s 扫描文档=%s 索引键=%s"
          % (t_after, avg_after, p_after["stage"], p_after["docs"], p_after["keys"]))
    if avg_after > 0:
        print("  单次耗时变化：%.2f 倍（>1 表示变快）" % (avg_before / avg_after))
    return avg_before, avg_after


def build_bench(db):
    """构造放大数据集：50000 本图书 + 300000 条借阅流水（时间序列集合）。"""
    if "books_bench" in db.db.list_collection_names():
        db.db.drop_collection("books_bench")
    if "borrow_bench" in db.db.list_collection_names():
        db.db.drop_collection("borrow_bench")
    db.db.create_collection("books_bench")
    db.db.create_collection("borrow_bench", timeseries={
        "timeField": "borrow_date", "metaField": "reader_card", "granularity": "hours"})

    rnd = random.Random(2025)
    docs = []
    base = datetime(2023, 1, 1)
    for i in range(50000):
        docs.append({
            "isbn": "99%011d" % i,
            "title": "馆藏图书样本 %05d %s" % (i, rnd.choice(["编程", "导论", "原理", "教程"])),
            "author": "作者%03d" % (i % 900),
            "publisher": "出版社%02d" % (i % 40),
            "category": rnd.choice(CATEGORIES),
            "price": round(rnd.uniform(20, 200), 2),
            "stock": rnd.randint(0, 30),
            "rating": round(rnd.uniform(3.0, 5.0), 1),
            "publish_date": base + timedelta(days=rnd.randint(0, 4000)),
            "borrow_count": rnd.randint(0, 300),
            "location": {"floor": "二楼", "shelf": "A-%02d" % (i % 50), "copies": 2},
            "tags": ["编程", "入门"],
        })
    db.db.books_bench.insert_many(docs)

    logs = []
    for i in range(300000):
        d = base + timedelta(days=rnd.randint(0, 1090), hours=rnd.randint(0, 23))
        logs.append({"borrow_date": d, "reader_card": "R2024%04d" % (i % 5000),
                     "book_isbn": "99%011d" % (i % 50000), "status": "已归还",
                     "duration_days": rnd.randint(1, 60)})
    for i in range(0, len(logs), 20000):
        db.db.borrow_bench.insert_many(logs[i:i + 20000])
    print("\n[放大数据集] books_bench=%d 条，borrow_bench=%d 条"
          % (db.db.books_bench.count_documents({}), db.db.borrow_bench.count_documents({})))


def main():
    with LibraryDB() as db:
        print("=" * 78)
        print("A. 真实教学数据集（books 50 / readers 30 / borrow_logs 3000）")
        print("=" * 78)
        one_case("Q1 类别+价格区间", db.books,
                 {"category": "计算机", "price": {"$gte": 50, "$lte": 90}},
                 ["idx_category_price"], book_mod.ensure_indexes, ITER_A)
        one_case("Q2 书名模糊（前缀可走索引）", db.books,
                 {"title": {"$regex": "^Python"}},
                 ["idx_title"], book_mod.ensure_indexes, ITER_A)
        one_case("Q3 出版年份区间", db.books,
                 {"publish_date": {"$gte": datetime(2019, 1, 1), "$lt": datetime(2023, 1, 1)}},
                 ["idx_publish_date"], book_mod.ensure_indexes, ITER_A)
        one_case("Q4 借阅流水按借阅证", db.borrow_logs,
                 {"reader_card": "R20240001"},
                 ["idx_reader_card"], borrow_mod.ensure_indexes, ITER_A)

        print("\n" + "=" * 78)
        print("B. 放大数据集（books_bench 50000 / borrow_bench 300000）")
        print("=" * 78)
        build_bench(db)

        def idx_books_bench(coll):
            coll.create_index([("category", ASCENDING), ("price", ASCENDING)], name="idx_category_price")
            coll.create_index([("title", ASCENDING)], name="idx_title")
            coll.create_index([("publish_date", ASCENDING)], name="idx_publish_date")

        def idx_borrow_bench(coll):
            coll.create_index([("reader_card", ASCENDING)], name="idx_reader_card")
            coll.create_index([("book_isbn", ASCENDING)], name="idx_book_isbn")

        one_case("Q1 类别+价格区间", db.db.books_bench,
                 {"category": "计算机", "price": {"$gte": 50, "$lte": 90}},
                 ["idx_category_price"], idx_books_bench, ITER_B)
        one_case("Q2 书名前缀匹配", db.db.books_bench,
                 {"title": {"$regex": "^馆藏图书样本 0004"}},
                 ["idx_title"], idx_books_bench, ITER_B)
        one_case("Q3 出版年份区间", db.db.books_bench,
                 {"publish_date": {"$gte": datetime(2019, 1, 1), "$lt": datetime(2021, 1, 1)}},
                 ["idx_publish_date"], idx_books_bench, ITER_B)
        one_case("Q4 借阅流水按借阅证", db.db.borrow_bench,
                 {"reader_card": "R20240007"},
                 ["idx_reader_card"], idx_borrow_bench, ITER_B)

        db.db.books_bench.drop()
        db.db.borrow_bench.drop()
        print("\n[清理] 已删除放大数据集，正式库不受影响。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
