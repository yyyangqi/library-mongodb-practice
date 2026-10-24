from mongodb_connect import get_db


def add_book(doc):
    """新增一本图书（insert_one）"""
    db, client = get_db()
    try:
        r = db.books.insert_one(doc)
        print(f"新增图书成功，_id={r.inserted_id}，受影响行数=1")
    finally:
        client.close()


def batch_add_books(docs):
    """批量新增图书（insert_many）"""
    db, client = get_db()
    try:
        r = db.books.insert_many(docs)
        print(f"批量新增图书成功，共 {len(r.inserted_ids)} 本")
    finally:
        client.close()


def find_by_isbn(isbn):
    """按 ISBN 精确查找"""
    db, client = get_db()
    try:
        doc = db.books.find_one({"isbn": isbn})
        if not doc:
            print("未找到该 ISBN 对应的图书")
            return None
        print(doc)
        return doc
    finally:
        client.close()


def find_by_condition(condition):
    """按条件检索（字典形式，如 {"category": "计算机", "price": {"$gt": 80}}）"""
    db, client = get_db()
    try:
        docs = list(db.books.find(condition))
        if not docs:
            print("查询无结果")
        else:
            for d in docs:
                print(f"{d['isbn']} | {d['title']} | {d['category']} | 价格{d['price']} | 库存{d['stock']} | 评分{d['rating']}")
            print(f"共 {len(docs)} 条结果")
        return docs
    finally:
        client.close()


def update_stock(isbn, delta):
    """调整某本书库存（update_one + $inc）"""
    db, client = get_db()
    try:
        r = db.books.update_one({"isbn": isbn}, {"$inc": {"stock": delta}})
        print(f"库存调整完成，受影响行数={r.modified_count}")
    finally:
        client.close()


def update_price_by_category(category, factor):
    """按类别统一调价（update_many + $mul）"""
    db, client = get_db()
    try:
        r = db.books.update_many({"category": category}, {"$mul": {"price": factor}})
        print(f"{category}类图书调价完成，受影响行数={r.modified_count}")
    finally:
        client.close()


def delete_book(isbn):
    """删除一本图书（delete_one）"""
    db, client = get_db()
    try:
        r = db.books.delete_one({"isbn": isbn})
        print(f"删除图书完成，受影响行数={r.deleted_count}")
    finally:
        client.close()


def delete_books_by_category(category):
    """按类别批量删除（delete_many）"""
    db, client = get_db()
    try:
        r = db.books.delete_many({"category": category})
        print(f"批量删除完成，受影响行数={r.deleted_count}")
    finally:
        client.close()


def rating_rank(limit=5):
    """按评分降序输出排行榜"""
    db, client = get_db()
    try:
        docs = list(db.books.find().sort("rating", -1).limit(limit))
        if not docs:
            print("查询无结果")
        else:
            for i, d in enumerate(docs, 1):
                print(f"{i}. {d['title']} | 评分{d['rating']} | 借阅{d['borrow_count']}次")
    finally:
        client.close()
