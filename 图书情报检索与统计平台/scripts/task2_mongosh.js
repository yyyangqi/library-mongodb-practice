// ========== 任务二 · 数据建模与填充 ==========
db = db.getSiblingDB("library")
db.dropDatabase() // 幂等初始化：重建 library 库

// ---- ST-2.1 创建普通业务集合 ----
db.createCollection("books")
db.createCollection("readers")
db.createCollection("category_stats")

// ---- ST-2.2 三种特殊集合 ----
// 固定集合 book_logs：1MB、最多1000条
db.createCollection("book_logs", { capped: true, size: 1048576, max: 1000 })

// 时间序列集合 borrow_logs：timeField=borrow_date, granularity=hours, 保留期5年(157680000秒)
// 说明：借阅日期为 2023—2025 年，保留期由原 2 年改为 5 年，保证实训数据集完整不被 TTL 自动清理。
db.createCollection("borrow_logs", {
  timeseries: {
    timeField: "borrow_date",
    granularity: "hours"
  },
  expireAfterSeconds: 157680000
})

// 视图 book_in_stock：基于 books，过滤 stock>0
db.createView("book_in_stock", "books", [{ $match: { stock: { $gt: 0 } } }])

// 集合列表及类型
print("===== 集合列表 =====")
db.getCollectionInfos().forEach(function (c) {
  print(c.name + " | type=" + c.type + " | options=" + JSON.stringify(c.options || {}))
})

// ---- ST-2.3 录入配套数据集 ----
const fs = require('fs')
const D = "C:/Users/26295/Doubao/chats/2026-10-21/new-chat/图书情报检索与统计平台/data/"
const books = EJSON.parse(fs.readFileSync(D + "books.txt", "utf8"))
const readers = EJSON.parse(fs.readFileSync(D + "readers.txt", "utf8"))
const borrows = EJSON.parse(fs.readFileSync(D + "borrow_logs.txt", "utf8"))

print("books条数=" + books.length + ", readers条数=" + readers.length + ", borrows条数=" + borrows.length)

// insertOne 单独录入第一条图书
const first = db.books.insertOne(books[0])
print("insertOne 结果: " + JSON.stringify(first))

// insertMany 批量录入其余图书
const rest = db.books.insertMany(books.slice(1))
print("insertMany 图书插入数=" + rest.insertedCount)

// readers 批量录入
const r = db.readers.insertMany(readers)
print("readers 插入数=" + r.insertedCount)

// borrow_logs 批量录入（时间序列集合）
const b = db.borrow_logs.insertMany(borrows)
print("borrow_logs 插入数=" + b.insertedCount)
// borrow_logs 保留期在集合创建时已设为5年(157680000秒)，无需再 collMod 调整。
print("borrow_logs TTL(秒)=" + JSON.stringify(db.getCollectionInfos({ name: "borrow_logs" })[0].options.expireAfterSeconds))
print("borrow_logs.count=" + db.borrow_logs.countDocuments({}))

// ---- 各集合文档数量核对 ----
print("===== 文档数量核对 =====")
print("books.count=" + db.books.countDocuments({}))
print("readers.count=" + db.readers.countDocuments({}))
print("borrow_logs.count=" + db.borrow_logs.countDocuments({}))
print("category_stats.count=" + db.category_stats.countDocuments({}))
print("book_in_stock.count=" + db.book_in_stock.countDocuments({}))
print("book_logs.count=" + db.book_logs.countDocuments({}))
