// ========== 任务四 · 用户与权限 S1-S3（创建账号） ==========
db = db.getSiblingDB("admin")
// S1 只读账号 libReader（角色 read，针对 library 库）
db.createUser({ user: "libReader", pwd: "libreader123", roles: [{ role: "read", db: "library" }] })
// S2 读写账号 libWriter（角色 readWrite + dbAdmin，针对 library 库）
db.createUser({ user: "libWriter", pwd: "libwriter123", roles: [{ role: "readWrite", db: "library" }, { role: "dbAdmin", db: "library" }] })
print("libReader roles = " + JSON.stringify(db.getUser("libReader").roles))
print("libWriter roles = " + JSON.stringify(db.getUser("libWriter").roles))
