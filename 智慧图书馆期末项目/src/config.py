"""统一配置模块：读取 config/config.json，并支持环境变量覆盖。

所有程序文件通过本模块获取连接参数与路径，避免在代码中硬编码。
"""
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = BASE_DIR / "config" / "config.json"


def _ensure_utf8():
    """Windows 控制台默认编码可能导致中文输出异常，这里统一为 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_config(path=None) -> dict:
    _ensure_utf8()
    cfg_path = Path(path or os.environ.get("LIB_CONFIG") or DEFAULT_CONFIG)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    mongo = cfg.setdefault("mongo", {})
    # 环境变量优先级最高，便于换机部署
    if os.environ.get("LIB_MONGO_URI"):
        mongo["uri"] = os.environ["LIB_MONGO_URI"]
    if os.environ.get("LIB_MONGO_DB"):
        mongo["db_name"] = os.environ["LIB_MONGO_DB"]
    if os.environ.get("LIB_MONGO_USER"):
        mongo["username"] = os.environ["LIB_MONGO_USER"]
    if os.environ.get("LIB_MONGO_PASS"):
        mongo["password"] = os.environ["LIB_MONGO_PASS"]
    if os.environ.get("LIB_READ_PREF"):
        mongo["read_preference"] = os.environ["LIB_READ_PREF"]
    if os.environ.get("LIB_MONGO_REPLSET"):
        mongo["replica_set"] = os.environ["LIB_MONGO_REPLSET"]

    paths = cfg.setdefault("paths", {})
    for key, default in (("data_dir", "data"), ("download_dir", "downloads"), ("export_dir", "exports")):
        paths[key] = str((BASE_DIR / paths.get(key, default)).resolve()) if not os.path.isabs(paths.get(key, default)) else paths[key]
    cfg["base_dir"] = str(BASE_DIR)
    return cfg


def build_uri(mongo: dict) -> str:
    if mongo.get("uri"):
        return mongo["uri"]
    from urllib.parse import quote_plus
    host = mongo.get("host", "127.0.0.1")
    port = mongo.get("port", 27017)
    user = mongo.get("username")
    pwd = mongo.get("password")
    if user and pwd:
        auth = mongo.get("auth_source") or mongo.get("db_name", "admin")
        return "mongodb://%s:%s@%s:%s/?authSource=%s" % (
            quote_plus(user), quote_plus(pwd), host, port, auth)
    return "mongodb://%s:%s/" % (host, port)


CONFIG = load_config()
