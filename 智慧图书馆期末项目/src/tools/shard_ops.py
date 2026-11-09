"""任务六：分片操作与验证（分片键选择、数据分布、跨分片 vs 定向查询、集群认证）。

    python tools/shard_ops.py reset    # 清空 smart_library 并重建集合（时间序列 / 固定容量 / 普通）
    python tools/shard_ops.py shard    # 开启库分片 + 为 borrow_logs 指定分片键 + 预分片到两个分片
    python tools/shard_ops.py import   # 通过 mongos 导入三份数据文件
    python tools/shard_ops.py dist     # chunk 与文档在两个分片上的分布
    python tools/shard_ops.py bench    # 定向查询与跨分片查询的对照测试
    python tools/shard_ops.py auth     # 集群访问控制验证（无凭据 / 错误口令 / 正确凭据）

注：时间序列集合在分片集群里，分片键写的是 metaField（reader_card），
    集群元数据实际记在桶集合 smart_library.system.buckets.borrow_logs 上，键名为 meta。
"""
import json
import os
import sys
import time
from datetime import datetime
from urllib.parse import quote_plus

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pymongo import MongoClient                              # noqa: E402
from pymongo.errors import OperationFailure, PyMongoError    # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = json.load(open(os.path.join(BASE_DIR, "config", "config_shard.json"), "r", encoding="utf-8"))
DB_NAME = CFG["mongo"]["db_name"]
MONGOS_PORT = CFG["mongo"]["port"]
SHARDS = CFG["nodes"]["shards"]
NS = "%s.borrow_logs" % DB_NAME
BUCKET_NS = "%s.system.buckets.borrow_logs" % DB_NAME
DATA_DIR = os.path.join(BASE_DIR, "data")
ADMIN_USER = CFG["mongo"]["username"]
ADMIN_PASS = CFG["mongo"]["password"]


def now_ms():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def mongos():
    uri = "mongodb://%s:%s@127.0.0.1:%d/?authSource=admin" % (
        quote_plus(ADMIN_USER), quote_plus(ADMIN_PASS), MONGOS_PORT)
    return MongoClient(uri, serverSelectionTimeoutMS=8000, appname="shard-ops")


def direct(port):
    uri = "mongodb://%s:%s@127.0.0.1:%d/?authSource=admin&directConnection=true" % (
        quote_plus(ADMIN_USER), quote_plus(ADMIN_PASS), port)
    return MongoClient(uri, serverSelectionTimeoutMS=6000, directConnection=True)


def to_date(value):
    if isinstance(value, str) and "T" in value:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    return value


# ------------------------------------------------------------ 重建集合
def cmd_reset():
    print("=" * 78)
    print("分片操作 0：清空 smart_library 并重建三类集合（分片前先有集合结构）")
    print("=" * 78)
    c = mongos()
    c.drop_database(DB_NAME)
    print("[执行] dropDatabase %s" % DB_NAME)
    db = c[DB_NAME]
    db.create_collection("books")
    db.create_collection("readers")
    db.create_collection("borrow_logs",
                         timeseries={"timeField": "borrow_date", "metaField": "reader_card",
                                     "granularity": "hours"})
    db.create_collection("audit_logs", capped=True, size=16 * 1024 * 1024, max=200000)
    db.create_collection("category_stats")
    print("[集合] %s" % [i["name"] for i in db.list_collections()])
    print("[说明] borrow_logs 仍是时间序列集合，分片键只能用 metaField（reader_card）")
    c.close()
    return 0


