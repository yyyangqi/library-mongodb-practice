"""电子书存储模块（F8）：GridFS 上传、按书名检索下载、字节数校验、文件清单。"""
import hashlib
import os
from datetime import datetime, timezone

from gridfs.errors import NoFile


def _local(dt):
    """GridFS 的 uploadDate 为 UTC naive，转为本地时间字符串展示。"""
    if dt is None:
        return "-"
    return dt.replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_file(fs, path, isbn, file_type, display_name=None):
    """上传单个文件，写入 isbn / file_type / original_name 元数据。"""
    name = display_name or os.path.basename(path)
    if fs.exists({"filename": name}):
        fs.delete(fs.find_one({"filename": name})._id)
    with open(path, "rb") as f:
        file_id = fs.put(
            f.read(),
            filename=name,
            metadata={
                "isbn": isbn,
                "file_type": file_type,          # ebook / cover
                "original_name": os.path.basename(path),
                "upload_ts": datetime.now(),
                "size_bytes": os.path.getsize(path),
                "md5": _md5(path),
            },
        )
    return file_id


def upload_from_manifest(fs, manifest_path, file_dir, books_coll):
    """按 files_manifest.txt 建立 ISBN 关联，批量上传 PDF 与封面图。"""
    import json
    with open(manifest_path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        manifest = json.loads(raw)
        ebooks = manifest.get("ebooks", [])
        covers = manifest.get("covers", [])
    except json.JSONDecodeError:
        ebooks, covers = [], []
    uploaded = []
    for item in ebooks:                        # 电子书 PDF
        p = os.path.join(file_dir, item["filename"])
        if not os.path.exists(p):
            continue
        upload_file(fs, p, item["related_isbn"], "ebook")
        uploaded.append((item["filename"], "ebook", item["related_isbn"], os.path.getsize(p)))
    for item in covers:                        # 封面图
        p = os.path.join(file_dir, item["filename"])
        if not os.path.exists(p):
            continue
        upload_file(fs, p, item["related_isbn"], "cover")
        uploaded.append((item["filename"], "cover", item["related_isbn"], os.path.getsize(p)))
    return uploaded


def find_by_title(fs, books_coll, title):
    """按书名（模糊）定位图书，返回其电子书与封面的 GridFS 文件信息。

    若书名关键词命中多本图书，优先返回真正挂有电子书文件的那一本；
    只有都无文件时才返回第一本，避免「按书名下载」落到无电子书的书上。
    """
    books = list(books_coll.find({"title": {"$regex": title, "$options": "i"}},
                                 {"_id": 0, "isbn": 1, "title": 1, "ebook_name": 1}))
    if not books:
        return None, []
    first_book, first_files = None, []
    for book in books:
        files = _files_of(fs, book)
        if first_book is None:
            first_book, first_files = book, files
        if files:
            return book, files
    return first_book, first_files


def _files_of(fs, book):
    isbn = book["isbn"]
    files = []
    for meta in fs.find({"$or": [{"metadata.isbn": isbn}, {"filename": book.get("ebook_name")}]}):
        files.append({
            "filename": meta.filename,
            "length": meta.length,
            "upload_date": _local(meta.upload_date),
            "file_type": (meta.metadata or {}).get("file_type"),
            "isbn": (meta.metadata or {}).get("isbn"),
        })
    return files


def download(fs, filename, out_dir):
    """下载文件到本地，返回 (本地路径, 期望字节数, 实际字节数, 是否一致)。"""
    grid_out = fs.get_last_version(filename=filename)
    os.makedirs(out_dir, exist_ok=True)
    local = os.path.join(out_dir, filename)
    with open(local, "wb") as f:
        f.write(grid_out.read())
    expected = grid_out.length
    actual = os.path.getsize(local)
    return local, expected, actual, expected == actual


def download_by_title(fs, books_coll, title, out_dir):
    book, files = find_by_title(fs, books_coll, title)
    if not book:
        return book, None, []
    results = []
    for meta in files:
        local, exp, act, ok = download(fs, meta["filename"], out_dir)
        results.append({"filename": meta["filename"], "local": local,
                        "gridfs_bytes": exp, "local_bytes": act, "match": ok})
    return book, files, results


def list_files(fs):
    """列出 GridFS 全部文件（文件名、大小、上传时间、类型）。"""
    rows = []
    for meta in fs.find().sort("uploadDate", 1):
        rows.append({
            "filename": meta.filename,
            "size_kb": round(meta.length / 1024, 1),
            "bytes": meta.length,
            "upload_date": _local(meta.upload_date),
            "file_type": (meta.metadata or {}).get("file_type", "-"),
            "isbn": (meta.metadata or {}).get("isbn", "-"),
        })
    return rows
