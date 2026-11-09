"""任务五：副本集部署、状态核对与读取偏好验证。

用法：
    python tools/rs_admin.py init       # 初始化三节点副本集
    python tools/rs_admin.py status     # 打印副本集状态（节点角色、同步延迟）
    python tools/rs_admin.py readpref   # 对比 primary / secondaryPreferred / secondary 三种读取偏好

说明：脚本读取 config/config_rs.json（节点端口、副本集名、管理员账号），
因此换机器只需改配置，不需改代码。
"""
import json
import os
import sys
import time
from datetime import datetime
from urllib.parse import quote_plus

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pymongo import MongoClient, ReadPreference            # noqa: E402
from pymongo.errors import OperationFailure, PyMongoError  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG_PATH = os.path.join(BASE_DIR, "config", "config_rs.json")


def load_cfg():
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


CFG = load_cfg()
SET_NAME = CFG["replset"]
HOSTS = CFG["hosts"]
ADMIN = CFG["admin"]
DB_NAME = CFG["mongo"]["db_name"]


def hosts_str():
    return ",".join(HOSTS)


def admin_client(read_preference=None, direct_host=None):
    """管理员连接：默认连整个副本集，指定 direct_host 时单点直连（用于故障排查）。"""
    if direct_host:
        uri = "mongodb://%s:%s@%s/%s?authSource=%s&directConnection=true" % (
            quote_plus(ADMIN["user"]), quote_plus(ADMIN["password"]), direct_host,
            ADMIN["auth_source"], ADMIN["auth_source"])
        return MongoClient(uri, serverSelectionTimeoutMS=5000)
    uri = "mongodb://%s:%s@%s/%s?authSource=%s&replicaSet=%s" % (
        quote_plus(ADMIN["user"]), quote_plus(ADMIN["password"]), hosts_str(),
        ADMIN["auth_source"], ADMIN["auth_source"], SET_NAME)
    kwargs = {"serverSelectionTimeoutMS": 10000, "appname": "rs-admin"}
    if read_preference:
        kwargs["read_preference"] = read_preference
    return MongoClient(uri, **kwargs)