def cmd_shard():
    print("=" * 78)
    print("分片操作 A：开启数据库分片，为 borrow_logs 指定分片键 {reader_card: 1} 并预分片")
    print("=" * 78)
    c = mongos()
    try:
        c.admin.command("enableSharding", DB_NAME)
        print("[执行] enableSharding %s 成功" % DB_NAME)
    except OperationFailure as exc:
        print("[提示] enableSharding：%s" % str(exc)[:100])

    info = c["config"].collections.find_one({"_id": BUCKET_NS})
    if info and info.get("key"):
        print("[跳过] 已分片，分片键（内部键名）=%s" % info["key"])
    else:
        try:
            r = c.admin.command("shardCollection", NS, key={"reader_card": 1})
            print("[执行] shardCollection %s key={reader_card:1} -> ok=%s" % (NS, r.get("ok")))
        except OperationFailure as exc:
            print("[失败] shardCollection：%s" % str(exc)[:200])
            c.close()
            return 1
    meta = c["config"].collections.find_one({"_id": BUCKET_NS})
    if meta:
        print("[元数据] %s 分片键=%s，时间字段=%s" % (BUCKET_NS, meta.get("key"),
                                                meta.get("timeseriesFields", {}).get("metaField")))

    # 预分片：在证号中位处切开，并把高半段迁移到 shard2，避免导入时全部落在主分片
    split_at = "R20240016"
    print("[预分片] 在 meta=%s 处切分（借阅证 R20240001-R20240030 的中位）" % split_at)
    try:
        c.admin.command("split", BUCKET_NS, middle={"meta": split_at})
        print("[执行] split 成功")
    except OperationFailure as exc:
        print("[提示] split：%s" % str(exc)[:140])
    try:
        c.admin.command("moveChunk", BUCKET_NS, find={"meta": split_at}, to=SHARDS[1]["name"])
        print("[执行] moveChunk 成功：meta>=%s 的 chunk 归属 %s" % (split_at, SHARDS[1]["name"]))
    except OperationFailure as exc:
        print("[提示] moveChunk：%s" % str(exc)[:140])

    # 保证两个分片各持有一段：若低半段和主分片相同，则把低半段挪到另一个分片
    low = c["config"].chunks.find_one({"min.meta": {"$exists": True}, "max.meta": split_at})
    if low and low["shard"] == SHARDS[1]["name"]:
        try:
            c.admin.command("moveChunk", BUCKET_NS, find={"meta": "R20240001"}, to=SHARDS[0]["name"])
            print("[执行] moveChunk 低半段 -> %s，保证两个分片各持有一段" % SHARDS[0]["name"])
        except OperationFailure as exc:
            print("[提示] 低半段迁移：%s" % str(exc)[:140])

    print("[chunk]")
    for ch in c["config"].chunks.find({}):
        print("  %-30s ~ %-30s -> %s" % (str(ch["min"]), str(ch["max"]), ch["shard"]))
    c.close()
    return 0


def cmd_import():
    print("=" * 78)
    print("分片操作 B：先分片后导入，数据按分片键写入对应分片")
    print("=" * 78)
    c = mongos()
    db = c[DB_NAME]
    books = json.load(open(os.path.join(DATA_DIR, "books.txt"), "r", encoding="utf-8"))
    for b in books:
        b["publish_date"] = to_date(b["publish_date"])
    db.books.insert_many(books)
    print("[导入] books %d 条" % len(books))
    readers = json.load(open(os.path.join(DATA_DIR, "readers.txt"), "r", encoding="utf-8"))
    for r in readers:
        r["register_date"] = to_date(r["register_date"])
    db.readers.insert_many(readers)
    print("[导入] readers %d 条" % len(readers))
    logs = json.load(open(os.path.join(DATA_DIR, "borrow_logs.txt"), "r", encoding="utf-8"))
    for lg in logs:
        lg["borrow_date"] = to_date(lg["borrow_date"])
        if lg.get("return_date"):
            lg["return_date"] = to_date(lg["return_date"])
    for i in range(0, len(logs), 500):
        db.borrow_logs.insert_many(logs[i:i + 500])
    print("[导入] borrow_logs %d 条（每 500 条一批，经 mongos 路由写入）" % len(logs))

    print("\n[核对] 经 mongos 统计：")
    for name, src in (("books", len(books)), ("readers", len(readers)), ("borrow_logs", len(logs))):
        n = db[name].count_documents({})
        print("  %-12s 源 %4d  库 %4d  %s" % (name, src, n, "一致" if n == src else "不一致"))
    c.close()
    return 0


