import hashlib, os, sys
root = sys.argv[1] if len(sys.argv) > 1 else "."
e1 = open(os.path.join(root, "inputs", "evidence_1.txt"), "rb").read()
e2 = open(os.path.join(root, "inputs", "evidence_2.txt"), "rb").read()
out = os.path.join(root, "outputs", "result.txt")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8", newline="\n").write(
    "spine_sha256=%s\nmethod=sha256(evidence_1 || evidence_2)\n" % hashlib.sha256(e1 + e2).hexdigest())
