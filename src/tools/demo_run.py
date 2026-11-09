"""程序演示脚本：以脚本化输入驱动 main.py 的菜单功能，生成可复现的运行记录。

用于交付材料中的「程序运行截图 / 执行记录」：本脚本把真实运行结果打印到标准输出，
不修改任何业务数据以外的内容，且运行后由调用方决定是否保留演示数据。
"""
import builtins
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main as app                                       # noqa: E402
from db import LibraryDB                                 # noqa: E402


class ScriptedInput(object):
    """按预设答案依次响应 input()，用完后回落到回车（退出）。"""

    def __init__(self, answers):
        self.answers = list(answers)
        self.real = builtins.input

    def __call__(self, prompt=""):
        if self.answers:
            value = self.answers.pop(0)
            print(prompt + str(value))
            return value
        print(prompt)
        return ""


def run(app_answers, func, db, title):
    print("\n" + "#" * 78)
    print("# 执行功能：%s" % title)
    print("#" * 78)
    old = builtins.input
    builtins.input = ScriptedInput(app_answers)
    try:
        func(db)
    finally:
        builtins.input = old


def main():
    db = LibraryDB()
    print("智慧图书馆数字资源平台  v1.0   （程序演示：菜单 + 检索 + 统计 + 文件 + 日志 + 导出）")
    print("数据库=%s  读取偏好=%s  连接串主机=%s"
          % (db.db.name, db.read_preference_name, db.client.address))

    print("\n" + "=" * 78)
    print(" 智慧图书馆数字资源平台 —— 主菜单")
    print("-" * 78)
    for key, name, _ in app.MENU:
        print("  %-3s %s" % (key, name))
    print("   0  退出")

    run(["1"], app.ui_list_books, db, "1 图书列表（分页 + 排序）")
    run(["计算机", "50", "90"], app.ui_search_category_price, db, "2 按类别 + 价格区间检索")
    run(["编程,入门"], app.ui_search_tags, db, "3 按标签多选检索（$all）")
    run(["编程"], app.ui_search_title, db, "4 按书名模糊检索")
    run(["2019", "2022"], app.ui_search_year, db, "5 按出版年份范围检索")
    run([], app.ui_missing_tags, db, "6 数据质量核查（缺 tags 字段）")
    run([], app.ui_top_rated, db, "7 评分 Top10")
    run(["", "高级"], app.ui_list_readers, db, "10 读者列表 / 等级检索")
    run(["13"], app.ui_stats_category, db, "13 分类统计 + 写入 category_stats")
    run([], app.ui_stats_college, db, "14 学院借阅 Top5")
    run([], app.ui_stats_trend, db, "15 月度借阅趋势")
    run([], app.ui_stats_top_books, db, "16 借阅排行 Top10 + 馆藏位置")
    run([], app.ui_list_files, db, "19 GridFS 文件清单")
    run(["Python"], app.ui_download_ebook, db, "18 按书名下载电子书并校验字节数")
    run([], app.ui_audit, db, "20 最近 100 条操作日志")
    run([], app.ui_export, db, "21 导出统计结果 CSV")

    db.close()
    print("\n演示结束。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
