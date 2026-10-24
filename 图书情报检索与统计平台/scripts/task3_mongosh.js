// ========== 任务三 · 检索功能实现 ==========
db = db.getSiblingDB("library")

function cnt(name, filter) { print(name + " 结果条数=" + db[name].countDocuments(filter)) }

print("========== 基础检索 Q1-Q6 ==========")
cnt("books", { price: { $gt: 80 } })            // Q1 $gt 定价80元以上
cnt("books", { stock: { $lt: 10 } })            // Q2 $lt 库存不足10
cnt("books", { isbn: { $eq: "9787121362726" } }) // Q3 $eq ISBN精确
cnt("readers", { email: { $eq: null } })        // Q4 email为null
cnt("books", { publisher: { $ne: "人民邮电出版社" } }) // Q5 排除某出版社
cnt("books", { category: { $in: ["计算机", "经济管理"] } }) // Q6 $in 多类别

print("========== 组合与高级检索 Q7-Q12 ==========")
cnt("books", { $and: [{ rating: { $gt: 4.0 } }, { category: "计算机" }] }) // Q7 $and
cnt("books", { $or: [{ rating: { $lt: 3.5 } }, { stock: 0 }] })           // Q8 $or
cnt("books", { title: { $regex: "Python" } })                             // Q9 $regex
cnt("books", { tags: { $all: ["编程", "入门"] } })                         // Q10 $all
cnt("books", { tags: { $size: 3 } })                                       // Q11 $size
cnt("books", { tags: { $exists: true } })                                  // Q12 $exists

print("========== 结果处理 Q13-Q16 ==========")
cnt("books", { _id: { $type: "string" } })      // Q13 $type _id为string
print("Q14 评分降序前5：")
db.books.find().sort({ rating: -1 }).limit(5).forEach(d => print("  " + d.title + " | 评分" + d.rating))
print("Q15 投影(书名/价格/评分,不含_id)：")
db.books.find({}, { title: 1, price: 1, rating: 1, _id: 0 }).limit(3).forEach(d => print("  " + JSON.stringify(d)))
print("Q16 类别清单：")
print("  " + JSON.stringify(db.books.distinct("category")))

print("========== 更新操作 U1-U4 ==========")
// U1 updateOne + $inc：Python编程库存减5
var u1 = db.books.updateOne({ isbn: "9787115428028" }, { $inc: { stock: -5 } })
print("U1 $inc 受影响行数=" + u1.modifiedCount + "，该书写库存=" + db.books.findOne({ isbn: "9787115428028" }).stock)
// U2 updateMany + $mul：计算机类价格打9折
var u2 = db.books.updateMany({ category: "计算机" }, { $mul: { price: 0.9 } })
print("U2 $mul 受影响行数=" + u2.modifiedCount)
// U3 $currentDate：为某本书新增 updated_at 字段并记录当前时间
var u3 = db.books.updateOne({ isbn: "9787115546081" }, { $currentDate: { updated_at: true } })
print("U3 $currentDate 受影响行数=" + u3.modifiedCount)
// U4 $unset：删除某本书的 tags 字段
var u4 = db.books.updateOne({ isbn: "9787544253994" }, { $unset: { tags: "" } })
print("U4 $unset 受影响行数=" + u4.modifiedCount + "，该书仍有tags=" + db.books.findOne({ isbn: "9787544253994" }).hasOwnProperty("tags"))

print("========== 删除操作 D1-D3 ==========")
// D1 deleteOne 删除一条已归还的借阅记录
var d1 = db.borrow_logs.deleteOne({ status: "已归还" })
print("D1 deleteOne 受影响行数=" + d1.deletedCount)
// D2 预览逾期记录，然后 deleteMany 清理
print("D2 预览：逾期记录条数=" + db.borrow_logs.countDocuments({ status: "逾期" }))
var d2 = db.borrow_logs.deleteMany({ status: "逾期" })
print("D2 deleteMany 受影响行数=" + d2.deletedCount)
// D3 replaceOne 整体替换读者 R20240001（保留 _id）
var d3 = db.readers.replaceOne({ card_no: "R20240001" }, {
  card_no: "R20240001", name: "张明", college: "计算机学院",
  email: "zhangming_new@example.edu", phone: "13800138000",
  level: "高级", fav_categories: ["计算机", "数学"]
})
print("D3 replaceOne 受影响行数=" + d3.modifiedCount)
