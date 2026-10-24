// 探查 library 库当前状态：各集合条数、borrow_logs 的 TTL、年份分布
db = db.getSiblingDB("library")
print("===== 集合文档数量 =====")
print("books=" + db.books.countDocuments({}))
print("readers=" + db.readers.countDocuments({}))
print("borrow_logs=" + db.borrow_logs.countDocuments({}))
print("category_stats=" + db.category_stats.countDocuments({}))

print("===== borrow_logs 选项(TTL) =====")
const info = db.getCollectionInfos({ name: "borrow_logs" })
print(JSON.stringify(info[0].options, null, 2))

print("===== 借阅年份分布 =====")
const dates = db.borrow_logs.aggregate([
  { $group: { _id: { $dateToString: { format: "%Y", date: "$borrow_date" } }, n: { $sum: 1 } } },
  { $sort: { _id: 1 } }
]).toArray()
dates.forEach(function (d) { print(d._id + "年 = " + d.n + "条") })
