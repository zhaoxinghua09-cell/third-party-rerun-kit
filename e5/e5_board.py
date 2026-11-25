"""生成 E5 实测看板（自包含：无外链资源、无 <a href>，URL 以纯文本给出）。"""
import html
import json
import os
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
STRUCT = os.path.join(ROOT, "e5_20261125", "e5_structural.json")
RUNNER = os.path.join(ROOT, "e5_20261125", "e5_runner.json")
OUT = os.path.join(ROOT, "e5_20261125", "E5外人全量实测看板_20261126.html")

s = json.load(open(STRUCT, encoding="utf-8"))
r = json.load(open(RUNNER, encoding="utf-8"))
su, ru = s["summary"], r["summary"]
recs = r["records"]
by_struct = {x["repo"]: x for x in s["records"]}
passed_total = sum(x.get("passed", 0) for x in recs)

COLOR = {"pass": "#2e7d32", "partial": "#c62828", "no_tests_collected": "#ef6c00",
         "not_runnable": "#b71c1c", "error": "#8e24aa"}
LABEL = {"pass": "合格（passed>0 且 failed=0）", "partial": "真跑有失败",
         "no_tests_collected": "入口在但收集 0 条", "not_runnable": "缺依赖/跑不起来"}


def bar(label, n, total, color):
    pct = (n / total * 100) if total else 0
    return (f'<div class="row"><span class="lb">{html.escape(label)}</span>'
            f'<span class="track"><span class="fill" style="width:{pct:.1f}%;background:{color}"></span></span>'
            f'<span class="num">{n}<i>/{total}</i></span></div>')


rows = []
for x in sorted(recs, key=lambda z: (z["verdict"] != "pass", -z.get("passed", 0))):
    st = by_struct.get(x["repo"], {})
    rows.append(
        "<tr><td class=repo>{repo}</td><td><span class=tag style='background:{c}'>{v}</span></td>"
        "<td class=num2>{p}</td><td class=num2>{f}</td><td class=num2>{sec}</td>"
        "<td class=small>{ent}</td><td class=url>{url}</td></tr>".format(
            repo=html.escape(x["repo"]), c=COLOR.get(x["verdict"], "#555"),
            v=html.escape(x["verdict"]), p=x.get("passed", 0), f=x.get("failed", 0),
            sec=x.get("seconds", ""), ent=html.escape(",".join(st.get("verification_entries", []))),
            url="https://github.com/" + x["repo"]))

dist = "".join(bar(LABEL.get(k, k), v, ru["candidates"], COLOR.get(k, "#555"))
               for k, v in sorted(ru["counts"].items(), key=lambda kv: -kv[1]))
sdist = bar("有可执行入口", su["measurable"], su["probed"], "#2e7d32") + \
        bar("无可执行入口", su["probed"] - su["measurable"], su["probed"], "#9e9e9e")