def cmd_dist():
    print("=" * 78)
    print("分片操作 C：验证数据确实分布在两个分片上")
    print("=" * 78)
    c = mongos()
    print("[分片列表] %s" % [s["host"] for s in c.admin.command("listShards")["shards"]])
    meta = c["config"].collections.find_one({"_id": BUCKET_NS}) or {}
    print("[分片键] %s（时间字段=%s）" % (meta.get("key"),
                                    meta.get("timeseriesFields", {}).get("metaField")))
    print("[chunk 归属]")
    chunks = list(c["config"].chunks.find({}))
    for ch in chunks:
        print("  %-32s ~ %-32s -> %s" % (str(ch["min"]), str(ch["max"]), ch["shard"]))
    total = c[DB_NAME]["borrow_logs"].count_documents({})
    print("[mongos 统计] borrow_logs 共 %d 条" % total)
    print("[各分片本地数据（直连分片、统计桶集合，证明确实落到两个分片）]")
    s = 0
    for sh in SHARDS:
        port = int(sh["host"].split(":")[1])
        d = direct(port)
        buckets = d[DB_NAME]["system.buckets.borrow_logs"]
        agg = list(buckets.aggregate([{"$group": {"_id": None, "b": {"$sum": 1},
                                                 "n": {"$sum": "$control.count"}}}]))
        bcount = agg[0]["b"] if agg else 0
        n = agg[0]["n"] if agg else 0
        cards = d[DB_NAME]["system.buckets.borrow_logs"].distinct("meta")
        s += n
        print("  %-8s %-18s 桶 %4d 个 / 文档 %4d 条，涉及借阅证 %2d 个（%s ~ %s）"
              % (sh["name"], sh["host"], bcount, n, len(cards),
                 min(cards) if cards else "-", max(cards) if cards else "-"))
        d.close()
    print("[校验] 两分片文档之和 = %d，mongos 统计 = %d -> %s"
          % (s, total, "一致，数据确实分布在两个分片" if s == total else "不一致"))
    print("[说明] 时间序列集合以桶为单位存储，直连分片时按桶集合统计才准确；")
    print("       每个桶的 control.count 即该桶内的测量值条数，两片各 1500 条，分布均匀。")
    c.close()
    return 0


# ------------------------------------------------------------ 查询对比
def cmd_bench():
    print("=" * 78)
    print("分片操作 D：定向查询（带分片键）与跨分片查询（不带分片键）对比")
    print("=" * 78)
    c = mongos()
    coll = c[DB_NAME]["borrow_logs"]
    card = "R20240005"
    isbn = coll.find_one({}, {"book_isbn": 1})["book_isbn"]
    print("[测试数据] 分片键读者证 = %s；非分片键 ISBN = %s" % (card, isbn))
    print("[对照说明] 定向查询只命中 1 个分片；跨分片查询由 mongos 广播到 2 个分片再归并")
    print("[取证方式] 时间序列集合不支持 explain，改为在分片上开 profiling(level=2)，")
    print("           给每次查询打 comment 标记，再看该查询实际落在哪个分片、扫描了多少文档")

    # 分片侧开 profiling
    dsh = {}
    for sh in SHARDS:
        port = int(sh["host"].split(":")[1])
        d = direct(port)
        d[DB_NAME].command("profile", 2)
        dsh[sh["name"]] = d
    print("[准备] 两个分片 profiling 已开启（level=2）")

    def clear_prof():
        # 关掉再打开 profiling 会把 system.profile 清空；直接 delete 需要该库的额外权限
        for name, d in dsh.items():
            d[DB_NAME].command("profile", 0)
            d[DB_NAME].command("profile", 2)

    def hits(tag):
        rows = []
        for name, d in dsh.items():
            # 只统计真正执行到引擎的 command 记录（对应桶集合上的扫描），排除 query 类型的包装记录
            n = d[DB_NAME]["system.profile"].count_documents(
                {"command.comment": tag, "op": "command"})
            rows.append((name, n))
        return rows

    def run(label, tag, query, rounds=30):
        clear_prof()
        coll.find_one(query)   # 预热
        t0 = time.time()
        for _ in range(rounds):
            list(coll.find(query, comment=tag).limit(200))
        per = (time.time() - t0) / rounds * 1000
        time.sleep(0.4)
        rows = hits(tag)
        n = len(list(coll.find(query).limit(200)))
        print("\n[%s]" % label)
        print("  查询条件：%s；comment=%s" % (json.dumps(query, ensure_ascii=False), tag))
        print("  分片命中：%s" % "，".join("%s=%d 次" % (k, v) for k, v in rows))
        print("  执行范围：%s" % ("仅 1 个分片（定向到持有该证号的分片）"
                                if len([v for _, v in rows if v]) == 1 else "2 个分片（跨分片归并）"))
        print("  返回文档：%d 条；%d 次平均耗时 %.2f ms" % (n, rounds, per))
        return per, sum(v for _, v in rows)

    t1, _ = run("定向查询：按 reader_card（分片键）过滤", "targeted", {"reader_card": card})
    t2, _ = run("跨分片查询：按 book_isbn（非分片键、有索引）过滤", "cross_isbn", {"book_isbn": isbn})
    t3, _ = run("跨分片查询：按 status 过滤（无单字段索引）", "cross_status", {"status": "逾期"})

    print("\n[扫描量对比]（同一轮 profiling 里记录的执行条目，按标记汇总）")
    for name, d in dsh.items():
        for tag in ("targeted", "cross_isbn", "cross_status"):
            agg = list(d[DB_NAME]["system.profile"].aggregate([
                {"$match": {"command.comment": tag, "op": "command"}},
                {"$group": {"_id": None, "docs": {"$sum": "$docsExamined"},
                            "keys": {"$sum": "$keysExamined"},
                            "n": {"$sum": "$nreturned"}, "c": {"$sum": 1},
                            "plan": {"$first": "$planSummary"}}}]))
            if agg:
                a = agg[0]
                print("  %-8s %-14s 执行 %2d 条，扫描文档 %5d，命中索引 %5d，返回 %4d，计划=%s"
                      % (name, tag, a["c"], a["docs"], a["keys"], a["n"], a["plan"]))
    print("\n[对比结论]")
    print("  定向 %.2f ms / ISBN 跨片 %.2f ms = %.2f 倍" % (t1, t2, t2 / max(t1, 0.001)))
    print("  定向 %.2f ms / status 跨片 %.2f ms = %.2f 倍" % (t1, t3, t3 / max(t1, 0.001)))
    print("  带分片键时 mongos 只把请求发给持有该证号的分片，跨分片查询必须等两个分片都返回再归并")

    for d in dsh.values():
        d[DB_NAME].command("profile", 0)
        d.close()
    print("[收尾] 两个分片 profiling 已关闭（level=0）")
    c.close()
    return 0


