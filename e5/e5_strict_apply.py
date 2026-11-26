"""把断言审计结论写回 e5_runner.json（只附加字段，不改 verdict）。

附加：evidence_tier(A/B/C/D)、strict_verdict(pass_strict/pass_thin)、
assert_evidence(最多 3 条真实断言行)、assert_stats{strong,trivial,cmp,files}；
summary 增加 strict_counts 与 note。原文件先备份。
"""
import json, os, shutil, time

E5 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e5_20261125")
RUN = os.path.join(E5, "e5_runner.json")
AUD = os.path.join(E5, "e5_assert_audit_company.json")

runner = json.load(open(RUN, encoding="utf-8"))
aud = {r["repo"]: r for r in json.load(open(AUD, encoding="utf-8"))["records"]}


def tier(p):
    if p >= 20:
        return "A"
    if p >= 6:
        return "B"
    if p >= 3:
        return "C"
    return "D"


for x in runner["records"]:
    if x["verdict"] != "pass":
        continue
    a = aud.get(x["repo"], {})
    x["evidence_tier"] = tier(x.get("passed", 0))
    strict = x.get("passed", 0) >= 3 and (a.get("strong", 0) > 0 or a.get("cmp", 0) > 0)
    x["strict_verdict"] = "pass_strict" if strict else "pass_thin"
    x["assert_stats"] = {"strong": a.get("strong", 0), "trivial": a.get("trivial", 0),
                         "cmp": a.get("cmp", 0), "files": a.get("files_scanned", 0)}
    x["assert_evidence"] = a.get("samples", [])
    if not strict:
        x["manual_review_note"] = ("测试文件内无断言/无状态比对，或 passed<3；"
                                   "计数为脚本自报，不计入合格")

n_strict = sum(1 for x in runner["records"] if x.get("strict_verdict") == "pass_strict")
n_thin = sum(1 for x in runner["records"] if x.get("strict_verdict") == "pass_thin")
runner["summary"]["strict_counts"] = {"pass_strict": n_strict, "pass_thin": n_thin}
runner["summary"]["strict_note"] = ("严格合格 = passed>=3 且测试文件内至少一处非平凡断言或状态比对；"
                                    "薄证据不计入合格。算法见 断言判定算法_20261126.md")
runner["summary"]["strict_generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
runner["summary"]["strict_machine"] = "company (client:582478:3880613324794288)"

shutil.copy(RUN, RUN + ".bak_before_strict_company_20261126")
json.dump(runner, open(RUN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("strict", n_strict, "thin", n_thin)
for x in runner["records"]:
    if x.get("strict_verdict") == "pass_thin":
        print("thin:", x["repo"], "passed", x["passed"], x["assert_stats"])
