"""任务六：分片集群部署与验证。

拓扑（教学环境，单机多进程模拟）：
    config server  : 127.0.0.1:27019  副本集 csrs（单成员，生产建议 3 成员）
    shard1         : 127.0.0.1:27031  副本集 shard1（单成员）
    shard2         : 127.0.0.1:27032  副本集 shard2（单成员）
    mongos         : 127.0.0.1:27101  路由，连接串 mongodb://127.0.0.1:27101

三个 mongod 与 mongos 共用 deploy/keyfile，集群内部认证与账号认证同时开启。

分步命令（每步都很快，便于逐条留证）：
    python tools/shard_setup.py conf      # 生成 4 个配置文件
    python tools/shard_setup.py start-all # 拉起 config server + 两个分片
    python tools/shard_setup.py init      # 初始化三个副本集并创建 root 账号
    python tools/shard_setup.py mongos    # 拉起 mongos
    python tools/shard_setup.py shards    # 添加两个分片，查看分片状态
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from urllib.parse import quote_plus

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pymongo import MongoClient                              # noqa: E402
from pymongo.errors import PyMongoError                      # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MONGOD = r"D:\MongoDB\mongodb\mongodb-win32-x86_64-windows-8.0.4\bin\mongod.exe"
MONGOS = r"D:\MongoDB\mongodb\mongodb-win32-x86_64-windows-8.0.4\bin\mongos.exe"
KEYFILE = os.path.join(BASE_DIR, "deploy", "keyfile")

CS_PORT = 27019
SHARD_PORTS = [27031, 27032]
MONGOS_PORT = 27101
ADMIN_USER = "root"
ADMIN_PASS = "Super@2025"

NODES = [
    {"name": "cs", "port": CS_PORT, "dir": "db/cs", "conf": "deploy/cs.conf",
     "role": "configsvr", "replset": "csrs"},
    {"name": "shard1", "port": 27031, "dir": "db/shard1", "conf": "deploy/shard1.conf",
     "role": "shardsvr", "replset": "shard1"},
    {"name": "shard2", "port": 27032, "dir": "db/shard2", "conf": "deploy/shard2.conf",
     "role": "shardsvr", "replset": "shard2"},
]
CONF_TEMPLATE = """storage:
  dbPath: {dbpath}
replication:
  replSetName: {replset}
sharding:
  clusterRole: {role}
net:
  port: {port}
  bindIp: 127.0.0.1
security:
  keyFile: {keyfile}
  authorization: enabled
systemLog:
  destination: file
  path: {logpath}
  logAppend: true
"""
MONGOS_TEMPLATE = """net:
  port: {port}
  bindIp: 127.0.0.1
sharding:
  configDB: csrs/127.0.0.1:{csport}
security:
  keyFile: {keyfile}
systemLog:
  destination: file
  path: {logpath}
  logAppend: true
