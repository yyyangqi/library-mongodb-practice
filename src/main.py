"""主程序：菜单式交互（F7），覆盖图书/读者/借阅/统计/文件/日志六类功能。

运行：python main.py
"""
import sys
from datetime import datetime

from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError

import audit
import books as book_mod
import borrow as borrow_mod
import files as file_mod
import readers as reader_mod
import stats as stats_mod
from config import CONFIG
from db import LibraryDB

PAGE = CONFIG.get("ui", {}).get("page_size", 5)


def line(title=""):
    print("\n" + "=" * 70)
    if title:
        print(title)
        print("-" * 70)


def pause():
    try:
        input("\n按回车返回主菜单...")
    except EOFError:
        pass


def ui_list_books(db):
    line("图书列表（按借阅次数倒序，分页）")
    try:
        page = int(input("页码(默认1): ") or 1)
    except ValueError:
        page = 1
    docs, total = book_mod.list_books(db.books, page, PAGE, "borrow_count", -1)
    print("共 %d 条，第 %d 页：" % (total, page))
    for b in docs:
        print("  " + book_mod.fmt(b))


def ui_search_category_price(db):
    line("按类别 + 价格区间检索")
    print("类别可选：", "、".join(book_mod.CATEGORIES))
    cat = input("类别: ").strip()
    low = float(input("最低价: ") or 0)
    high = float(input("最高价: ") or 9999)
    docs, n = book_mod.by_category_price(db.books, cat, low, high)
    print("命中 %d 条" % n)
    for b in docs[:20]:
        print("  " + book_mod.fmt(b))


def ui_search_tags(db):
    line("按标签多选检索（须同时包含全部标签）")
    tags = [t.strip() for t in input("标签，用逗号分隔: ").split(",") if t.strip()]
    docs, n = book_mod.by_tags_all(db.books, tags)
    print("标签 %s 命中 %d 条" % (tags, n))
    for b in docs[:20]:
        print("  " + book_mod.fmt(b))


def ui_search_title(db):
    line("按书名模糊检索")
    kw = input("书名关键词: ").strip()
    docs, n = book_mod.by_title_like(db.books, kw)
    print("命中 %d 条" % n)
    for b in docs[:20]:
        print("  " + book_mod.fmt(b))


def ui_search_year(db):
    line("按出版年份范围检索")
    y1 = int(input("起始年份: ") or 2020)
    y2 = int(input("结束年份: ") or 2025)
    docs, n = book_mod.by_year_range(db.books, y1, y2)
    print("命中 %d 条" % n)
    for b in docs[:20]:
        print("  " + book_mod.fmt(b))


def ui_missing_tags(db):
    line("数据质量核查：缺少 tags 字段的图书")
    docs, n = book_mod.missing_tags(db.books)
    print("缺少 tags 的图书 %d 条" % n)
    for b in docs:
        print("  %-28s %s" % (b.get("title"), b.get("isbn")))


def ui_top_rated(db):
    line("评分 Top10（仅返回书名/作者/评分）")
    docs, n = book_mod.top_rated(db.books, 10)
    for i, b in enumerate(docs, 1):
        print("  %2d. %-30s %-12s %.1f" % (i, b.get("title"), b.get("author"), b.get("rating")))


