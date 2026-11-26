"""内容指纹：把"这棵树"压成一个 sha256，供基线/复跑两侧比对。

算法（必须两处共用，改这里就两边同时改）：
  SKIP_DIRS 内目录整枝跳过；
  逐文件取 rel_path(正斜杠) 与 sha256(全文)，组成 "path<TAB>hash"；
  行按字典序排序，用 "\n" 连接，再取 sha256。
"""
import hashlib, os

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".tox"}
ALGO = "sha256(sorted 'rel_path\\tsha256(file)' lines, skip=" + ",".join(sorted(SKIP_DIRS)) + ")"


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 16)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def manifest(root):
    """返回 (digest, file_count)。"""
    items = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            try:
                h256 = file_sha256(p)
            except Exception:
                h256 = "UNREADABLE"
            items.append("%s\t%s" % (rel, h256))
    items.sort()
    return hashlib.sha256("\n".join(items).encode()).hexdigest(), len(items)
