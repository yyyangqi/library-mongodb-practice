# 任务五程序验证：调用各模块功能确认可运行
import sys, io
sys.path.insert(0, r"C:\Users\26295\Doubao\chats\2026-10-21\new-chat\图书情报检索与统计平台\code")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from mongodb_connect import get_db
import book_manager, reader_manager, borrow_manager, stat_manager

print("########## 1. 数据库连接状态 ##########")
db, client = get_db()
db.command("ping")
for name in ["books", "readers", "borrow_logs", "category_stats"]:
    print(f"集合 {name} 文档数 = {db[name].count_documents({})}")
client.close()

print("\n########## 2. 图书条件检索（计算机类价格>80）##########")
book_manager.find_by_condition({"category": "计算机", "price": {"$gt": 80}})

print("\n########## 3. 图书评分排行榜前5 ##########")
book_manager.rating_rank(5)

print("\n########## 4. 读者学院统计 ##########")
reader_manager.college_stats()

print("\n########## 5. 读者借阅等级分布 ##########")
reader_manager.level_distribution()

print("\n########## 6. 逾期借阅查询 ##########")
borrow_manager.find_overdue()

print("\n########## 7. 分类统计（库存/均价/数量）##########")
stat_manager.category_stats()

print("\n########## 8. 借阅趋势（按年份）##########")
stat_manager.borrow_trend()

print("\n########## 9. 畅销榜 ##########")
stat_manager.bestseller(5)

print("\n全部功能验证通过！")
