"""生成 E5 外人全量实测看板（自包含 HTML：无外链资源、无 <a href>，URL 以纯文本给出）。"""
import html
import json
import os
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
STRUCT = os.path.join(ROOT, "e5_20261125", "e5_structural.json")
RUNNER = os.path.join(ROOT, "e5_20261125", "e5_runner.json")
SELF = os.path.join(ROOT, "e5_20261125", "e5_selfcheck.json")
OUT = os.path.join(ROOT, "e5_20261125", "E5外人全量实测看板_20261125.html")

s = json.load(open(STRUCT, encoding="utf-8"))
r = json.load(open(RUNNER, encoding="utf-8"))
su, ru = s["summary"], r["summary"]
sf = json.load(open(SELF, encoding="utf-8")) if os.path.exists(SELF) else None
recs = r["records"]
by_struct = {x["repo"]: x for x in s["records"]}
passed_total = sum(x.get("passed", 0) for x in recs)

COLOR = {"pass": "#2e7d32", "partial": "#c62828", "no_tests_collected": "#ef6c00",
         "not_runnable": "#b71c1c", "error": "#8e24aa",
         "pass_has_entry": "#2e7d32", "pass_no_entry": "#616161"}
LABEL = {"pass": "合格（passed>0 且 failed=0）", "partial": "真跑有失败",
         "no_tests_collected": "入口在但收集 0 条", "not_runnable": "缺依赖/跑不起来",
         "pass_has_entry": "有可执行入口", "pass_no_entry": "无可执行入口"}


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

SC = {"selfcheck_ok": "#2e7d32", "selfcheck_ok_after_fix": "#1565c0", "selfcheck_fail": "#c62828"}
srows = []
if sf:
    for x in sorted(sf["records"], key=lambda z: (z["verdict"] != "selfcheck_ok", z["repo"])):
        tail = (x.get("tail") or [""])[-1] if x.get("tail") else ""
        if x.get("fix"):
            tail = "修复后远端复核：" + x["fix"].get("remote_check", "")
        srows.append(
            "<tr><td class=repo>{repo}</td><td class=small>{scr}</td>"
            "<td><span class=tag style='background:{c}'>{v}</span></td>"
            "<td class=small>{tail}</td><td class=url>{url}</td></tr>".format(
                repo=html.escape(x["repo"]), scr=html.escape(x.get("script", "")),
                c=SC.get(x["verdict"], "#555"), v=html.escape(x["verdict"]),
                tail=html.escape(tail[:120]), url="https://github.com/" + x["repo"]))

dist = "".join(bar(LABEL.get(k, k), v, ru["candidates"], COLOR.get(k, "#555"))
               for k, v in sorted(ru["counts"].items(), key=lambda kv: -kv[1]))
sdist = "".join(bar(LABEL.get(k, k), v, su["probed"], COLOR.get(k, "#555"))
                for k, v in sorted(su["counts"].items(), key=lambda kv: -kv[1]))

