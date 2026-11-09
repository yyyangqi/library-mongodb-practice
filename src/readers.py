"""读者管理模块（F3）：读者信息的增删改查与条件检索。"""
from pymongo import ASCENDING, DESCENDING


def list_readers(coll, page=1, size=5, college=None):
    q = {"college": college} if college else {}
    total = coll.count_documents(q)
    cur = coll.find(q, {"_id": 0}).sort("card_no", ASCENDING).skip((page - 1) * size).limit(size)
    return list(cur), total


def add_reader(coll, doc):
    coll.insert_one(dict(doc))
    return doc.get("card_no")


def update_reader(coll, card_no, fields):
    return coll.update_one({"card_no": card_no}, {"$set": fields}).modified_count


def delete_reader(coll, card_no):
    return coll.delete_one({"card_no": card_no}).deleted_count


def by_level(coll, level):
    q = {"level": level}
    return list(coll.find(q, {"_id": 0})), coll.count_documents(q)


def by_fav_category(coll, category):
    """按偏好类别检索：数组字段等值匹配即可命中数组内元素。"""
    q = {"fav_categories": category}
    return list(coll.find(q, {"_id": 0})), coll.count_documents(q)


def missing_email(coll):
    q = {"email": {"$in": [None, ""]}}
    return list(coll.find(q, {"_id": 0})), coll.count_documents(q)


def ensure_indexes(coll):
    coll.create_index([("card_no", ASCENDING)], unique=True, name="uk_card_no")
    coll.create_index([("college", ASCENDING)], name="idx_college")
    coll.create_index([("level", ASCENDING)], name="idx_level")
    coll.create_index([("fav_categories", ASCENDING)], name="idx_fav_categories")