doc = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>E5 外人全量实测看板 2026-11-26（家机）</title>
<style>
:root{{--ink:#111;--dim:#666;--line:#e3e3e3}}
body{{font:15px/1.6 "Segoe UI",system-ui,sans-serif;color:var(--ink);margin:0;padding:32px 40px;background:#fff}}
h1{{font-size:26px;margin:0 0 4px}} .sub{{color:var(--dim);margin-bottom:26px}}
.kpi{{display:flex;gap:14px;flex-wrap:wrap;margin:0 0 28px}}
.card{{border:1px solid var(--line);border-radius:10px;padding:14px 18px;min-width:150px}}
.card b{{display:block;font-size:30px;line-height:1.1}} .card span{{color:var(--dim);font-size:13px}}
h2{{font-size:17px;margin:30px 0 12px;padding-left:10px;border-left:4px solid #111}}
.row{{display:flex;align-items:center;gap:10px;margin:6px 0}}
.lb{{width:230px;color:#333;font-size:14px}} .track{{flex:1;height:14px;background:#f0f0f0;border-radius:7px;overflow:hidden}}
.fill{{display:block;height:100%}} .num{{width:86px;text-align:right;font-variant-numeric:tabular-nums}}
.num i{{color:var(--dim);font-style:normal;font-size:12px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}}
th{{background:#fafafa;font-weight:600}}
.tag{{color:#fff;border-radius:4px;padding:1px 6px;font-size:11px;white-space:nowrap}}
td.num2{{text-align:right;font-variant-numeric:tabular-nums;width:64px}}
td.url{{font-family:Consolas,monospace;font-size:11px;color:#555;word-break:break-all}}
td.small{{font-size:11px;color:#555}}
.note{{border:1px solid var(--line);border-left:4px solid #c62828;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:14px;background:#fffafa}}
code{{background:#f5f5f5;padding:1px 5px;border-radius:4px;font-size:12px}}
</style>
<h1>E5：GitHub 贡献全部外人角度实测（家机侧）</h1>
<div class="sub">生成 {time.strftime('%Y-%m-%d %H:%M')} · 三账号全量 · 外部持证人执行，未使用仓库写权限 · 与公司机同脚本同判据</div>

<div class="kpi">
  <div class="card"><b>{su['probed']}</b><span>结构探测（全量，分母已由 162 更正）</span></div>
  <div class="card"><b>{su['measurable']}</b><span>有可执行验证入口（测试）</span></div>
  <div class="card"><b>{su.get('selfcheck_only', 0)}</b><span>仅自检脚本（不计合格）</span></div>
  <div class="card"><b>{ru['candidates']}</b><span>真下载真解包真跑</span></div>
  <div class="card"><b>{ru['counts'].get('pass',0)}</b><span>通过 E5 合格线</span></div>
  <div class="card"><b>{passed_total:,}</b><span>实测通过的测试条数</span></div>
</div>

<h2>一、结构层：能不能跑（全量 {su['probed']} 件）</h2>
{sdist}

<h2>二、执行层：真跑了没有（{ru['candidates']} 件）</h2>
{dist}
<div class="note"><strong>两机对照要一起看</strong>：公司机（DESKTOP-IGJBTUB）同脚本跑出 254/48 结构读数，执行层 34 件、26 合格；
本机执行层 {ru['candidates']} 件、{ru['counts'].get('pass',0)} 合格。结构层两机完全一致，执行层读数受环境（Windows symlink、subprocess、git 状态）影响，
<strong>必须两台分别记录，只报一台就是抽样冒充全量</strong>。</div>

<h2>三、逐件读数（{len(recs)} 件）</h2>
<table><thead><tr><th>仓库</th><th>结论</th><th>passed</th><th>failed</th><th>秒</th><th>入口</th><th>直达地址</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>

<h2>四、失败读数（不掩盖）</h2>
<div class="note"><strong>zhaoxinghua09-cell/uibc-core · 2090 passed / 2 failed</strong><br>
失败项：<code>test_resolve_generated.py::test_outside_a_rebase_it_touches_nothing</code>（<code>FileNotFoundError</code>，本机 subprocess 环境）、
<code>test_verify_external_node_report.py::TestItRecomputes::test_quick_run_matches_the_receipt</code>（quick run 与 receipt 不一致）。<br>
对比公司机同仓读数为 2092 passed / 1 failed（<code>FILE COUNT MOVED: receipt 2244, tree 2248</code>）——
<strong>同一仓库、两机不同失败项</strong>，恰好证明"外人复跑"必须多环境做。</div>
<div class="note"><strong>zhaoxinghua09-cell/agent-control-standard · 794 passed / 20 failed</strong>（触发 maxfail=20 停止）<br>
集中在 symlink 拒绝、roadmap sync 入队；Windows 无 POSIX symlink 语义 + 本地 git 状态差异。</div>

<h2>五、复现</h2>
<p class="small"><code>python e5_build_manifest.py</code> → <code>python e5_probe.py</code> →
<code>python e5_run.py --repos &lt;owner/repo ...&gt;</code> → <code>python e5_merge.py</code> → <code>python e5_board.py</code>。
原件：<code>e5_20261125/e5_structural.json</code>、<code>e5_20261125/e5_runner.json</code>、<code>artifact_manifest_20261125.json</code>。</p>
"""
open(OUT, "w", encoding="utf-8").write(doc)
print(OUT, len(doc))
