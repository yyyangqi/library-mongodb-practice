db = db.getSiblingDB("library")
print("total borrow_logs = " + db.borrow_logs.countDocuments({}))
print("--- 按年份分组 ---")
db.borrow_logs.aggregate([
  { $group: { _id: { $year: "$borrow_date" }, c: { $sum: 1 } } },
  { $sort: { _id: 1 } }
]).forEach(d => print(d._id + " -> " + d.c))
print("--- 样例 borrow_date ---")
db.borrow_logs.find({}, { borrow_date: 1, _id: 0 }).limit(5).forEach(d => print(JSON.stringify(d.borrow_date)))