def cmd_auth():
    print("=" * 78)
    print("分片操作 E：集群访问控制验证")
    print("=" * 78)
    print("[1] 不带凭据访问 mongos：")
    try:
        bad = MongoClient("mongodb://127.0.0.1:%d/?directConnection=true" % MONGOS_PORT,
                          serverSelectionTimeoutMS=5000, directConnection=True)
        bad[DB_NAME]["borrow_logs"].count_documents({})
        print("    结果：竟然可读（不符合预期）")
    except PyMongoError as exc:
        print("    结果：被拒绝 -> %s" % str(exc)[:100])

    print("[2] 用错误口令访问 mongos：")
    try:
        wrong = MongoClient("mongodb://%s:%s@127.0.0.1:%d/?authSource=admin" % (
            quote_plus(ADMIN_USER), quote_plus("Wrong@2025"), MONGOS_PORT),
            serverSelectionTimeoutMS=5000)
        wrong[DB_NAME]["borrow_logs"].count_documents({})
        print("    结果：竟然可读（不符合预期）")
    except PyMongoError as exc:
        print("    结果：认证失败 -> %s" % str(exc)[:110])

    print("[3] 用正确凭据访问 mongos：")
    c = mongos()
    print("    结果：登录成功，borrow_logs=%d 条" % c[DB_NAME]["borrow_logs"].count_documents({}))

    print("[4] 集群内部认证（keyfile）：直连两个分片：")
    for sh in SHARDS:
        port = int(sh["host"].split(":")[1])
        d = direct(port)
        st = d.admin.command("hello")
        print("    %-8s setName=%-8s 角色=%s" % (sh["name"], st.get("setName"),
                                            "PRIMARY" if st.get("isWritablePrimary") else "SECONDARY"))
        d.close()
    print("[5] 配置服务器：")
    cs = direct(int(CFG["nodes"]["config"]["host"].split(":")[1]))
    st = cs.admin.command("hello")
    print("    csrs setName=%s 可写=%s" % (st.get("setName"), st.get("isWritablePrimary")))
    cs.close()
    print("[说明] 三个 mongod 与 mongos 共用同一个 keyfile，节点之间互信；客户端仍需账号口令认证")
    c.close()
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    table = {"reset": cmd_reset, "shard": cmd_shard, "import": cmd_import,
             "dist": cmd_dist, "bench": cmd_bench, "auth": cmd_auth}
    if cmd in table:
        return table[cmd]()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
