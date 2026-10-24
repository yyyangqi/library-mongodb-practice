from mongodb_connect import get_db
import book_manager
import reader_manager
import borrow_manager
import stat_manager


def show_banner():
    """启动时打印连接状态与各集合文档总数"""
    db, client = get_db()
    try:
        db.command("ping")
        print("=" * 56)
        print("图书情报检索与统计平台 · PyMongo 应用")
        print("=" * 56)
        print("数据库连接状态：成功")
        print("数据库：library")
        for name in ["books", "readers", "borrow_logs", "category_stats"]:
            try:
                n = db[name].count_documents({})
                print("集合 " + name + " 文档总数 = " + str(n))
            except Exception:
                print("集合 " + name + " 尚未创建")
    finally:
        client.close()


def menu():
    print("\n" + "=" * 56)
    print("功能菜单")
    print("=" * 56)
    print(" 1. 新增图书（insert_one）")
    print(" 2. 按ISBN查询图书")
    print(" 3. 按条件检索图书（如 类别/价格范围）")
    print(" 4. 图书评分排行榜（前5）")
    print(" 5. 调整图书库存")
    print(" 6. 删除图书")
    print(" 7. 读者列表与学院统计")
    print(" 8. 读者借阅等级分布")
    print(" 9. 借阅登记 / 归还处理")
    print("10. 逾期记录查询")
    print("11. 分类统计（库存/均价/数量）")
    print("12. 借阅趋势（按年份）")
    print("13. 畅销榜")
    print(" 0. 退出")
    print("=" * 56)


def main():
    show_banner()
    while True:
        menu()
        try:
            choice = input("请输入功能编号：").strip()
        except (EOFError, KeyboardInterrupt):
            print("已退出，连接已关闭。")
            break
        if choice == "0":
            print("正在关闭数据库连接，再见！")
            break
        elif choice == "1":
            isbn = input("ISBN：").strip()
            title = input("书名：").strip()
            author = input("作者：").strip()
            publisher = input("出版社：").strip()
            category = input("类别：").strip()
            price = float(input("价格："))
            stock = int(input("库存："))
            rating = float(input("评分："))
            doc = {"isbn": isbn, "title": title, "author": author,
                   "publisher": publisher, "category": category,
                   "price": price, "stock": stock, "rating": rating,
                   "tags": [], "borrow_count": 0}
            book_manager.add_book(doc)
        elif choice == "2":
            book_manager.find_by_isbn(input("ISBN：").strip())
        elif choice == "3":
            print("示例：{'category': '计算机', 'price': {'$gt': 80}}")
            cond = input("请输入条件字典：")
            try:
                cond = eval(cond)
            except Exception:
                print("条件格式错误")
                continue
            book_manager.find_by_condition(cond)
        elif choice == "4":
            book_manager.rating_rank(5)
        elif choice == "5":
            isbn = input("ISBN：").strip()
            delta = int(input("库存增减量（减少用负数）："))
            book_manager.update_stock(isbn, delta)
        elif choice == "6":
            isbn = input("ISBN：").strip()
            book_manager.delete_book(isbn)
        elif choice == "7":
            print("—— 读者列表 ——")
            reader_manager.list_readers()
            print("—— 学院统计 ——")
            reader_manager.college_stats()
        elif choice == "8":
            reader_manager.level_distribution()
        elif choice == "9":
            act = input("借阅(b)/归还(r)？").strip().lower()
            card = input("读者证号：").strip()
            isbn = input("图书ISBN：").strip()
            if act == "b":
                borrow_manager.borrow_book(card, isbn)
            else:
                borrow_manager.return_book(card, isbn)
        elif choice == "10":
            borrow_manager.find_overdue()
        elif choice == "11":
            stat_manager.category_stats()
        elif choice == "12":
            stat_manager.borrow_trend()
        elif choice == "13":
            stat_manager.bestseller(5)
        else:
            print("无效编号，请重新输入")


if __name__ == "__main__":
    main()
