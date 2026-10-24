// ========== 任务六 · 数据导出（ST-6.3） ==========
db = db.getSiblingDB("library")
const fs = require('fs')
const D = "C:/Users/26295/Doubao/chats/2026-10-21/new-chat/图书情报检索与统计平台/data/"
fs.writeFileSync(D + "books_export.json", EJSON.stringify(db.books.find().toArray(), null, 2))
fs.writeFileSync(D + "category_stats_export.json", EJSON.stringify(db.category_stats.find().toArray(), null, 2))
print("已导出 books = " + db.books.countDocuments({}) + " 条 -> books_export.json")
print("已导出 category_stats = " + db.category_stats.countDocuments({}) + " 条 -> category_stats_export.json")
