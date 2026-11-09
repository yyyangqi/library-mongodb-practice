"""F8 执行记录：GridFS 上传、按书名下载、字节数校验、文件清单。"""
import hashlib
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import audit                                        # noqa: E402
import files as file_mod                            # noqa: E402
from config import CONFIG                          # noqa: E402
from db import LibraryDB                            # noqa: E402

OUT = io.StringIO()


def out(text=""):
    print(text)
    OUT.write(text + "\n")


def main():
    with LibraryDB() as db:
        data_dir = CONFIG["paths"]["data_dir"]
        file_dir = os.path.join(data_dir, "gridfs_files")
        manifest = os.path.join(file_dir, "files_manifest.txt")

        out("GridFS 文件存储执行记录")
        out("=" * 70)
        ups = file_mod.upload_from_manifest(db.fs, manifest, file_dir, db.books)
        out("\n[上传] 按 manifest 建立 ISBN 关联，共 %d 个文件" % len(ups))
        for name, ftype, isbn, size in ups:
            src = os.path.join(file_dir, name)
            with open(src, "rb") as f:
                local_md5 = hashlib.md5(f.read()).hexdigest()
            g = db.fs.find_one({"filename": name})
            out("  %-14s 类型=%-6s ISBN=%-14s 源文件=%6d 字节  GridFS=%6d 字节  元数据md5一致=%s"
                % (name, ftype, isbn, size, g.length, g.metadata.get("md5") == local_md5))
        audit.write_audit(db.audit_logs, "UPLOAD", "gridfs", "上传 %d 个文件" % len(ups))

        out("\n[清单] GridFS 全部文件")
        out("  %-14s %8s %-8s %-20s %-14s" % ("文件名", "大小KB", "类型", "上传时间", "关联ISBN"))
        for r in file_mod.list_files(db.fs):
            out("  %-14s %8.1f %-8s %-20s %-14s"
                % (r["filename"], r["size_kb"], r["file_type"], r["upload_date"], r["isbn"]))
        rows = file_mod.list_files(db.fs)
        out("  合计 %d 个文件，%d 字节" % (len(rows), sum(r["bytes"] for r in rows)))

        out("\n[按书名检索并下载]")
        for title in ("Python编程", "深入理解计算机系统", "经济学原理"):
            book, fs_meta, results = file_mod.download_by_title(
                db.fs, db.books, title, CONFIG["paths"]["download_dir"])
            if not book:
                out("  %-20s 未找到图书" % title)
                continue
            out("  书名关键词「%s」-> %s（ISBN %s），关联文件 %d 个"
                % (title, book["title"], book["isbn"], len(results)))
            for r in results:
                out("    %-14s GridFS=%6d 字节  下载后=%6d 字节  校验=%s  保存至=%s"
                    % (r["filename"], r["gridfs_bytes"], r["local_bytes"],
                       "一致" if r["match"] else "不一致", r["local"]))
                audit.write_audit(db.audit_logs, "DOWNLOAD", "gridfs", "下载 %s" % r["filename"])

    path = os.path.join(CONFIG["base_dir"], "records", "任务四_GridFS执行记录.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n记录已保存：%s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
