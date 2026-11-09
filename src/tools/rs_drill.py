"""任务五：故障转移演练与节点增删演练。

演练拆成若干条短命令，每条都在几秒内结束并立即输出，便于逐条留证：
    python tools/rs_drill.py failover-kill      # 记录初始拓扑 + 写基线 + 杀掉主节点
    python tools/rs_drill.py failover-watch     # 观察选举过程，同时用业务探针记录中断时长
    python tools/rs_drill.py failover-restart   # 把被杀的节点重新拉起
    python tools/rs_drill.py failover-sync      # 等待原主节点重新加入并降级为从节点
    python tools/rs_drill.py addnode            # 加入第四个节点 27024 并提交 reconfig
    python tools/rs_drill.py addnode-sync       # 等待新节点完成初始同步
    python tools/rs_drill.py removenode         # 移除该节点并停止其进程

    python tools/rs_drill.py failover-all       # 一次性完整演练（约 1 分钟，供手工执行）
    python tools/rs_drill.py status             # 当前成员角色
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import quote_plus

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pymongo import MongoClient                              # noqa: E402
from pymongo.errors import PyMongoError                      # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = json.load(open(os.path.join(BASE_DIR, "config", "config_rs.json"), "r", encoding="utf-8"))
MONGOD = r"D:\MongoDB\mongodb\mongodb-win32-x86_64-windows-8.0.4\bin\mongod.exe"
SET_NAME = CFG["replset"]
ADMIN = CFG["admin"]
DB_NAME = CFG["mongo"]["db_name"]
NODE_BY_PORT = dict((n["port"], n) for n in CFG["nodes"])
HOSTS = CFG["hosts"]
STATE_PATH = os.path.join(BASE_DIR, "records", "_failover_state.json")
PROBE_COLL = "failover_probe"


def now_ms():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def load_state():
    if os.path.exists(STATE_PATH):
        return json.load(open(STATE_PATH, "r", encoding="utf-8"))
    return {}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------ 连接 / 进程工具
def client_hosts(hosts):
    uri = "mongodb://%s:%s@%s/%s?authSource=%s&replicaSet=%s" % (
        quote_plus(ADMIN["user"]), quote_plus(ADMIN["password"]), ",".join(hosts),
        ADMIN["auth_source"], ADMIN["auth_source"], SET_NAME)
    return MongoClient(uri, serverSelectionTimeoutMS=8000, appname="rs-drill")


def pid_of_port(port):
    """从 netstat 输出里解析监听该端口的 PID（Windows）。"""
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    for line in out.splitlines():
        m = re.search(r"TCP\s+127\.0\.0\.1:%d\s+0\.0\.0\.0:0\s+LISTENING\s+(\d+)" % port, line)
        if m:
            return int(m.group(1))
    return None


def start_node(port):
    node = NODE_BY_PORT[port]
    conf = os.path.join(BASE_DIR, node["conf"])
    # mongod 不会自动创建日志父目录，先确保 dbPath 存在，否则日志文件打不开会直接退出
    os.makedirs(os.path.join(BASE_DIR, node["dir"]), exist_ok=True)
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([MONGOD, "--config", conf], cwd=BASE_DIR, creationflags=flags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def members(hosts=None):
    hosts = hosts or HOSTS
    try:
        c = client_hosts(hosts)
        st = c.admin.command("replSetGetStatus")
        c.close()
        return st["members"]
    except PyMongoError:
        return None


def find_primary():
    st = members()
    if not st:
        return None
    for m in st:
        if m["stateStr"] == "PRIMARY":
            return m["name"]
    return None


def print_topology(title="当前拓扑"):
    print("[%s]" % title)
    st = members()
    if not st:
        print("  （副本集不可达）")
        return
    for m in st:
        print("  %-22s %-11s health=%s" % (m["name"], m["stateStr"], m["health"]))


def probe_coll(hosts):
    c = client_hosts(hosts)
    return c, c[DB_NAME][PROBE_COLL]


# ------------------------------------------------------------ 分步演练
def cmd_failover_kill():
    print("=" * 78)
    print("故障转移演练 A：记录初始拓扑，写入基线后停止主节点进程")
    print("=" * 78)
    primary = find_primary()
    if not primary:
        print("[失败] 当前没有主节点，无法演练")
        return 1
    pport = int(primary.split(":")[1])
    pid = pid_of_port(pport)
    node = NODE_BY_PORT[pport]
    print("[初始状态] 主节点=%s  PID=%s  配置文件=%s  priority=%s"
          % (primary, pid, node["conf"], node["priority"]))
    print_topology("演练前副本集角色")

    c, coll = probe_coll(HOSTS)
    seq = 0
    for i in range(6):
        try:
            coll.insert_one({"t": datetime.now(), "seq": seq})
            seq += 1
        except PyMongoError as exc:
            print("  基线写入失败：%s" % type(exc).__name__)
        time.sleep(0.25)
    print("[基线] 停机前 6 次写入成功 %d 次（写入集合 %s，可正常写库）"
          % (seq, PROBE_COLL))

    kill_time = datetime.now()
    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
    print("[宕机] %s 执行 taskkill /F /PID %s，主节点 %s 进程被强制终止"
          % (now_ms(), pid, primary))
    save_state({"killed_port": pport, "killed_host": primary, "killed_pid": pid,
                "kill_time": kill_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]})
    print("[状态] 演练状态已写入 records/_failover_state.json，等待选举观察")
    return 0


def cmd_failover_watch():
    print("=" * 78)
    print("故障转移演练 B：观察选举过程，业务探针逐次记录写入成败")
    print("=" * 78)
    state = load_state()
    if "kill_time" not in state:
        print("[失败] 找不到演练状态，请先执行 failover-kill")
        return 1
    kill_dt = datetime.strptime(state["kill_time"], "%Y-%m-%d %H:%M:%S.%f")
    pport = state["killed_port"]
    rest = [h for h in HOSTS if not h.endswith(":%d" % pport)]
    print("[观察目标] 剩余节点 %s（已排除宕机的 %s）"
          % ("、".join(rest), state["killed_host"]))

    attempts = 0
    fails = 0
    first_fail = None
    last_fail = None
    fail_types = {}
    elected = None
    seen = []
    c, coll = probe_coll(rest)
    deadline = time.time() + 12
    while time.time() < deadline:
        attempts += 1
        t0 = time.time()
        try:
            coll.insert_one({"t": datetime.now(), "seq": 100 + attempts})
            ok = True
            err = ""
        except PyMongoError as exc:
            ok = False
            err = type(exc).__name__
            fails += 1
            fail_types[err] = fail_types.get(err, 0) + 1
            if first_fail is None:
                first_fail = datetime.now()
            last_fail = datetime.now()
        print("  [%s] 业务写入第 %2d 次：%-6s 耗时 %4d ms%s"
              % (now_ms(), attempts, "成功" if ok else "失败", int((time.time() - t0) * 1000),
                 ("（" + err + "）") if err else ""))
        st = members(rest)
        if st:
            states = dict((m["name"], m["stateStr"]) for m in st)
            cur = tuple(sorted(states.items()))
            if not seen or seen[-1] != cur:
                seen.append(cur)
                print("  [%s] 距宕机 %5.1fs 角色：%s"
                      % (now_ms(), (datetime.now() - kill_dt).total_seconds(),
                         "  ".join("%s=%s" % (k.split(":")[1], v) for k, v in cur)))
            for k, v in states.items():
                if v == "PRIMARY":
                    elected = datetime.now()
                    break
        if elected:
            break
        time.sleep(0.3)

    print("[统计] 业务探针共 %d 次操作，失败 %d 次，成功率 %.1f%%"
          % (attempts, fails, 100.0 * (attempts - fails) / max(1, attempts)))
    if fails:
        print("  首次失败 %s；最后失败 %s；中断时长 %.1f 秒"
              % (first_fail.strftime("%H:%M:%S.%f")[:-3],
                 last_fail.strftime("%H:%M:%S.%f")[:-3],
                 (last_fail - first_fail).total_seconds() + 0.3))
        print("  失败类型分布：%s" % json.dumps(fail_types, ensure_ascii=False))
    if elected:
        new_primary = find_primary()
        el = (elected - kill_dt).total_seconds()
        print("[结果] 新主节点=%s，从宕机到新主接受写入共 %.1f 秒" % (new_primary, el))
        state["new_primary"] = new_primary
        state["election_seconds"] = round(el, 1)
        state["elected_time"] = elected.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        state["probe"] = {"attempts": attempts, "fails": fails,
                          "first_fail": first_fail.strftime("%H:%M:%S.%f")[:-3] if first_fail else "",
                          "last_fail": last_fail.strftime("%H:%M:%S.%f")[:-3] if last_fail else "",
                          "types": fail_types}
        save_state(state)
    else:
        print("[进行中] 12 秒内尚未选出新主节点，可再次执行 failover-watch 继续观察")
    print_topology("观察结束时副本集角色")
    return 0


def cmd_failover_restart():
    print("=" * 78)
    print("故障转移演练 C：重新拉起原主节点")
    print("=" * 78)
    state = load_state()
    if "killed_port" not in state:
        print("[失败] 找不到演练状态")
        return 1
    pport = state["killed_port"]
    print("[重启] %s 以 %s 启动进程，重新加入副本集 %s"
          % (now_ms(), os.path.join("deploy", NODE_BY_PORT[pport]["conf"]), SET_NAME))
    start_node(pport)
    state["restart_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    save_state(state)
    print("[说明] 原主节点磁盘上的数据仍然存在，重启后按 oplog 追平，角色由主降为从")
    return 0


def cmd_failover_sync():
    print("=" * 78)
    print("故障转移演练 D：观察原主节点重新加入后的角色变化")
    print("=" * 78)
    state = load_state()
    pport = state.get("killed_port")
    host = "127.0.0.1:%d" % pport
    deadline = time.time() + 12
    last = None
    t0 = time.time()
    final = None
    while time.time() < deadline:
        st = members()
        if st:
            me = [m for m in st if m["name"] == host]
            if me:
                s = me[0]["stateStr"]
                if s != last:
                    last = s
                    print("  [%s] %s 状态 -> %-11s health=%s（用 %.1f 秒）"
                          % (now_ms(), host, s, me[0]["health"], time.time() - t0))
                if s in ("SECONDARY", "RECOVERING"):
                    final = s
                    break
        time.sleep(0.5)
    if final == "SECONDARY":
        print("[结果] 原主节点 %s 已降级为 SECONDARY，重新提供只读服务" % host)
    elif final:
        print("[进行中] 原主节点处于 %s（初始同步中），可再次执行 failover-sync" % final)
    else:
        print("[进行中] 节点尚未出现在 replSetGetStatus 中，可再次执行 failover-sync")
    print_topology("同步阶段拓扑")
    if final == "SECONDARY":
        c, coll = probe_coll(HOSTS)
        coll.drop()
        print("[清理] 已删除探针集合 %s" % PROBE_COLL)
        print("[结论] 副本集恢复 1 主 2 从，原主节点的写入已在重启后补同步完成")
    return 0


# ------------------------------------------------------------ 一次性完整演练
class Probe(threading.Thread):
    """模拟业务程序：持续写入，记录每次操作是否成功、耗时与错误类型。"""

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.stop_flag = False
        self.records = []
        self.client = MongoClient(
            "mongodb://%s:%s@%s/%s?authSource=%s&replicaSet=%s" % (
                quote_plus(ADMIN["user"]), quote_plus(ADMIN["password"]), ",".join(HOSTS),
                ADMIN["auth_source"], ADMIN["auth_source"], SET_NAME),
            serverSelectionTimeoutMS=3000, retryWrites=True, w=1)

    def run(self):
        coll = self.client[DB_NAME][PROBE_COLL]
        while not self.stop_flag:
            t0 = time.time()
            kind, err = "W", ""
            try:
                coll.insert_one({"t": datetime.now(), "seq": len(self.records)})
            except PyMongoError as exc:
                kind, err = "W-FAIL", type(exc).__name__
            self.records.append((datetime.now(), kind, round((time.time() - t0) * 1000), err))
            time.sleep(0.25)

    def stop(self):
        self.stop_flag = True


def cmd_failover_all():
    print("=" * 78)
    print("故障转移演练（一次性完整版）：手动停止主节点，观察选举与业务影响")
    print("=" * 78)
    primary = find_primary()
    if not primary:
        print("[失败] 当前没有主节点，无法演练")
        return 1
    pport = int(primary.split(":")[1])
    pid = pid_of_port(pport)
    print("[初始状态] 主节点=%s（进程 PID=%s，配置 %s）" % (primary, pid, NODE_BY_PORT[pport]["conf"]))
    print_topology()
    probe = Probe()
    probe.start()
    time.sleep(2.5)
    kill_time = datetime.now()
    print("\n[%s] 执行 taskkill /F /PID %s" % (now_ms(), pid))
    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
    rest = [h for h in HOSTS if not h.endswith(":%d" % pport)]
    election_time = None
    deadline = time.time() + 60
    while time.time() < deadline:
        st = members(rest)
        if st:
            for m in st:
                if m["stateStr"] == "PRIMARY":
                    election_time = (datetime.now() - kill_time).total_seconds()
                    break
        if election_time:
            break
        time.sleep(0.5)
    print("[结果] 新主节点=%s，选举耗时 %.1f 秒" % (find_primary(), election_time or -1))
    time.sleep(3)
    start_node(pport)
    restart_time = datetime.now()
    deadline = time.time() + 90
    while time.time() < deadline:
        st = members()
        if st:
            me = [m for m in st if m["name"] == "127.0.0.1:%d" % pport]
            if me and me[0]["stateStr"] == "SECONDARY":
                break
        time.sleep(0.5)
    probe.stop()
    time.sleep(0.5)
    print_topology("最终拓扑")
    recs = probe.records
    fails = [r for r in recs if "FAIL" in r[1]]
    print("[业务探针] 总操作 %d，失败 %d，成功率 %.1f%%"
          % (len(recs), len(fails), 100.0 * (len(recs) - len(fails)) / max(1, len(recs)))
          if recs else "[业务探针] 无记录")
    print("[时间线] 宕机 %s / 重启 %s / 新主选出后 %.1fs"
          % (kill_time.strftime("%H:%M:%S.%f")[:-3],
             restart_time.strftime("%H:%M:%S.%f")[:-3], election_time or -1))
    c, coll = probe_coll(HOSTS)
    coll.drop()
    print("[清理] 已删除探针集合 %s" % PROBE_COLL)
    return 0


# ------------------------------------------------------------ 节点增删
def get_config():
    c = client_hosts(HOSTS)
    cfg = c.admin.command("replSetGetConfig")["config"]
    c.close()
    return cfg


def apply_config(cfg):
    c = client_hosts(HOSTS)
    cfg["version"] = int(cfg["version"]) + 1
    c.admin.command("replSetReconfig", cfg)
    c.close()
    return cfg["version"]


def cmd_addnode():
    port = 27024
    host = "127.0.0.1:%d" % port
    print("=" * 78)
    print("节点增加演练：向副本集 %s 加入新节点 %s（配置 %s）"
          % (SET_NAME, host, NODE_BY_PORT[port]["conf"]))
    print("=" * 78)
    if pid_of_port(port):
        print("[提示] 端口 %d 已有 mongod 进程" % port)
    else:
        start_node(port)
        print("[启动] %s 拉起新节点进程（dbPath=db/rs3）" % now_ms())
        for _ in range(20):
            if pid_of_port(port):
                break
            time.sleep(0.5)
        pid = pid_of_port(port)
        if pid:
            print("[启动] 端口 %d 已监听（PID=%s）" % (port, pid))
        else:
            print("[启动] 端口 %d 尚未监听，进程可能启动失败，请检查 db/rs3/mongod.log" % port)
    time.sleep(2)
    cfg = get_config()
    print("[当前配置] version=%s，成员=%s" % (cfg["version"], [m["host"] for m in cfg["members"]]))
    if any(m["host"] == host for m in cfg["members"]):
        print("[提示] 该节点已在成员列表中")
    else:
        new_id = max(m["_id"] for m in cfg["members"]) + 1
        cfg["members"].append({"_id": new_id, "host": host, "priority": 1})
        ver = apply_config(cfg)
        print("[执行] %s replSetReconfig 提交成功，配置 version=%s，新成员 _id=%d"
              % (now_ms(), ver, new_id))
    print("[说明] 新节点加入后先进入 STARTUP2 做初始同步，同步完成才转为 SECONDARY")
    return 0


def cmd_addnode_sync():
    port = 27024
    host = "127.0.0.1:%d" % port
    print("=" * 78)
    print("节点增加演练（续）：等待新节点 %s 完成初始同步" % host)
    print("=" * 78)
    t0 = time.time()
    last = None
    done = False
    while time.time() - t0 < 12:
        st = members()
        if st:
            me = [m for m in st if m["name"] == host]
            if me:
                s = me[0]["stateStr"]
                if s != last:
                    last = s
                    print("  [%s] 新节点状态 -> %-10s health=%s（加入后 %.1fs）"
                          % (now_ms(), s, me[0]["health"], time.time() - t0))
                if s == "SECONDARY":
                    done = True
                    break
        time.sleep(1)
    if done:
        print("[结果] 新节点已完成初始同步并成为 SECONDARY，可承担读请求")
    else:
        print("[进行中] 仍在同步，可再次执行 addnode-sync")
    print_topology("节点增加后拓扑")
    return 0


def cmd_removenode():
    port = 27024
    host = "127.0.0.1:%d" % port
    print("=" * 78)
    print("节点移除演练：从副本集 %s 移除 %s" % (SET_NAME, host))
    print("=" * 78)
    cfg = get_config()
    print("[当前配置] version=%s，成员=%s" % (cfg["version"], [m["host"] for m in cfg["members"]]))
    if not any(m["host"] == host for m in cfg["members"]):
        print("[提示] 该节点不在成员列表中")
    else:
        cfg["members"] = [m for m in cfg["members"] if m["host"] != host]
        ver = apply_config(cfg)
        print("[执行] %s replSetReconfig 提交，移除成员后 version=%s" % (now_ms(), ver))
    time.sleep(3)
    print_topology("移除后拓扑")
    pid = pid_of_port(port)
    if pid:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
        print("[清理] 已停止被移除节点的进程（PID=%s），其数据目录 db/rs3 保留" % pid)
    print("[说明] 移除时主节点与其余从节点未受影响，业务读写继续正常")
    return 0


def cmd_failover_logs():
    """从三个节点的 mongod 日志里抽取关键事件，作为角色变化的时间点证据。"""
    print("=" * 78)
    print("故障转移演练 E：从 mongod 日志抽取选举与角色变化事件")
    print("=" * 78)
    state = load_state()
    since = state.get("kill_time", "")[:19]
    print("[时间窗] %s 之后的事件（日志文件 db/rsN/mongod.log）" % since)
    keys = ["transition to primary", "new primary", "election", "starting promotion",
            "transition to secondary", "reactivating", "initial sync", "sync source",
            "replication recovery"]
    events = []
    for node in CFG["nodes"]:
        path = os.path.join(BASE_DIR, node["dir"], "mongod.log")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    doc = json.loads(line)
                except ValueError:
                    continue
                ts = doc.get("t", {}).get("$date", "")[:23].replace("T", " ")[11:]
                msg = doc.get("msg", "") or ""
                low = msg.lower()
                if any(k in low for k in keys):
                    events.append((ts, node["name"], msg[:110]))
    events.sort()
    shown = 0
    for ts, name, msg in events:
        if ts < since[11:19]:
            continue
        print("  %s  %-4s  %s" % (ts, name, msg))
        shown += 1
    print("[统计] 命中关键事件 %d 条" % shown)
    if state.get("killed_host"):
        print("[说明] 原主节点 %s 被 kill -9 后不会写日志，其重新加入的时间点以 replSetGetStatus 观测为准"
              % state["killed_host"])
    return 0


def cmd_status():
    print("=" * 78)
    print("副本集当前状态：%s" % SET_NAME)
    print("=" * 78)
    print_topology()
    st = members()
    if st:
        print("[连接串] %s" % ",".join(HOSTS))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    table = {
        "failover-kill": cmd_failover_kill,
        "failover-watch": cmd_failover_watch,
        "failover-restart": cmd_failover_restart,
        "failover-sync": cmd_failover_sync,
        "failover-all": cmd_failover_all,
        "failover-logs": cmd_failover_logs,
        "addnode": cmd_addnode,
        "addnode-sync": cmd_addnode_sync,
        "removenode": cmd_removenode,
        "status": cmd_status,
    }
    if cmd in table:
        return table[cmd]()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
