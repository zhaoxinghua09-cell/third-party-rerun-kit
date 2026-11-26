"""生成 E5 逐件证据附录（自包含、零外链、零 <a href>）。

目的：让「36 件合格」不是数字，而是 61 条可逐条核对的证据（commit + 入口 + 真实输出尾）。
"""
import html
import json
import os
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(ROOT, "e5_20261125", "e5_runner.json")
STRUCT = os.path.join(ROOT, "e5_20261125", "e5_structural.json")
OUT = os.path.join(ROOT, "e5_20261125", "E5逐件证据附录_20261126.html")

COLOR = {"pass": "#2e7d32", "partial": "#c62828", "no_tests_collected": "#ef6c00",
         "not_runnable": "#b71c1c", "no_entry": "#616161"}

r = json.load(open(RUNNER, encoding="utf-8"))
s = json.load(open(STRUCT, encoding="utf-8"))
recs = r["records"]
by_struct = {x["repo"]: x for x in s["records"]}
ru = r["summary"]
npass = ru["counts"].get("pass", 0)

cards = []
for i, x in enumerate(sorted(recs, key=lambda z: (z["verdict"] != "pass", -z.get("passed", 0))), 1):
    st = by_struct.get(x["repo"], {})
    ent = st.get("verification_entries") or []
    tail = (x.get("tail") or [])[-4:]
    note = x.get("manual_review_note")
    cards.append(f"""
<div class="card">
  <div class="hd"><span class="no">{i:02d}</span>
    <span class="repo">{html.escape(x["repo"])}</span>
    <span class="tag" style="background:{COLOR.get(x['verdict'],'#555')}">{html.escape(x['verdict'])}</span>
    <span class="tier">强度 {html.escape(x.get("evidence_tier","-"))}</span>
    {f'<span class="tag" style="background:#8e24aa">薄，不计合格</span>' if x.get("strict_verdict")=="pass_thin" else ''}
  </div>
  <div class="meta">commit <code>{html.escape((x.get("commit") or "")[:12])}</code>
    · passed <b>{x.get("passed",0)}</b> · failed <b>{x.get("failed",0)}</b> · errors <b>{x.get("errors",0)}</b>
    · exit <b>{x.get("exit","")}</b> · {x.get("seconds","")}s · 解包 {(x.get("bytes") or 0)//1024} KB</div>
  <div class="meta">入口：<code>{html.escape(", ".join(ent) if ent else "(未记录)")}</code></div>
  {f'<div class="note">{html.escape(note)}</div>' if note else ''}
  <pre class="out">{html.escape("\n".join(tail) if tail else "(无输出)")}</pre>
</div>""")

doc = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>E5 逐件证据附录 2026-11-26（家机）</title>
<style>
body{{font:14px/1.6 "Segoe UI",system-ui,sans-serif;margin:0;padding:30px 36px;background:#fff;color:#111}}
h1{{font-size:24px;margin:0 0 6px}} .sub{{color:#666;margin-bottom:22px}}
.kpi{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px}}
.k{{border:1px solid #e3e3e3;border-radius:9px;padding:10px 16px}} .k b{{font-size:24px;display:block}}
.k span{{color:#666;font-size:12px}}
.warn{{border:1px solid #e3e3e3;border-left:4px solid #1565c0;background:#f6faff;border-radius:8px;padding:12px 16px;margin:0 0 22px;font-size:13px}}
.card{{border:1px solid #e6e6e6;border-radius:10px;padding:12px 16px;margin:10px 0}}
.hd{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.no{{color:#9e9e9e;font-variant-numeric:tabular-nums;font-size:12px}}
.repo{{font-family:Consolas,monospace;font-size:14px;font-weight:600}}
.tag{{color:#fff;border-radius:4px;padding:1px 7px;font-size:11px}}
.tier{{border:1px solid #ccc;border-radius:4px;padding:1px 6px;font-size:11px;color:#444}}
.note{{border-left:3px solid #c62828;background:#fff6f6;padding:6px 10px;margin:8px 0 0;font-size:12px;color:#7a1f1f}}
.meta{{color:#555;font-size:12px;margin-top:5px}}
code{{background:#f5f5f5;padding:1px 5px;border-radius:4px;font-size:11px}}
.out{{background:#fbfbfb;border:1px solid #eee;border-radius:6px;padding:8px 10px;margin:8px 0 0;
font-family:Consolas,monospace;font-size:11px;color:#333;white-space:pre-wrap;word-break:break-all}}
</style>
<h1>E5 逐件证据附录：{len(recs)} 件，{npass} 件合格</h1>
<div class="sub">生成 {time.strftime('%Y-%m-%d %H:%M')} · 家机 · 每件 = 一个 commit + 一组入口 + 一段真实输出尾 · 无外链、无 a 标签</div>

<div class="kpi">
  <div class="k"><b>{len(recs)}</b><span>实跑件数</span></div>
  <div class="k"><b>{npass}</b><span>合格</span></div>
  <div class="k"><b>{ru["counts"].get("partial",0)}</b><span>有失败</span></div>
  <div class="k"><b>{ru["counts"].get("no_tests_collected",0)}</b><span>入口在但收集 0</span></div>
  <div class="k"><b>{ru["counts"].get("not_runnable",0)}</b><span>跑不起来</span></div>
  <div class="k"><b>{npass - ru.get("evidence_tiers_of_pass",{}).get("D",0)}</b><span>强合格（≥3 条通过）</span></div>
  <div class="k"><b>{ru.get("evidence_tiers_of_pass",{}).get("D",0)}</b><span>薄证据（1-2 条，待人工复核）</span></div>
  <div class="k"><b>{sum(x.get("passed",0) for x in recs):,}</b><span>累计通过条数</span></div>
</div>

<div class="warn"><strong>怎么核</strong>：拿 <code>{html.escape((recs[0].get("commit") or "")[:12])}</code> 这类 commit 去对应仓库，
按 <code>readouts/e5_structural.json</code> 里该仓库的 <code>verification_entries</code> 找到入口文件，本地解包后跑；
你看到的最后几行应当与下面的 <code>out</code> 同义。全树无 <code>.git</code>、环境无 token，是这套判定的前提。</div>
{"".join(cards)}
"""
open(OUT, "w", encoding="utf-8").write(doc)
print(OUT, len(doc))
