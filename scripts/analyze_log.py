#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 Shadowrocket PacketTunnel 日志，输出分流/拦截/DNS/耗电相关统计。

用法：
    python3 scripts/analyze_log.py "/path/to/PacketTunnel-YYYYMMDDHHMMSS.log"

要点（踩过的坑）：
  1. 「规则命中」必须按多行块解析：
         result = <策略/规则集名>,
         ns = <规则集序号>,
         url  = <目标>,
         type = <DIRECT|PROXY|REJECT>,
     不能写 `result = ([^,]+),` —— result 字段自身含逗号（如
     `DOMAIN-SUFFIX,apple.com,苹果服务 # DIRECT`），逐行正则必错。
  2. 判断「配置有没有真的换掉」看 DNS 上游指纹：数 `any send` 打到几个上游、
     有没有 `dns over quic ...#h3`。dns-server 这行配置本身不会出现在日志里。
  3. `route manager skip load rule file => <name>.db` 表示本次没有重新编译，
     配置可能是旧版 —— 结合第 2 点一起看。
  4. `tailscale:` 是可独立开关的一层隧道，不是噪音，耗电分析要单列。
"""
import re
import sys
from collections import Counter, defaultdict

PATH = sys.argv[1]
raw = open(PATH, encoding='utf-8', errors='replace').read()
lines = raw.split('\n')
print(f"文件: {PATH}")
print(f"行数: {len(lines)}")

TS = re.compile(r'^\[(\d\d:\d\d:\d\d\.\d+)\]')
# 抓取 "xxx rule => {" ... "}" 块
block_re = re.compile(r'(?:tcp|udp|http2?|proxy) (?:stream <\d+> )?(?:async )?(?:match |lookup )?rule url? ?=>? ?\{?\n((?:\t.*\n)+)\}')
results = re.findall(r'\tresult = (.*),\n\tns = (\d+),\n\turl = (.*),\n\ttype = (\w+),', raw)
print(f"\n=== 规则命中块数: {len(results)} ===")
name_c = Counter(r[0].split(',')[-1].strip() for r in results)
print("--- 按落地策略/规则集名 ---")
for name, n in name_c.most_common(40):
    print(f"{n:6d}  {name}")

print("\n--- 按命中规则的域名模式(前2字段) ---")
pat_c = Counter(','.join(r[0].split(',')[:2]) for r in results)
for p, n in pat_c.most_common(40):
    print(f"{n:6d}  {p}")

# 按 ns (规则集序号) 统计
ns_c = Counter(r[1] for r in results)
print("\n=== 命中来源 ns 序号 TOP25 ===")
for ns, n in ns_c.most_common(25):
    print(f"{n:6d}  ns={ns}")

# REJECT 明细
print("\n=== REJECT 命中明细 ===")
for p, n in Counter(','.join(r[0].split(',')[:2]) for r in results if r[3] == 'REJECT').most_common(30):
    print(f"{n:6d}  {p}")

# PROXY 明细
print("\n=== PROXY 命中明细 ===")
for p, n in Counter(','.join(r[0].split(',')[:2]) for r in results if r[3] == 'PROXY').most_common(30):
    print(f"{n:6d}  {p}")

# type 统计
types = re.findall(r'\ttype = ([A-Z]+),', raw)
print("\n=== 命中类型 ===")
for t, n in Counter(types).most_common():
    print(f"{n:6d}  {t}")

# REJECT 上下文
print("\n=== REJECT 行样本(前12) ===")
rej = [l for l in lines if 'REJECT' in l]
for l in rej[:12]:
    print("   ", l[:200])

# 时间跨度 & 每分钟规则数
ts = [TS.match(l).group(1) for l in lines if TS.match(l)]
print(f"\n时间跨度: {ts[0]} → {ts[-1]}  共 {len(ts)} 条带时间戳")
minute_c = Counter(t[:5] for t in ts)
print("每分钟日志行数:")
for m in sorted(minute_c):
    print(f"  {m}  {minute_c[m]}")

# DNS
print("\n=== DNS 汇总 ===")
print("  send 目标:", Counter(re.findall(r' to (\S+)\s*$', raw, re.M) and [x for x in re.findall(r'(?:any|system) send (?:ipv4|ipv6) \S+ to (\S+)', raw)]).most_common())
print("  any send 行:", len(re.findall(r' any send ', raw)), " system send 行:", len(re.findall(r' system send ', raw)))
print("  ipv6 send:", len(re.findall(r' send ipv6 ', raw)), " ipv4 send:", len(re.findall(r' send ipv4 ', raw)))
print("  did start:", len(re.findall(r' did start ', raw)), " did finish:", len(re.findall(r' did finish ', raw)))
print("  cancel from:", len(re.findall(r' cancel from ', raw)))
print("  dns over quic:", len(re.findall(r'dns over quic', raw)))
print("  dns over https disconnect:", len(re.findall(r'dns over https <[^>]+> did disconnect', raw)))
for l in [l for l in lines if 'dns over' in l and 'disconnect' in l][:10]:
    print("   ", l[:180])

# 连接耗时
costs = [float(x) for x in re.findall(r'did connect to host => \S+ cost => ([\d.]+) ms', raw)]
if costs:
    costs.sort()
    print(f"\n=== 连接耗时 did connect ({len(costs)} 次) ===")
    print(f"  min {costs[0]:.0f} / p50 {costs[len(costs)//2]:.0f} / p90 {costs[int(len(costs)*0.9)]:.0f} / max {costs[-1]:.0f} ms")
    slow = [c for c in costs if c > 1000]
    print(f"  >1s 的连接: {len(slow)} 次")

# 长连接/断开耗时
dcost = re.findall(r'disconnect \S+ error => (\S+) reason => (\S+) cost => ([\d.]+) ms', raw)
print(f"\n=== 带耗时的 disconnect: {len(dcost)} ===")
for k, v in Counter(x[0] for x in dcost).most_common(10):
    print(f"  {v:6d}  {k}")
for k, v in Counter(x[1] for x in dcost).most_common(10):
    print(f"  {v:6d}  reason={k}")

# 错误
print("\n=== 错误关键字 ===")
for kw in ['ERR_', 'unreachable', 'timeout', 'failed', 'error =>', 'refused', 'reset']:
    n = raw.count(kw)
    print(f"  {kw:15s} {n}")
print("\n失败行样本:")
for l in [l for l in lines if ('unreachable' in l or 'ERR_' in l or 'failed' in l)][:15]:
    print("   ", l[:180])

# tailscale
print("\n=== Tailscale ===")
tls = [l for l in lines if 'tailscale' in l]
print(f"  行数: {len(tls)}")
for l in tls[:20]:
    print("   ", l[:180])

# MITM
print("\n=== MITM ===")
for l in [l for l in lines if 'mitm' in l.lower()][:12]:
    print("   ", l[:200])

# URL Rewrite
print("\n=== URL Rewrite / URL-REGEX ===")
for l in [l for l in lines if 'rewrite' in l.lower() or 'URL-REGEX' in l][:12]:
    print("   ", l[:250])

# 代理节点
print("\n=== 节点/代理 ===")
for l in [l for l in lines if re.search(r'proxy (?:stream|group|node)|server =>|switch', l)][:15]:
    print("   ", l[:200])
