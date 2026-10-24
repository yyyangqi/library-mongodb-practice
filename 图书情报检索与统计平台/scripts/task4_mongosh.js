// ========== 任务四 · 聚合管道与索引 ==========
db = db.getSiblingDB("library")

print("========== 聚合管道统计 A1-A9 ==========")
print("-- A1 按类别统计图书数量与平均评分 --")
db.books.aggregate([
  { $group: { _id: "$category", book_count: { $sum: 1 }, avg_rating: { $avg: "$rating" } } }
]).forEach(d => print("  " + d._id + " | 数量" + d.book_count + " | 平均评分" + d.avg_rating.toFixed(2)))

print("-- A2 各出版社图书数量，取前5 --")
db.books.aggregate([
  { $group: { _id: "$publisher", count: { $sum: 1 } } },
  { $sort: { count: -1 } },
  { $limit: 5 }
]).forEach(d => print("  " + d._id + " | " + d.count + "本"))

print("-- A3 文档数最多的图书类别 sortByCount --")
var a3 = db.books.aggregate([{ $sortByCount: "$category" }]).toArray()
print("  " + a3[0]._id + " | " + a3[0].count)

print("-- A4 评分最高的3本图书 --")
db.books.aggregate([
  { $sort: { rating: -1 } },
  { $limit: 3 },
  { $project: { title: 1, borrow_count: 1, _id: 0 } }
]).forEach(d => print("  " + d.title + " | 借阅" + d.borrow_count))

print("-- A5 每本书销售额(price*borrow_count)四舍五入两位 --")
db.books.aggregate([
  { $project: { title: 1, sales: { $round: [{ $multiply: ["$price", "$borrow_count"] }, 2] }, _id: 0 } }
]).forEach(d => print("  " + d.title + " | 销售额" + d.sales))

print("-- A6 按借阅年份分组统计 --")
db.borrow_logs.aggregate([
  { $group: { _id: { $year: "$borrow_date" }, count: { $sum: 1 } } },
  { $sort: { _id: 1 } },
  { $project: { year: { $dateToString: { format: "%Y年", date: { $dateFromParts: { year: "$_id" } } } }, count: 1, _id: 0 } }
]).forEach(d => print("  " + d.year + " 借阅 " + d.count + " 次"))

print("-- A7 读者借阅次数前5 --")
db.borrow_logs.aggregate([
  { $group: { _id: "$reader_card", count: { $sum: 1 } } },
  { $sort: { count: -1 } },
  { $limit: 5 }
]).forEach(d => print("  " + d._id + " 借阅" + d.count + "次"))

print("-- A8 关联读者与借阅流水，学院借阅量排行 --")
db.borrow_logs.aggregate([
  { $lookup: { from: "readers", localField: "reader_card", foreignField: "card_no", as: "reader" } },
  { $unwind: "$reader" },
  { $group: { _id: "$reader.college", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
]).forEach(d => print("  " + d._id + " | " + d.count + "次"))

print("-- A9 将A1分类统计写入 category_stats 集合 --")
db.books.aggregate([
  { $group: { _id: "$category", book_count: { $sum: 1 }, avg_rating: { $avg: "$rating" } } },
  { $merge: { into: "category_stats", on: "_id", whenMatched: "replace", whenNotMatched: "insert" } }
])
print("  category_stats 文档数=" + db.category_stats.countDocuments({}))
db.category_stats.find().forEach(d => print("  " + d._id + " | 数量" + d.book_count + " | 均分" + d.avg_rating.toFixed(2)))

print("========== 索引建立 I1-I5 ==========")
print("-- I1 isbn 唯一索引 --")
db.books.createIndex({ isbn: 1 }, { unique: true })
print("-- I2 title 单键索引 --")
db.books.createIndex({ title: 1 })
print("-- I3 category 单键索引 --")
db.books.createIndex({ category: 1 })
print("-- I4 tags 多键索引 --")
db.books.createIndex({ tags: 1 })
print("-- I5 category+price 复合索引 --")
db.books.createIndex({ category: 1, price: 1 })

print("===== getIndexes() 索引清单 =====")
db.books.getIndexes().forEach(i => print("  " + i.name + " | " + JSON.stringify(i.key)))

print("===== 验证唯一索引：重复ISBN无法插入 =====")
try {
  db.books.insertOne({ isbn: "9787115428028", title: "重复测试" })
  print("  未报错(异常)")
} catch (e) {
  print("  已拦截重复ISBN：" + e.message)
}

print("===== explain 对比有无索引查询耗时 =====")
print("-- 无索引：按 author 查询（author 无索引，需全表扫描） --")
var noIdx = db.books.find({ author: "余华" }).explain("executionStats")
print("  无索引(author) 执行时间=" + noIdx.executionStats.executionTimeMillis + "ms，检查文档=" + noIdx.executionStats.totalDocsExamined)
print("-- 有索引：按 isbn 查询（命中 isbn_1 唯一索引） --")
var withIdx = db.books.find({ isbn: "9787115428028" }).explain("executionStats")
print("  有索引(isbn) 执行时间=" + withIdx.executionStats.executionTimeMillis + "ms，检查文档=" + withIdx.executionStats.totalDocsExamined)
