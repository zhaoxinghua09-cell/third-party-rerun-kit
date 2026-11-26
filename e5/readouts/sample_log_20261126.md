# E5 外部审查抽样日志（10%）

抽样规则：34 件严格合格中按 passed 分层各取 1 件（A 多 / B 中 / C 少 / D 薄证据），共 4 件 = 11.8%。
每件从 commit 锚点重新下载 zipball（无 .git、无凭证），完整 stdout/stderr 存同目录 .log，不截断。

## 本机环境快照

```json
{
 "python": "3.13.18",
 "platform": "Windows-10-10.0.19045-SP0",
 "machine": "DESKTOP-IGJBTUB",
 "pytest": "9.2.0",
 "setuptools": "84.2.1",
 "requests": "2.34.2",
 "node": "v22.23.2",
 "npm": null
}
```

## 抽样结果

| 档 | 仓库 | commit | 预期 passed | 实测 passed | exit | 秒 | 字节 |
|---|---|---|---|---|---|---|---|

## 逐件输出尾

### A zhaoxinghua09-cell/lgd-xverify `7ca1b83a496d`

命令：`python -m pytest tests -q -p no:cacheprovider`

```
............................                                             [100%]
28 passed in 5.96s
```

### B zhaoxinghua09-cell/lgd-skeleton `f3aac86e9c56`

命令：`python -m pytest tests -q -p no:cacheprovider`

```
..............                                                           [100%]
14 passed in 5.05s
```

### C zhaoxinghua09-cell/evaluation-evidence `387ead9c0d42`

命令：`python -m pytest tests -q -p no:cacheprovider`

```
.....                                                                    [100%]
5 passed in 0.05s
```

### D LGD-Eval/skill-scout `aa26f4195d8f`

命令：`python -m pytest tests -q -p no:cacheprovider`

```
no tests ran in 0.01s
```
