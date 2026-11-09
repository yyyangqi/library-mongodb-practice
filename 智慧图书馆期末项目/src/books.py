"""图书管理模块（F3）：增删改查、条件检索、分页排序。"""
import re
from datetime import datetime

from pymongo import ASCENDING, DESCENDING

CATEGORIES = ["计算机", "文学", "经济管理", "数学", "外语", "历史"]


def fmt(b):
    loc = b.get("location") or {}
    return "%-32s %-10s %-12s %5.1f元 库存%2d 评分%.1f %s/%s" % (
        b.get("title", "")[:30], b.get("category", ""), b.get("author", "")[:10],
        b.get("price", 0), b.get("stock", 0), b.get("rating", 0),
        loc.get("floor", ""), loc.get("shelf", ""))


def list_books(coll, page=1, size=5, sort_field="borrow_count", order=-1):
    """分页 + 排序：skip/limit 模式，配合索引可支撑页面跳转。"""
    total = coll.count_documents({})
    cur = coll.find({}, {"_id": 0}).sort(sort_field, order).skip((page - 1) * size).limit(size)
    return list(cur), total


def add_book(coll, doc):
    doc.setdefault("borrow_count", 0)
    doc.setdefault("stock", 0)
    coll.insert_one(dict(doc))
    return doc.get("isbn")


def update_book(coll, isbn, fields: dict):
    res = coll.update_one({"isbn": isbn}, {"$set": fields})
    return res.modified_count


def delete_book(coll, isbn):
    res = coll.delete_one({"isbn": isbn})
    return res.deleted_count


# ---------------- 六类检索 ----------------
def by_category_price(coll, category, low, high):
    """按类别 + 价格区间组合筛选（命中索引 category_1_price_1）。"""
    q = {"category": category, "price": {"$gte": low, "$lte": high}}
    return list(coll.find(q, {"_id": 0})), coll.count_documents(q)


def by_tags_all(coll, tags):
    """按标签多选匹配，要求同时包含全部标签（$all）。"""
    q = {"tags": {"$all": tags}}
    return list(coll.find(q, {"_id": 0})), coll.count_documents(q)


def by_title_like(coll, keyword):
    """书名模糊检索（正则），同时给出大小写不敏感形式。"""
    q = {"title": {"$regex": re.escape(keyword), "$options": "i"}}
    return list(coll.find(q, {"_id": 0})), coll.count_documents(q)


def by_year_range(coll, y1, y2):
    q = {"publish_date": {"$gte": datetime(y1, 1, 1), "$lt": datetime(y2 + 1, 1, 1)}}
    return list(coll.find(q, {"_id": 0})), coll.count_documents(q)


def missing_tags(coll):
    """数据质量核查：tags 字段不存在（注意 $exists:false 也会命中 tags 为 null）。"""
    q = {"tags": {"$exists": False}}
    return list(coll.find(q, {"_id": 0})), coll.count_documents(q)


def top_rated(coll, n=10):
    """按评分排序取前 N，只返回书名、作者、评分（投影 + 覆盖查询）。"""
    cur = coll.find({}, {"_id": 0, "title": 1, "author": 1, "rating": 1}).sort("rating", DESCENDING).limit(n)
    return list(cur), n


def ensure_indexes(coll):
    coll.create_index([("isbn", ASCENDING)], unique=True, name="uk_isbn")
    coll.create_index([("category", ASCENDING), ("price", ASCENDING)], name="idx_category_price")
    coll.create_index([("tags", ASCENDING)], name="idx_tags")
    coll.create_index([("title", ASCENDING)], name="idx_title")
    coll.create_index([("publish_date", ASCENDING)], name="idx_publish_date")
    coll.create_index([("rating", DESCENDING)], name="idx_rating_desc")
    coll.create_index([("borrow_count", DESCENDING)], name="idx_borrow_count_desc")
