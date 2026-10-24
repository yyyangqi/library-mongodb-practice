from mongodb_connect import get_db


def add_reader(doc):
    """新增读者（insert_one）"""
    db, client = get_db()
    try:
        r = db.readers.insert_one(doc)
        print(f"新增读者成功，_id={r.inserted_id}，受影响行数=1")
    finally:
        client.close()


def find_reader(card_no):
    """按借阅证号查找读者"""
    db, client = get_db()
    try:
        doc = db.readers.find_one({"card_no": card_no})
        if not doc:
            print("未找到该读者")
            return None
        print(doc)
        return doc
    finally:
        client.close()


def list_readers():
    """列出全部读者"""
    db, client = get_db()
    try:
        docs = list(db.readers.find())
        if not docs:
            print("查询无结果")
        else:
            for d in docs:
                print(f"{d['card_no']} | {d['name']} | {d['college']} | {d['level']} | 邮箱={d.get('email')}")
        return docs
    finally:
        client.close()


def total_count():
    """统计读者总数（count_documents）"""
    db, client = get_db()
    try:
        n = db.readers.count_documents({})
        print(f"读者总数={n}")
        return n
    finally:
        client.close()


def college_names():
    """获取学院清单（distinct）"""
    db, client = get_db()
    try:
        cols = db.readers.distinct("college")
        print("学院清单：", cols)
        return cols
    finally:
        client.close()


def college_stats():
    """按学院统计读者人数（聚合）"""
    db, client = get_db()
    try:
        pipe = [
            {"$group": {"_id": "$college", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        rows = list(db.readers.aggregate(pipe))
        if not rows:
            print("查询无结果")
        for r in rows:
            print(f"{r['_id']}：{r['count']} 人")
    finally:
        client.close()


def level_distribution():
    """按借阅等级统计人数（聚合）"""
    db, client = get_db()
    try:
        pipe = [
            {"$group": {"_id": "$level", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        rows = list(db.readers.aggregate(pipe))
        if not rows:
            print("查询无结果")
        for r in rows:
            print(f"{r['_id']}：{r['count']} 人")
    finally:
        client.close()