def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def wait_primary(timeout=60):
    """等待出现主节点，返回 (client, primary_host)。"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            c = admin_client()
            st = c.admin.command("replSetGetStatus")
            for m in st["members"]:
                if m["stateStr"] == "PRIMARY":
                    return c, m["name"]
        except PyMongoError as exc:
            last = exc
        time.sleep(1)
    raise RuntimeError("等待主节点超时：%s" % last)


# ---------------------------------------------------------------- init
def cmd_init():
    print("=" * 78)
    print("副本集初始化：%s  节点 %s" % (SET_NAME, hosts_str()))
    print("=" * 78)
    cfg_doc = {"_id": SET_NAME, "members": []}
    for n in CFG["nodes"][:3]:
        cfg_doc["members"].append({"_id": len(cfg_doc["members"]),
                                   "host": "127.0.0.1:%d" % n["port"],
                                   "priority": n.get("priority", 1)})
    print("[配置] %s" % json.dumps(cfg_doc["members"], ensure_ascii=False))
    c = MongoClient("mongodb://127.0.0.1:%d/" % CFG["nodes"][0]["port"],
                    directConnection=True, serverSelectionTimeoutMS=5000)
    try:
        c.admin.command("replSetInitiate", cfg_doc)
        print("[执行] replSetInitiate 成功，等待选举完成 ...")
    except OperationFailure as exc:
        print("[执行] replSetInitiate 返回：%s" % str(exc)[:120])
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            st = c.admin.command("replSetGetStatus")
            states = sorted(m["stateStr"] for m in st["members"])
            print("  [%s] 成员状态：%s" % (ts(), "、".join(states)))
            if "PRIMARY" in states and states.count("SECONDARY") == 2:
                print("[结果] 初始化完成：1 主 2 从")
                return 0
        except PyMongoError as exc:
            print("  [%s] 状态读取中：%s" % (ts(), str(exc)[:70]))
        time.sleep(3)
    print("[结果] 初始化未在 90 秒内达成 1 主 2 从")
    return 1


# ---------------------------------------------------------------- status
def cmd_status():
    c, primary = wait_primary(timeout=30)
    st = c.admin.command("replSetGetStatus")
    now = st["date"]
    print("=" * 78)
    print("副本集状态   集群=%s   主节点=%s   采集时间=%s"
          % (st["set"], primary, now.strftime("%Y-%m-%d %H:%M:%S")))
    print("=" * 78)
    print("  %-22s %-12s %-6s %-6s %-22s %s" % ("节点", "角色", "health", "state", "最后一次oplog时间", "同步源"))
    for m in st["members"]:
        opt = m.get("optimeDate")
        opt_s = opt.strftime("%Y-%m-%d %H:%M:%S") if opt else "-"
        print("  %-22s %-12s %-6s %-6s %-22s %s"
              % (m["name"], m["stateStr"], m["health"], m["state"],
                 opt_s, m.get("syncSourceHost") or "-"))
    for m in st["members"]:
        if m["stateStr"] == "PRIMARY":
            others = [x.get("optimeDate") for x in st["members"] if x["stateStr"] == "SECONDARY"]
            if others and m.get("optimeDate"):
                lag = max((m["optimeDate"] - o).total_seconds() for o in others if o)
                print("\n[复制延迟] 从节点相对主节点最大延迟 %.2f 秒（oplog 时间差）" % lag)
    print("\n[oplog] 主节点 oplog 窗口：")
    try:
        c.local["oplog.rs"].find_one({}, {"ts": 1})
        first = c.local["oplog.rs"].find().sort("$natural", 1).limit(1)[0]
        last = c.local["oplog.rs"].find().sort("$natural", -1).limit(1)[0]
        t_first = datetime.fromtimestamp(first["ts"].time)
        t_last = datetime.fromtimestamp(last["ts"].time)
        print("  最早 %s  最近 %s  跨度 %.1f 分钟"
              % (t_first.strftime("%Y-%m-%d %H:%M:%S"),
                 t_last.strftime("%Y-%m-%d %H:%M:%S"),
                 (t_last - t_first).total_seconds() / 60.0))
    except PyMongoError as exc:
        print("  读取失败：%s" % str(exc)[:80])
    c.close()
    return 0


# ---------------------------------------------------------------- readpref
def _ports():
    return [n["port"] for n in CFG["nodes"][:3]]


def _set_profiling(level):
    """对三个节点直接连接，统一设置 profiling 级别（2=记录全部操作）。"""
    for p in _ports():
        c = admin_client(direct_host="127.0.0.1:%d" % p)
        try:
            c[DB_NAME].command("profile", level)
            if level == 0:
                pass
            else:
                try:
                    c[DB_NAME]["system.profile"].delete_many({})
                except PyMongoError:
                    pass
        finally:
            c.close()


def _profile_hits(comment):
    """统计各节点 system.profile 中带指定 comment 的记录数，用于判定查询落在哪个节点。"""
    hits = {}
    for p in _ports():
        c = admin_client(direct_host="127.0.0.1:%d" % p)
        try:
            hits[p] = c[DB_NAME]["system.profile"].count_documents({"command.comment": comment})
        except PyMongoError:
            hits[p] = -1
        finally:
            c.close()
    return hits


def cmd_readpref():
    print("=" * 78)
    print("读取偏好验证：同一查询在不同读取偏好下由哪个节点提供服务")
    print("（判定方式：临时开启 system.profile 级别的慢查询剖析，按查询 comment 归因到具体节点）")
    print("=" * 78)

    # 主节点写入一条带时间戳的探针文档，供从节点读取验证复制
    cw, primary = wait_primary(timeout=30)
    probe = {"kind": "readpref-probe", "ts": datetime.now()}
    cw[DB_NAME]["read_pref_probe"].insert_one(probe)
    print("[写入] 主节点 %s 写入探针文档 1 条" % primary)

    _set_profiling(2)
    print("[准备] 三个节点 profiling=2 已开启，profile 集合已清空")

    cases = [
        ("primary", ReadPreference.PRIMARY, "强一致：统计报表、借阅/归还扣减库存等实时结果"),
        ("secondaryPreferred", ReadPreference.SECONDARY_PREFERRED, "读多写少：馆藏检索、排行榜，可容忍秒级延迟"),
        ("secondary", ReadPreference.SECONDARY, "只读副本消耗：明细导出、离线统计，可容忍延迟但不允许回落主节点"),
    ]
    for name, pref, scene in cases:
        c = admin_client(read_preference=pref)
        time.sleep(1.2)   # 给复制留出时间，避免 secondary 读到旧数据
        comment = "pref-%s-%d" % (name, int(time.time() * 1000))
        try:
            docs = list(c[DB_NAME]["books"].find({"category": "计算机"},
                                                 {"_id": 0, "title": 1}, comment=comment))
            n_books = c[DB_NAME]["books"].count_documents({})
            n_probe = c[DB_NAME]["read_pref_probe"].count_documents({"kind": "readpref-probe"})
            time.sleep(0.8)
            hits = _profile_hits(comment)
            served = [p for p, n in hits.items() if n > 0]
            print("\n[%s] 读取偏好=%s" % (name, name))
            print("  实际执行查询的节点：%s" % ("、".join("127.0.0.1:%d" % p for p in served) or "未捕获"))
            print("  各节点 profile 命中数：%s"
                  % "  ".join("%d:%s" % (p, n) for p, n in sorted(hits.items())))
            print("  本次查询返回 %d 条（计算机类）；全库 books=%d 条；探针文档可见=%d 条"
                  % (len(docs), n_books, n_probe))
            print("  适用场景：%s" % scene)
        finally:
            c.close()

    _set_profiling(0)
    print("\n[收尾] 三个节点 profiling 已关闭（0）")

    # 直连两个从节点，验证从节点数据可读（副本已落地）
    print("\n[从节点直连读取] 验证复制确实写入从节点本地：")
    for n in CFG["nodes"][1:3]:
        h = "127.0.0.1:%d" % n["port"]
        try:
            c = admin_client(direct_host=h)
            hello = c.admin.command("hello")
            cnt = c[DB_NAME]["books"].count_documents({"category": "计算机"})
            print("  %s  stateStr=%-10s  books(计算机)=%d 条"
                  % (h, "SECONDARY" if hello.get("secondary") else "PRIMARY", cnt))
            c.close()
        except PyMongoError as exc:
            print("  %s  连接失败：%s" % (h, str(exc)[:80]))

    # 清理探针
    cw[DB_NAME]["read_pref_probe"].drop()
    cw.close()
    print("\n[清理] 已删除探针集合 read_pref_probe")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "init":
        return cmd_init()
    if cmd == "status":
        return cmd_status()
    if cmd == "readpref":
        return cmd_readpref()
    print("未知子命令：%s" % cmd)
    return 1


if __name__ == "__main__":
    sys.exit(main())