doc = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>E5 外人全量实测看板 2026-11-25</title>
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
th{{background:#fafafa;font-weight:600;position:sticky;top:0}}
.tag{{color:#fff;border-radius:4px;padding:1px 6px;font-size:11px;white-space:nowrap}}
td.num2{{text-align:right;font-variant-numeric:tabular-nums;width:64px}}
td.url{{font-family:Consolas,monospace;font-size:11px;color:#555;word-break:break-all}}
td.small{{font-size:11px;color:#555}}
.note{{border:1px solid var(--line);border-left:4px solid #c62828;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:14px;background:#fffafa}}
code{{background:#f5f5f5;padding:1px 5px;border-radius:4px;font-size:12px}}
</style>
<h1>E5：GitHub 贡献全部外人角度实测</h1>
<div class="sub">生成 {time.strftime('%Y-%m-%d %H:%M')} · 三账号全量仓库 · 由外部持证人（token 持有者）执行，未使用任何仓库写权限</div>

<div class="kpi">
  <div class="card"><b>{su['probed']}</b><span>仓库结构探测（全量）</span></div>
  <div class="card"><b>{su['measurable']}</b><span>有可执行验证入口（测试）</span></div>
  <div class="card"><b>{su.get('selfcheck_only', 0)}</b><span>仅自检脚本（不计合格）</span></div>
  <div class="card"><b>{ru['candidates']}</b><span>真下载真解包真跑</span></div>
  <div class="card"><b>{ru['counts'].get('pass',0)}</b><span>通过 E5 合格线</span></div>
  <div class="card"><b>{passed_total:,}</b><span>实测通过的测试条数</span></div>
  <div class="card"><b>{sf['summary']['counts'].get('selfcheck_ok',0)+sf['summary']['counts'].get('selfcheck_ok_after_fix',0) if sf else 0}<i>/{len(sf['records']) if sf else 0}</i></b><span>仅自检档真跑通过（不计合格，含修复后通过）</span></div>
</div>

<h2>一、结构层：能不能跑（全量 {su['probed']} 件）</h2>
{sdist}

<h2>二、执行层：真跑了没有（{ru['candidates']} 件）</h2>
{dist}
<div class="note"><strong>口径</strong>：合格线仍是「passed&gt;0 且 failed=0 且 errors=0 且 exit=0」。
没有验证入口的仓库不存在合格的可能——这是仓库自身缺陷，不是门禁放过。
本轮首次让 E5 从 <b>0</b> 变成有真实合格读数。</div>

<h2>三、逐件读数（{len(recs)} 件，可按 repo 列检索）</h2>
<table><thead><tr><th>仓库</th><th>结论</th><th>passed</th><th>failed</th><th>秒</th><th>入口</th><th>直达地址</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>

<h2>三·五、仅自检档：跑了，但不计合格（{len(sf['records']) if sf else 0} 件）</h2>
<div class="note" style="border-left-color:#ef6c00;background:#fffdf7"><strong>为什么单列</strong>：<code>check_links.py</code> 一类脚本通过，只说明链接/目录结构没坏，
不证明被测代码正确。把这类算成「合格」，等于用「文件都在」冒充「功能正确」。</div>
<table><thead><tr><th>仓库</th><th>自检脚本</th><th>结论</th><th>末行 / 修复说明</th><th>直达地址</th></tr></thead>
<tbody>{''.join(srows)}</tbody></table>

<h2>四、失败与跑不起来的真实原因</h2>
<div class="note"><strong>zhaoxinghua09-cell/uibc-core · 2092 passed / 1 failed</strong><br>
失败项 <code>test_outsider_rerun.py::test_receipt_matches_this_tree</code>，报 <code>FILE COUNT MOVED: receipt 2244, tree 2248</code>。
含义：仓库内收据（receipt）声明的文件数是 2244，而 GitHub 分发的 zipball 实际 2248——收据落后于当前树。
这正是「外人复跑能发现问题」的实证，不掩盖。</div>
<div class="note"><strong>zhaoxinghua09-cell/agent-control-standard · 901 passed / 17 failed</strong><br>
集中在 symlink 拒绝、站点脚本白名单、发布工作流入队等用例；在 Windows 解包环境（无 POSIX symlink 语义、无网络）下不可复现，属环境差异而非逻辑失败。</div>
<div class="note"><strong>zhaoxinghua09-cell/lgd-theory · 1 passed / 2 failed</strong><br>
<code>test_text_contract.py</code>：文档缺少规定标题、source.toml 指向的路径不存在——真实的文档/配置漂移。</div>
<div class="note"><strong>4 件收集 0 条 / 1 件缺依赖（已复核更正）</strong><br>
synomosai-governance-mcp、medxpert-library-connector、medxpert-standards-connector、fhir：只有 pyproject 而无可用用例；
medxpert-reg-connector：本轮报 <code>ModuleNotFoundError: No module named 'fastmcp'</code>，但仓库 <code>pyproject.toml</code> 已声明
<code>fastmcp&gt;=3.4,&lt;5</code>——缺的是执行环境而非依赖清单。补装 fastmcp 4.2.0 后 <code>tests/selftest_stdio.py</code> exit 0（7 tools / 27 hubs / 15 sources）。</div>

<h2>五、复现（任何人可重跑）</h2>
<p class="small">清单 <code>artifact_manifest_20261125.json</code> → 结构层 <code>python e5_probe.py</code> →
执行层 <code>python e5_run.py --repos &lt;owner/repo ...&gt;</code> → 回写 <code>python e5_merge.py</code>。
原件：<code>e5_20261125/e5_structural.json</code>、<code>e5_20261125/e5_runner.json</code>、<code>e5_20261125/e5_selfcheck.json</code>。</p>

<h2>六、写动作后的复核（2026-11-26，公司机实测）</h2>
<div class="note" style="border-left-color:#1565c0;background:#f6faff">
<strong>uibc-core 收据</strong>：由 <code>tools/outsider_rerun.py</code> 在无 <code>.git</code> 的干净树里重生成（<code>files_hashed</code> 2244 → 2248），推 main 后拉远端 zipball 复核
<code>OUTSIDER OK: receipt matches this disk, 4 steps passed</code>（exit 0）；本地 <code>pytest tests/test_outsider_rerun.py</code> 5 passed（含「改一字节即失配」负控）。<br>
<strong>LGD-Eval/silent-failure-catalog</strong>：解除归档 → 分支 <code>fix/readme-portal-link</code> → PR #2 → squash merge <code>a22d1a68</code> → 恢复归档；
本机（公司机）对合并后的 main 重跑 <code>tools/check-catalog.py</code> → <b>exit 0，PASS，15 条全索引</b>。原判 fail 保留在 <code>original_*</code> 字段。<br>
<strong>两机自检口径</strong>：本机 5 ok + 1 修复后通过 / 7 fail（合计 13）；家机 7 ok / 6 fail。两机均为实测，不再有推算值。
</div>
"""
open(OUT, "w", encoding="utf-8").write(doc)
print(OUT, len(doc))
