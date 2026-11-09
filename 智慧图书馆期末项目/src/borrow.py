"""借阅管理模块（F3/F4）：借书、还书、逾期查询与流水检索。

borrow_logs 是时间序列集合（time-series），字段划分：
  timeField=borrow_date, metaField=reader_card, granularity=hours
因此 reader_card 属于 metaField，可在其上建索引；book_isbn、status 等为普通字段，
在时间序列集合中作为 measurement 存储。
"""
from datetime import datetime, timedelta

from pymongo import ASCENDING, DESCENDING


def borrow(coll, reader_card, book_isbn, books_coll, days=30):
    now = datetime.now().replace(microsecond=0)
    coll.insert_one({
        "borrow_date": now,
        "reader_card": reader_card,
        "book_isbn": book_isbn,
        "status": "借出",
        "duration_days": days,
    })
    books_coll.update_one({"isbn": book_isbn}, {"$inc": {"borrow_count": 1, "stock": -1}})
    return now


def give_back(coll, reader_card, book_isbn, books_coll):
    now = datetime.now().replace(microsecond=0)
    log = coll.find_one_and_update(
        {"reader_card": reader_card, "book_isbn": book_isbn, "status": {"$ne": "已归还"}},
        {"$set": {"return_date": now, "status": "已归还"}},
        sort=[("borrow_date", DESCENDING)],
        return_document=False,
    )
    if log is None:
        return None
    days = max((now - log["borrow_date"]).days, 0)
    coll.update_one({"_id": log["_id"]}, {"$set": {"duration_days": days}})
    books_coll.update_one({"isbn": book_isbn}, {"$inc": {"stock": 1}})
    return days


def by_reader(coll, reader_card, limit=50):
    q = {"reader_card": reader_card}
    return list(coll.find(q, {"_id": 0}).sort("borrow_date", DESCENDING).limit(limit)), \
        coll.count_documents(q)


def unreturned(coll):
    q = {"status": {"$in": ["借出", "逾期"]}}
    return list(coll.find(q, {"_id": 0}).sort("borrow_date", DESCENDING).limit(50)), \
        coll.count_documents(q)


def by_date_range(coll, d1, d2):
    q = {"borrow_date": {"$gte": d1, "$lt": d2}}
    return list(coll.find(q, {"_id": 0}).limit(20)), coll.count_documents(q)


def ensure_indexes(coll):
    # 时间序列集合：metaField 索引 + 常用查询字段（部分为 measurement 字段索引）
    coll.create_index([("reader_card", ASCENDING)], name="idx_reader_card")
    coll.create_index([("book_isbn", ASCENDING)], name="idx_book_isbn")
    coll.create_index([("status", ASCENDING)], name="idx_status")
