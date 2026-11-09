"""导出/恢复数据备份（环境无 mongodump，改用 pymongo + Extended JSON）。

用法：
    python src/tools/backup_db.py dump   导出到 backups\\<库名>_<时间戳>\\
    python src/tools/backup_db.py restore <备份目录>
"""
import datetime
import json
import os
import sys

from bson import json_util
from pymongo import MongoClient
from urllib.parse import quote_plus

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONF = os.environ.get("LIB_CONFIG") or os.path.join(ROOT, "config", "config.json")


def load_conf():
    with open(CONF, "r", encoding="utf-8") as f:
        return json.load(f)["mongo"]


def client(cfg):
    if cfg.get("uri"):
        return MongoClient(cfg["uri"], serverSelectionTimeoutMS=8000)
    return MongoClient("mongodb://%s:%s@%s:%d/?authSource=%s" % (
        quote_plus(cfg["username"]), quote_plus(cfg["password"]),
        cfg["host"], cfg["port"], cfg["auth_source"]), serverSelectionTimeoutMS=8000)


def cmd_dump():
    cfg = load_conf()
    c = client(cfg)
    db = c[cfg["db_name"]]
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out = os.path.join(ROOT, "backups", "%s_%s" % (cfg["db_name"], stamp))
    os.makedirs(out, exist_ok=True)
    print("=" * 74)
    print("数据备份导出：%s -> %s" % (cfg["db_name"], out))
    print("=" * 74)
    manifest = {"db": cfg["db_name"], "created": stamp, "collections": {}}
    for name in db.list_collection_names():
        if name.startswith("system."):
            continue
        docs = list(db[name].find({}))
        path = os.path.join(out, name + ".json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(json_util.dumps(docs, ensure_ascii=False, indent=1))
        manifest["collections"][name] = {
            "count": len(docs),
            "file": name + ".json",
            "indexes": [i["name"] for i in db[name].list_indexes()],
        }
        print("  %-15s %5d 条 -> %s" % (name, len(docs), name + ".json"))
    mpath = os.path.join(out, "_manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("\n[清单] %s" % mpath)
    print("[恢复] python src/tools/backup_db.py restore \"%s\"" % out)
    c.close()
    return 0


def cmd_restore(folder):
    cfg = load_conf()
    c = client(cfg)
    db = c[cfg["db_name"]]
    with open(os.path.join(folder, "_manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)
    print("=" * 74)
    print("数据恢复：%s <- %s" % (cfg["db_name"], folder))
    print("=" * 74)
    for name, meta in manifest["collections"].items():
        path = os.path.join(folder, meta["file"])
        with open(path, "r", encoding="utf-8") as f:
            docs = json_util.loads(f.read())
        if docs:
            db[name].delete_many({})
            db[name].insert_many(docs)
        print("  %-15s 恢复 %5d 条" % (name, len(docs)))
    print("[完成] 请重新执行 create_indexes.py 以恢复索引")
    c.close()
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("dump", "restore"):
        print(__doc__)
        return 1
    if sys.argv[1] == "dump":
        return cmd_dump()
    return cmd_restore(sys.argv[2])


if __name__ == "__main__":
    sys.exit(main())
