"""任务三执行记录脚本：一次性跑完 11 项检索与统计功能，输出「命令 + 结果条数」。

用法：python tools/exec_functions.py
"""
import io
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import books as book_mod                            # noqa: E402
import stats as stats_mod                           # noqa: E402
from config import CONFIG                           # noqa: E402
from db import LibraryDB                            # noqa: E402

OUT = io.StringIO()


def out(text=""):
    print(text)
    OUT.write(text + "\n")


def main():
    with LibraryDB() as db:
        out("智慧图书馆数字资源平台 —— 任务三 检索与统计执行记录")
        out("执行时间：%s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        out("数据库：%s  集合文档数：books=%d readers=%d borrow_logs=%d"
            % (CONFIG["mongo"]["db_name"], db.books.count_documents({}),
               db.readers.count_documents({}), db.borrow_logs.count_documents({})))

        # ---------- 检索 1 ----------
        out("\n[检索 1] 按类别与价格区间组合筛选")
        out('  db.books.find({category:"计算机", price:{$gte:50,$lte:90}})')
        docs, n = book_mod.by_category_price(db.books, "计算机", 50, 90)
        out("  结果条数：%d" % n)
        for b in docs[:5]:
            out("    " + book_mod.fmt(b))

        # ---------- 检索 2 ----------
        out("\n[检索 2] 按标签多选匹配（同时含多个标签）")
        tags = ["编程", "入门"]
        out('  db.books.find({tags:{$all:["编程","入门"]}})')
        docs, n = book_mod.by_tags_all(db.books, tags)
        out("  结果条数：%d" % n)
        for b in docs[:5]:
            out("    " + book_mod.fmt(b))

        # ---------- 检索 3 ----------
        out("\n[检索 3] 按书名模糊检索")
        out('  db.books.find({title:{$regex:"编程",$options:"i"}})')
        docs, n = book_mod.by_title_like(db.books, "编程")
        out("  结果条数：%d" % n)
        for b in docs[:5]:
            out("    " + book_mod.fmt(b))

        # ---------- 检索 4 ----------
        out("\n[检索 4] 按出版年份范围检索（2019—2022）")
        out('  db.books.find({publish_date:{$gte:ISODate("2019-01-01"),$lt:ISODate("2023-01-01")}})')
        docs, n = book_mod.by_year_range(db.books, 2019, 2022)
        out("  结果条数：%d" % n)
        for b in docs[:5]:
            out("    " + book_mod.fmt(b))

        # ---------- 检索 5 ----------
        out("\n[检索 5] 查询缺少 tags 字段的图书（数据质量核查）")
        out('  db.books.find({tags:{$exists:false}})')
        docs, n = book_mod.missing_tags(db.books)
        out("  结果条数：%d" % n)
        for b in docs:
            out("    %s  %s" % (b.get("isbn"), b.get("title")))

        # ---------- 检索 6 ----------
        out("\n[检索 6] 按评分排序取前 10，只返回书名/作者/评分")
        out('  db.books.find({},{_id:0,title:1,author:1,rating:1}).sort({rating:-1}).limit(10)')
        docs, _ = book_mod.top_rated(db.books, 10)
        out("  结果条数：%d" % len(docs))
        for i, b in enumerate(docs, 1):
            out("    %2d. %-30s %-12s %.1f" % (i, b["title"], b["author"], b["rating"]))

        # ---------- 统计 1 ----------
        out("\n[统计 1] 按类别统计藏书量、平均价格、平均评分")
        out('  db.books.aggregate([{$group:{_id:"$category", book_count:{$sum:1}, '
            'avg_price:{$avg:"$price"}, avg_rating:{$avg:"$rating"}}}])')
        rows = stats_mod.by_category(db.books)
        out("  结果条数：%d" % len(rows))
        for r in rows:
            out("    %-6s 藏书%2d 种  均价%7.2f  平均评分%.2f  在架合计%3d"
                % (r["_id"], r["book_count"], r["avg_price"], r["avg_rating"], r["total_stock"]))

        # ---------- 统计 2 ----------
        out("\n[统计 2] 各学院借阅总量 Top5（borrow_logs $lookup readers）")
        rows = stats_mod.top_colleges(db.borrow_logs, db.readers, 5)
        out("  结果条数：%d" % len(rows))
        for i, r in enumerate(rows, 1):
            out("    %d. %-16s 借阅 %4d 次  读者 %2d 人" % (i, r["college"], r["borrows"], r["reader_count"]))

        # ---------- 统计 3 ----------
        out("\n[统计 3] 按年月统计借阅趋势（可读标签）")
        rows = stats_mod.monthly_trend(db.borrow_logs)
        out('  db.borrow_logs.aggregate([{$group:{_id:{y:{$year:"$borrow_date"},m:{$month:"$borrow_date"}}}])')
        out("  结果条数：%d（%s ~ %s）" % (len(rows), rows[0]["label"], rows[-1]["label"]))
        for r in rows:
            out("    %s  %4d 次" % (r["label"], r["count"]))

        # ---------- 统计 4 ----------
        out("\n[统计 4] 借阅次数 Top10 图书并关联馆藏位置")
        rows = stats_mod.top_borrowed_books(db.borrow_logs, db.books, 10)
        out("  结果条数：%d" % len(rows))
        for i, r in enumerate(rows, 1):
            loc = r.get("location") or {}
            out("    %2d. %-30s %4d 次  %s / %s"
                % (i, r["title"][:28], r["times"], loc.get("floor"), loc.get("shelf")))

        # ---------- 统计 5 ----------
        out("\n[统计 5] 分类统计结果写入新集合 category_stats")
        saved = stats_mod.save_category_stats(db.books, db.category_stats)
        out('  db.books.aggregate([...{$out:"category_stats"}])')
        out("  写入条数：%d" % len(saved))
        for r in saved:
            out("    %-6s %2d 种  均价%.2f  评分%.2f"
                % (r["category"], r["book_count"], r["avg_price"], r["avg_rating"]))

        # ---------- 附加 ----------
        out("\n[附加] 借阅状态分布")
        for s, c in stats_mod.status_distribution(db.borrow_logs):
            out("    %-4s %4d 条" % (s, c))
        out("\n[附加] 年度借阅趋势")
        for y, c in stats_mod.yearly_trend(db.borrow_logs):
            out("    %d 年  %4d 次" % (y, c))

    path = os.path.join(CONFIG["base_dir"], "records", "任务三_检索与统计执行记录.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n记录已保存：%s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
