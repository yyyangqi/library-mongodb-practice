"""按任务二的索引清单创建全部索引。

用法：python tools/create_indexes.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pymongo import ASCENDING, DESCENDING          # noqa: E402

import audit                                       # noqa: E402
import books as book_mod                           # noqa: E402
import borrow as borrow_mod                        # noqa: E402
import readers as reader_mod                       # noqa: E402
import stats as stats_mod                          # noqa: E402
from db import LibraryDB                           # noqa: E402


def main():
    with LibraryDB() as db:
        book_mod.ensure_indexes(db.books)
        reader_mod.ensure_indexes(db.readers)
        borrow_mod.ensure_indexes(db.borrow_logs)
        db.audit_logs.create_index([("ts", DESCENDING)], name="idx_ts_desc")
        db.audit_logs.create_index([("action", ASCENDING), ("ts", DESCENDING)], name="idx_action_ts")
        stats_mod.ensure_indexes(db.category_stats)

        print("[索引清单]")
        for coll in ("books", "readers", "borrow_logs", "audit_logs", "category_stats"):
            print("\n%s：" % coll)
            for idx in db.db[coll].list_indexes():
                keys = ", ".join("%s:%s" % (k, v) for k, v in idx["key"].items())
                print("  %-24s %-28s unique=%s" % (idx["name"], keys, idx.get("unique", False)))
        audit.write_audit(db.audit_logs, "INDEX", "all_collections", "创建索引并校验")
    return 0


if __name__ == "__main__":
    sys.exit(main())
