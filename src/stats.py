"""统计分析模块（F4）：分类统计、借阅排行、年度趋势、多集合联合分析。"""
from datetime import datetime

from pymongo import ASCENDING, DESCENDING


def by_category(books):
    """按类别统计藏书量、平均价格、平均评分。"""
    pipe = [
        {"$group": {
            "_id": "$category",
            "book_count": {"$sum": 1},
            "avg_price": {"$avg": "$price"},
            "avg_rating": {"$avg": "$rating"},
            "total_stock": {"$sum": "$stock"},
        }},
        {"$sort": {"book_count": DESCENDING}},
    ]
    rows = list(books.aggregate(pipe))
    for r in rows:
        r["avg_price"] = round(r["avg_price"], 2)
        r["avg_rating"] = round(r["avg_rating"], 2)
    return rows


def top_colleges(borrow_logs, readers, n=5):
    """统计各学院借阅总量 Top N：借阅流水 -> $lookup 读者 -> 按学院汇总。"""
    pipe = [
        {"$group": {"_id": "$reader_card", "borrows": {"$sum": 1}}},
        {"$lookup": {
            "from": "readers",
            "localField": "_id",
            "foreignField": "card_no",
            "as": "reader",
        }},
        {"$unwind": "$reader"},
        {"$group": {"_id": "$reader.college", "borrows": {"$sum": "$borrows"},
                    "readers": {"$addToSet": "$_id"}}},
        {"$project": {"college": "$_id", "borrows": 1, "reader_count": {"$size": "$readers"}, "_id": 0}},
        {"$sort": {"borrows": DESCENDING}},
        {"$limit": n},
    ]
    return list(borrow_logs.aggregate(pipe))


def monthly_trend(borrow_logs):
    """按年月统计借阅趋势，输出可读的 'YYYY-MM' 标签。"""
    pipe = [
        {"$group": {
            "_id": {"y": {"$year": "$borrow_date"}, "m": {"$month": "$borrow_date"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.y": ASCENDING, "_id.m": ASCENDING}},
        {"$project": {
            "_id": 0,
            "label": {"$concat": [
                {"$toString": "$_id.y"}, "-",
                {"$cond": [{"$lt": ["$_id.m", 10]},
                           {"$concat": ["0", {"$toString": "$_id.m"}]},
                           {"$toString": "$_id.m"}]},
            ]},
            "year": "$_id.y", "month": "$_id.m", "count": 1,
        }},
    ]
    return list(borrow_logs.aggregate(pipe))


def top_borrowed_books(borrow_logs, books, n=10):
    """借阅次数最多的 N 本图书，并 $lookup 关联馆藏位置。"""
    pipe = [
        {"$group": {"_id": "$book_isbn", "times": {"$sum": 1}}},
        {"$sort": {"times": DESCENDING}},
        {"$limit": n},
        {"$lookup": {
            "from": "books",
            "localField": "_id",
            "foreignField": "isbn",
            "as": "book",
        }},
        {"$unwind": "$book"},
        {"$project": {
            "_id": 0, "isbn": "$_id", "times": 1,
            "title": "$book.title", "category": "$book.category",
            "location": "$book.location", "shelf": "$book.location.shelf",
        }},
    ]
    return list(borrow_logs.aggregate(pipe))


def yearly_trend(borrow_logs):
    pipe = [
        {"$group": {"_id": {"$year": "$borrow_date"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    return [(r["_id"], r["count"]) for r in borrow_logs.aggregate(pipe)]


def status_distribution(borrow_logs):
    pipe = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}, {"$sort": {"count": DESCENDING}}]
    return [(r["_id"], r["count"]) for r in borrow_logs.aggregate(pipe)]


def save_category_stats(books, target_coll):
    """将分类统计结果写入独立集合 category_stats，供后续查询与导出。
    用 $out 原子替换，避免重复数据。"""
    pipe = [
        {"$group": {
            "_id": "$category",
            "book_count": {"$sum": 1},
            "avg_price": {"$avg": "$price"},
            "avg_rating": {"$avg": "$rating"},
        }},
        {"$project": {"_id": 0, "category": "$_id", "book_count": 1,
                      "avg_price": {"$round": ["$avg_price", 2]},
                      "avg_rating": {"$round": ["$avg_rating", 2]}}},
        {"$sort": {"book_count": DESCENDING}},
        {"$out": target_coll.name},
    ]
    list(books.aggregate(pipe))
    return list(target_coll.find({}, {"_id": 0}))


def ensure_indexes(target_coll):
    target_coll.create_index([("category", ASCENDING)], unique=True, name="uk_category")
