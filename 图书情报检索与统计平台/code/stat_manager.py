from mongodb_connect import get_db


def category_stats():
    """分类统计：按类别分组，统计库存总量、平均价格、图书数量，按库存总量降序"""
    db, client = get_db()
    try:
        pipe = [
            {"$group": {
                "_id": "$category",
                "total_stock": {"$sum": "$stock"},
                "avg_price": {"$avg": "$price"},
                "book_count": {"$sum": 1}
            }},
            {"$sort": {"total_stock": -1}}
        ]
        rows = list(db.books.aggregate(pipe))
        if not rows:
            print("查询无结果")
        for r in rows:
            print(f"{r['_id']} | 库存总量{r['total_stock']} | 平均价格{round(r['avg_price'], 2)} | 图书数量{r['book_count']}")
    finally:
        client.close()


def borrow_trend():
    """借阅趋势：按年份分组统计借阅量，格式化输出"""
    db, client = get_db()
    try:
        pipe = [
            {"$group": {
                "_id": {"$year": "$borrow_date"},
                "borrow_count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}},
            {"$project": {"year": {"$dateToString": {"format": "%Y年", "date": {"$dateFromParts": {"year": "$_id"}}}}, "borrow_count": 1, "_id": 0}}
        ]
        rows = list(db.borrow_logs.aggregate(pipe))
        if not rows:
            print("查询无结果")
        for r in rows:
            print(f"{r['year']} 借阅 {r['borrow_count']} 次")
    finally:
        client.close()


def bestseller(limit=5):
    """畅销榜：取借阅次数最多的图书"""
    db, client = get_db()
    try:
        pipe = [
            {"$sort": {"borrow_count": -1}},
            {"$limit": limit},
            {"$project": {"title": 1, "borrow_count": 1, "price": 1, "_id": 0}}
        ]
        rows = list(db.books.aggregate(pipe))
        if not rows:
            print("查询无结果")
        for i, r in enumerate(rows, 1):
            print(f"{i}. {r['title']} | 借阅{r['borrow_count']}次 | 价格{r['price']}元")
    finally:
        client.close()
