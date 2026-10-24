from mongodb_connect import get_db


def borrow_book(reader_card, book_isbn):
    """借阅登记（insert_one）"""
    db, client = get_db()
    try:
        r = db.borrow_logs.insert_one({
            "borrow_date": __now(),
            "reader_card": reader_card,
            "book_isbn": book_isbn,
            "status": "借出"
        })
        print(f"借阅登记成功，_id={r.inserted_id}，受影响行数=1")
    finally:
        client.close()


def return_book(reader_card, book_isbn):
    """归还处理（update_many 将借出置为已归还并记录归还时间）"""
    db, client = get_db()
    try:
        r = db.borrow_logs.update_many(
            {"reader_card": reader_card, "book_isbn": book_isbn, "status": "借出"},
            {"$set": {"status": "已归还", "return_date": __now()}}
        )
        print(f"归还处理完成，受影响行数={r.modified_count}")
    finally:
        client.close()


def find_overdue():
    """查询逾期未还记录"""
    db, client = get_db()
    try:
        docs = list(db.borrow_logs.find({"status": "逾期"}))
        if not docs:
            print("查询无结果")
        else:
            for d in docs:
                print(f"{d['borrow_date']} | {d['reader_card']} | {d['book_isbn']} | {d['status']}")
            print(f"共 {len(docs)} 条逾期记录")
        return docs
    finally:
        client.close()


def find_borrows_by_reader(reader_card):
    """查询某读者全部借阅记录"""
    db, client = get_db()
    try:
        docs = list(db.borrow_logs.find({"reader_card": reader_card}))
        if not docs:
            print("查询无结果")
        else:
            for d in docs:
                print(f"{d['borrow_date']} | {d['book_isbn']} | {d['status']}")
    finally:
        client.close()


def __now():
    from datetime import datetime
    return datetime.now()