def ui_add_book(db):
    line("新增图书")
    doc = {
        "isbn": input("ISBN-13: ").strip(),
        "title": input("书名: ").strip(),
        "author": input("作者: ").strip(),
        "publisher": input("出版社: ").strip(),
        "category": input("类别: ").strip(),
        "price": float(input("定价: ") or 0),
        "stock": int(input("库存: ") or 0),
        "rating": float(input("评分: ") or 0),
        "publish_date": datetime.strptime(input("出版日期(YYYY-MM-DD): ").strip(), "%Y-%m-%d"),
        "borrow_count": 0,
        "location": {
            "floor": input("楼层区域: ").strip(),
            "shelf": input("架位号: ").strip(),
            "copies": int(input("复本数: ") or 1),
        },
    }
    tags = input("标签(逗号分隔，可空): ").strip()
    if tags:
        doc["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    try:
        isbn = book_mod.add_book(db.books, doc)
        audit.write_audit(db.audit_logs, "INSERT", "books", "新增图书 %s" % doc["title"])
        print("已新增：%s" % isbn)
    except DuplicateKeyError:
        print("失败：ISBN 已存在（唯一索引 uk_isbn 冲突）")


def ui_delete_book(db):
    line("删除图书")
    isbn = input("ISBN: ").strip()
    n = book_mod.delete_book(db.books, isbn)
    if n:
        audit.write_audit(db.audit_logs, "DELETE", "books", "删除图书 ISBN=%s" % isbn)
    print("删除 %d 条" % n)


def ui_list_readers(db):
    line("读者列表 / 等级检索")
    college = input("学院筛选(可空): ").strip() or None
    docs, total = reader_mod.list_readers(db.readers, 1, PAGE, college)
    print("共 %d 条，前 %d 条：" % (total, len(docs)))
    for r in docs:
        print("  %s %-6s %-14s %-4s %s" % (r["card_no"], r["name"], r["college"],
                                           r["level"], r.get("email") or "-"))
    level = input("按等级检索(普通/高级/教师，可空): ").strip()
    if level:
        docs, n = reader_mod.by_level(db.readers, level)
        print("等级 %s 命中 %d 条：" % (level, n))
        for r in docs[:10]:
            print("  %s %s %s" % (r["card_no"], r["name"], r["college"]))


def ui_borrow(db):
    line("借书")
    card = input("借阅证号: ").strip()
    isbn = input("图书 ISBN: ").strip()
    if not db.readers.find_one({"card_no": card}):
        print("读者不存在")
        return
    book = db.books.find_one({"isbn": isbn})
    if not book:
        print("图书不存在")
        return
    if book.get("stock", 0) <= 0:
        print("库存不足，无法借出")
        return
    when = borrow_mod.borrow(db.borrow_logs, card, isbn, db.books, 30)
    audit.write_audit(db.audit_logs, "INSERT", "borrow_logs", "借出 %s -> %s" % (isbn, card))
    print("借出成功：%s" % when)


def ui_return(db):
    line("还书")
    card = input("借阅证号: ").strip()
    isbn = input("图书 ISBN: ").strip()
    days = borrow_mod.give_back(db.borrow_logs, card, isbn, db.books)
    print("未找到在借记录" if days is None else "归还成功，借阅 %d 天" % days)


def ui_borrow_history(db):
    line("读者借阅记录")
    card = input("借阅证号: ").strip()
    docs, n = borrow_mod.by_reader(db.borrow_logs, card, 20)
    print("共 %d 条（显示最近 20 条）：" % n)
    for d in docs:
        print("  %s %s %-4s %s天" % (d["borrow_date"].strftime("%Y-%m-%d"),
                                     d["book_isbn"], d["status"], d.get("duration_days", "-")))


def ui_stats_category(db):
    line("分类统计（并写入 category_stats 集合）")
    for r in stats_mod.by_category(db.books):
        print("  %-6s 藏书%2d 种  均价%7.2f  平均评分%.2f  在架%3d"
              % (r["_id"], r["book_count"], r["avg_price"], r["avg_rating"], r["total_stock"]))
    saved = stats_mod.save_category_stats(db.books, db.category_stats)
    print("已写入 category_stats：%d 条" % len(saved))


def ui_stats_college(db):
    line("各学院借阅量 Top5")
    for i, r in enumerate(stats_mod.top_colleges(db.borrow_logs, db.readers), 1):
        print("  %d. %-14s 借阅%5d 次  读者%2d 人" % (i, r["college"], r["borrows"], r["reader_count"]))


def ui_stats_trend(db):
    line("月度借阅趋势")
    rows = stats_mod.monthly_trend(db.borrow_logs)
    for r in rows:
        print("  %s %4d 次" % (r["label"], r["count"]))
    print("  合计 %d 条" % sum(r["count"] for r in rows))


def ui_stats_top_books(db):
    line("借阅次数 Top10（关联馆藏位置）")
    for i, r in enumerate(stats_mod.top_borrowed_books(db.borrow_logs, db.books, 10), 1):
        loc = r.get("location") or {}
        print("  %2d. %-28s %4d次  %s %s" % (i, r["title"][:26], r["times"],
                                             loc.get("floor", ""), loc.get("shelf", "")))


def ui_upload_files(db):
    line("上传电子书与封面到 GridFS")
    manifest = CONFIG["paths"]["data_dir"] + "/gridfs_files/files_manifest.txt"
    file_dir = CONFIG["paths"]["data_dir"] + "/gridfs_files"
    ups = file_mod.upload_from_manifest(db.fs, manifest, file_dir, db.books)
    for name, ftype, isbn, size in ups:
        print("  已上传 %-14s %-6s %-14s %6d 字节" % (name, ftype, isbn, size))
    audit.write_audit(db.audit_logs, "UPLOAD", "gridfs", "上传 %d 个文件" % len(ups))


def ui_download_ebook(db):
    line("按书名下载电子书并校验字节数")
    title = input("书名关键词: ").strip()
    book, fs_meta, results = file_mod.download_by_title(db.fs, db.books, title,
                                                        CONFIG["paths"]["download_dir"])
    if not book:
        print("未找到匹配图书")
        return
    print("图书：%s  ISBN=%s" % (book["title"], book["isbn"]))
    if not results:
        print("该书没有关联的 GridFS 文件")
        return
    for r in results:
        print("  %s -> %s  GridFS=%d 字节  本地=%d 字节  %s"
              % (r["filename"], r["local"], r["gridfs_bytes"], r["local_bytes"],
                 "一致" if r["match"] else "不一致"))
        audit.write_audit(db.audit_logs, "DOWNLOAD", "gridfs", "下载 %s" % r["filename"])


def ui_list_files(db):
    line("GridFS 文件清单")
    rows = file_mod.list_files(db.fs)
    print("  %-14s %8s %-8s %-20s %-14s" % ("文件名", "大小KB", "类型", "上传时间", "关联ISBN"))
    for r in rows:
        print("  %-14s %8.1f %-8s %-20s %-14s" % (r["filename"], r["size_kb"], r["file_type"],
                                                  r["upload_date"], r["isbn"]))
    print("  合计 %d 个文件，%d 字节" % (len(rows), sum(r["bytes"] for r in rows)))


def ui_audit(db):
    line("最近 100 条操作日志")
    for r in audit.recent(db.audit_logs, 100)[:20]:
        print("  %s %-8s %-10s %-30s %s" % (r["ts"].strftime("%Y-%m-%d %H:%M:%S"),
                                            r["action"], r["operator"][:10], r["target"],
                                            r["detail"][:24]))
    print("  动作分布：", audit.summary(db.audit_logs))


def ui_export(db):
    line("导出统计结果（CSV）")
    import csv
    import os
    path = os.path.join(CONFIG["paths"]["export_dir"], "category_stats.csv")
    rows = list(db.category_stats.find({}, {"_id": 0}))
    os.makedirs(CONFIG["paths"]["export_dir"], exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["category", "book_count", "avg_price", "avg_rating"])
        w.writeheader()
        w.writerows(rows)
    audit.write_audit(db.audit_logs, "EXPORT", "category_stats", "导出 %d 行" % len(rows))
    print("已导出：%s（%d 行）" % (path, len(rows)))


MENU = [
    ("1", "图书列表（分页 + 排序）", ui_list_books),
    ("2", "按类别 + 价格区间检索", ui_search_category_price),
    ("3", "按标签多选检索（$all）", ui_search_tags),
    ("4", "按书名模糊检索", ui_search_title),
    ("5", "按出版年份范围检索", ui_search_year),
    ("6", "数据质量核查（缺 tags）", ui_missing_tags),
    ("7", "评分 Top10", ui_top_rated),
    ("8", "新增图书", ui_add_book),
    ("9", "删除图书", ui_delete_book),
    ("10", "读者列表 / 等级检索", ui_list_readers),
    ("11", "借书 / 还书", ui_borrow),
    ("12", "读者借阅记录", ui_borrow_history),
    ("13", "分类统计 + 落库", ui_stats_category),
    ("14", "学院借阅 Top5", ui_stats_college),
    ("15", "月度借阅趋势", ui_stats_trend),
    ("16", "借阅排行 Top10 + 馆藏位置", ui_stats_top_books),
    ("17", "上传电子书到 GridFS", ui_upload_files),
    ("18", "按书名下载并校验字节数", ui_download_ebook),
    ("19", "GridFS 文件清单", ui_list_files),
    ("20", "最近 100 条操作日志", ui_audit),
    ("21", "导出统计结果 CSV", ui_export),
]

HANDLERS = dict((key, func) for key, _, func in MENU)


def main():
    try:
        db = LibraryDB()
        db.ping()
    except PyMongoError as exc:
        print("数据库连接失败：%s" % exc)
        print("请确认 mongod 已启动、config/config.json 中的连接参数正确。")
        return 1
    print("智慧图书馆数字资源平台  v1.0")
    print("数据库 %s  读取偏好 %s" % (CONFIG["mongo"]["db_name"], db.read_preference_name))
    while True:
        line()
        print(" 智慧图书馆数字资源平台 —— 主菜单")
        print("-" * 70)
        for key, name, _ in MENU:
            print("  %-3s %s" % (key, name))
        print("   0  退出")
        try:
            choice = input("\n请选择: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if choice == "0":
            break
        func = HANDLERS.get(choice)
        if not func:
            print("无效选项")
            continue
        try:
            func(db)
        except OperationFailure as exc:
            print("[权限或操作被拒绝] %s" % exc)
        except ValueError:
            print("[输入格式错误] 请检查数字/日期格式")
        pause()
    db.close()
    print("已退出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