"""


def now_ms():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def uri(port, user=None, pwd=None, auth_source="admin", extra=""):
    if user:
        return "mongodb://%s:%s@127.0.0.1:%d/?authSource=%s%s" % (
            quote_plus(user), quote_plus(pwd), port, auth_source, extra)
    return "mongodb://127.0.0.1:%d/?directConnection=true%s" % (port, extra)


def connect(port, user=ADMIN_USER, pwd=ADMIN_PASS, auth_source="admin", timeout=8000):
    return MongoClient(uri(port, user, pwd, auth_source),
                       serverSelectionTimeoutMS=timeout, appname="shard-setup")


def port_open(port):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def conf_path(name):
    return os.path.join(BASE_DIR, "deploy", name)


def cmd_conf():
    for n in NODES:
        os.makedirs(os.path.join(BASE_DIR, n["dir"]), exist_ok=True)
        text = CONF_TEMPLATE.format(
            dbpath=os.path.join(BASE_DIR, n["dir"]).replace("\\", "/"),
            replset=n["replset"], role=n["role"], port=n["port"],
            keyfile=KEYFILE.replace("\\", "/"),
            logpath=os.path.join(BASE_DIR, n["dir"], "mongod.log").replace("\\", "/"))
        with open(conf_path(os.path.basename(n["conf"])), "w", encoding="utf-8") as f:
            f.write(text)
        print("[生成] %s（端口 %d，%s，dbPath=%s）" % (n["conf"], n["port"], n["replset"], n["dir"]))
    text = MONGOS_TEMPLATE.format(port=MONGOS_PORT, csport=CS_PORT,
                                 keyfile=KEYFILE.replace("\\", "/"),
                                 logpath=os.path.join(BASE_DIR, "db", "mongos.log").replace("\\", "/"))
    with open(conf_path("mongos.conf"), "w", encoding="utf-8") as f:
        f.write(text)
    print("[生成] deploy/mongos.conf（端口 %d，configDB=csrs/127.0.0.1:%d）" % (MONGOS_PORT, CS_PORT))
    return 0


def start(exe, conf, name):
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([exe, "--config", conf], cwd=BASE_DIR, creationflags=flags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[启动] %s %s" % (name, os.path.basename(conf)))


def cmd_start_all():
    print("=" * 78)
    print("分片集群部署 A：拉起配置服务器与两个分片")
    print("=" * 78)
    for n in NODES:
        conf = conf_path(os.path.basename(n["conf"]))
        if port_open(n["port"]):
            print("[跳过] %s 端口 %d 已在监听" % (n["name"], n["port"]))
            continue
        start(MONGOD, conf, n["name"])
    for n in NODES:
        for _ in range(40):
            if port_open(n["port"]):
                break
            time.sleep(0.5)
        print("[状态] %-6s 端口 %d %s" % (n["name"], n["port"], "已监听" if port_open(n["port"]) else "未监听"))
    return 0


def initiate(port, replset, members):
    c = MongoClient("mongodb://127.0.0.1:%d/?directConnection=true" % port,
                    serverSelectionTimeoutMS=8000, directConnection=True)
    try:
        c.admin.command("replSetGetStatus")
        print("[跳过] %s 已初始化" % replset)
        return
    except PyMongoError:
        pass
    cfg = {"_id": replset, "members": [{"_id": i, "host": h} for i, h in enumerate(members)]}
    c.admin.command("replSetInitiate", cfg)
    print("[执行] %s replSetInitiate 提交，成员=%s" % (replset, members))
    for _ in range(30):
        try:
            st = c.admin.command("replSetGetStatus")
            if st["myState"] == 1:
                print("[状态] %s 已选出主节点（myState=PRIMARY）" % replset)
                return
        except PyMongoError:
            pass
        time.sleep(0.5)
    print("[状态] %s 初始化后仍未就绪" % replset)


def create_root(port):
    """在开启认证且尚无用户的实例上，用 localhost exception 创建 root 账号。"""
    c = MongoClient("mongodb://127.0.0.1:%d/?directConnection=true" % port,
                    serverSelectionTimeoutMS=8000, directConnection=True)
    try:
        c.admin.command("replSetGetStatus")
    except PyMongoError:
        pass
    try:
        c.admin.command("createUser", ADMIN_USER, pwd=ADMIN_PASS, roles=["root"])
        print("[账号] 端口 %d 已创建 root 账号" % port)
    except PyMongoError as exc:
        print("[账号] 端口 %d 创建账号跳过：%s" % (port, str(exc)[:90]))
    c.close()


def cmd_init():
    print("=" * 78)
    print("分片集群部署 B：初始化配置服务器副本集与两个分片副本集")
    print("=" * 78)
    for n in NODES:
        initiate(n["port"], n["replset"], ["127.0.0.1:%d" % n["port"]])
    print("")
    for n in NODES:
        create_root(n["port"])
    print("[说明] 配置服务器与分片都用单成员副本集，是为了在单机上跑通；生产环境配置服务器需要 3 成员")
    return 0


def cmd_mongos():
    print("=" * 78)
    print("分片集群部署 C：拉起 mongos 路由")
    print("=" * 78)
    if port_open(MONGOS_PORT):
        print("[跳过] mongos 端口 %d 已在监听" % MONGOS_PORT)
        return 0
    start(MONGOS, conf_path("mongos.conf"), "mongos")
    for _ in range(40):
        if port_open(MONGOS_PORT):
            break
        time.sleep(0.5)
    print("[状态] mongos 端口 %d %s" % (MONGOS_PORT, "已监听" if port_open(MONGOS_PORT) else "未监听"))
    return 0


def cmd_shards():
    print("=" * 78)
    print("分片集群部署 D：向 mongos 注册两个分片并查看集群状态")
    print("=" * 78)
    c = connect(MONGOS_PORT)
    existing = [s["host"] for s in c.admin.command("listShards")["shards"]]
    for port in SHARD_PORTS:
        host = "shard%d/127.0.0.1:%d" % (SHARD_PORTS.index(port) + 1, port)
        if any(host in e for e in existing):
            print("[跳过] 分片 %s 已存在" % host)
            continue
        print("[执行] %s addShard %s" % (now_ms(), host))
        try:
            c.admin.command("addShard", host)
            print("[结果] 分片 %s 添加成功" % host)
        except PyMongoError as exc:
            print("[失败] 添加 %s 出错：%s" % (host, str(exc)[:150]))
    print("")
    print("[分片列表] %s" % [s["host"] for s in c.admin.command("listShards")["shards"]])
    print("[集群概况]")
    import pprint
    try:
        st = c.admin.command("serverStatus")["sharding"]
        for k, v in st.items():
            print("  %-16s %s" % (k, v))
    except PyMongoError as exc:
        print("  读取 serverStatus 失败：%s" % str(exc)[:80])
    c.close()
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    table = {"conf": cmd_conf, "start-all": cmd_start_all, "init": cmd_init,
             "mongos": cmd_mongos, "shards": cmd_shards}
    if cmd in table:
        return table[cmd]()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
