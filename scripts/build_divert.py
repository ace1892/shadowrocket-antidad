#!/usr/bin/env python3
"""
生成 dist/divert.conf —— 自建分流订阅（派生自 johnshall 的 lazy_group.conf）

── 为什么需要这个文件 ────────────────────────────────────────────────
上游 lazy_group.conf 里有 4 条 RULE-SET 引用写的是 **Quantumult X 目录**：

    line 321  rule/QuantumultX/Apple/Apple.list    → 苹果服务
    line 326  rule/QuantumultX/WeChat/WeChat.list  → DIRECT
    line 334  rule/QuantumultX/Global/Global.list  → PROXY
    line 335  rule/QuantumultX/China/China.list    → DIRECT

那 4 个文件里写的是 QX 方言（HOST-SUFFIX / HOST-KEYWORD / HOST-WILDCARD /
IP6-CIDR），**小火箭不识别** → 规则一条都不生效，而且**不报错、无任何可见症状**。

判断「漏改」而非「设计」的指纹（三条互相印证）：
  · 同一文件里 35 条 `rule/Shadowrocket/...` 对 4 条 `rule/QuantumultX/...`
  · 该文件自己的注释（第 234/235 行）示范的就是 `rule/Shadowrocket/...` 路径
  · 上游 issue Johnshall#206「为什么个别分流规则是QuantumultX？」维护者答「的确是这样的」

订阅是远程的，改不了源文件，所以派生一份自己的、定在这里修。
分流之外的东西（广告拦截）不在本文件 —— 见仓库 modules/antidad-*.module。

── 做的三件事 ────────────────────────────────────────────────────────
1. [改] `rule/QuantumultX/<组>/<名>.list` → `rule/Shadowrocket/<组>/<名>.list`
   并补上 `DOMAIN-SET` 引用。**这一步不能省**：小火箭版规则集是「拆开」的，
   `*.list` 只剩非域名部分（UA / IP-CIDR / DOMAIN-KEYWORD），域名全在
   `*_Domain.list` 里。只换路径会丢掉几千条域名且不报错。
2. [删] `Global` 那条：它与文件末尾的 `FINAL,PROXY` 近似等价，补回去只多下
   ~556 KB、多解析约 3.5 万条（`Global.list` 6.2 KB / 201 条 +
   `Global_Domain.list` 550 KB / 34,903 条）。开关见 KEEP_GLOBAL。
3. 头部插入生成说明 + 修正明细。

── 断言（任一不过即退出非零，CI 拦住） ────────────────────────────────
  A. 输出里 `rule/QuantumultX` 必须为 0
  B. [General] / [Proxy Group] / [Rule] 三段必须在；[Proxy] 段必须为空
  C. 公开仓库红线：全文不得出现节点协议 scheme 或凭据字段
  D. 被改写的 `X.list` 必须可达；`X_Domain.list` 的存在性与期望表比对，
     上游结构变了就报错，而不是静默少补一条
  E. 实际改写条数记入输出，供人复核

用法：
  python3 scripts/build_divert.py            # 写入 dist/divert.conf
  python3 scripts/build_divert.py --check    # 只校验是否与磁盘一致，不写（CI 用）
"""
from __future__ import annotations

import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / "dist" / "divert.conf"

CST = timezone(timedelta(hours=8))

REPO = "ace1892/shadowrocket-antidad"

# ------------------------------------------------------------
# 上游。jsDelivr 优先（国内可达），raw 兜底。
# 注意：上游同时有 release / master 两个分支、内容一致，任一可用即可。
# ------------------------------------------------------------
UPSTREAM_URLS = (
    "https://cdn.jsdelivr.net/gh/Johnshall/Shadowrocket-ADBlock-Rules-Forever@release/lazy_group.conf",
    "https://raw.githubusercontent.com/Johnshall/Shadowrocket-ADBlock-Rules-Forever/release/lazy_group.conf",
    "https://cdn.jsdelivr.net/gh/Johnshall/Shadowrocket-ADBlock-Rules-Forever@master/lazy_group.conf",
)
UPSTREAM_LABEL = "Johnshall/Shadowrocket-ADBlock-Rules-Forever @release/lazy_group.conf"

# 探测 `X_Domain.list` 是否存在时走的镜像（只用于探测，不写进配置里）。
# 走 jsDelivr 是因为它对本地和 CI 都可达；写进配置的仍是上游原本的 raw 地址。
BM7_MIRROR = "https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@master/rule/Shadowrocket"

# ------------------------------------------------------------
# 期望表：哪个组的域名被拆进了 `X_Domain.list`。
#
# 为什么要有这张表（而不是「探测说没有就没有」）：探测会因网络抖动返回未知，
# 那时若默认「没有」就会静默漏补一条 DOMAIN-SET —— 正好是本次要修的毛病。
# 有期望表就能区分三种情况：
#   探测=存在 & 期望=有 → 正常补
#   探测=不存在 & 期望=有 → **上游结构变了，报错**（不许静默降级）
#   探测=未知 & 期望=有 → 按期望补 + 警告
# 实测（2026-09-29）：WeChat 是唯一没有 `_Domain.list` 的 ——
# 它的 `WeChat.list` 33 行里已经含全部 29 条 DOMAIN/DOMAIN-SUFFIX，一行就够。
# ------------------------------------------------------------
EXPECT_DOMAIN_LIST = {
    "Apple": True,
    "China": True,
    "WeChat": False,
    "Global": True,
}

# Global 那条不补：与文件末尾 `FINAL,PROXY` 近似等价。
# 改成 True 会把 Global 也修好（收益：境外域名解析到 CN IP 时不再被 GEOIP,CN 误判直连；
# 代价：每次配置更新多下 ~556 KB、多解析 35,784 条）。
KEEP_GLOBAL = False

# ------------------------------------------------------------
# [General] 调优：DNS 上游精简 + 关掉 DoH 的 HTTP/3 自动升级
# （2026-09-29 新增；依据手册 §通用参数 + 一份真实 PacketTunnel 日志的定量结果）
#
# 依据一 —— 手册 §通用参数「DNS覆写 dns-server」：
#   「DNS 覆写支持同时添加多个地址，Shadowrocket 采用 **并行查询** 的方式进行解析请求，
#     最先返回的结果将被采用」
#   ⇒ 上游写了 4 个上游。实测（3 分 53 秒日志）：**68 个逻辑查询实际发出 182 次请求**
#     （放大 2.68 倍，其中 20 个查询同时打满 4 家、1 个打了 8 家）。
#     砍到 2 个 ≈ 直接砍掉一半的 DNS 收发与系统唤醒。
#
# 依据二 —— 手册同段：
#   「有些 dns over https 支持 http3，所以将会尝试查询，如果支持就切换到 http3，
#     可在 doh 链接后面加上 #no-h3 关闭」
#   ⇒ 上游的 DoH 会被自动升级到 HTTP/3。实测日志里 `dns over quic …#h3` 反复
#     `ERR_IDLE_CLOSE`（空闲断开又重建 = QUIC 握手 + TLS 握手）。加 `#no-h3` 后
#     固定走 TCP/TLS，连接可长复用。**这是手册给的官方解法，不是偏方。**
#
# 刻意 **不** 动的（避免过度调参、也避免把用户没要求的策略强塞进去）：
#   · `ipv6` —— 实测 AAAA 只占 DNS 请求的 2.2%（`prefer-ipv6 = false` 时不主动查 AAAA），
#     关它收益很小。想关在 UI 里点掉即可（手册给的微信加载异常解法就是关它）。
#   · `fallback-dns-server` / `hijack-dns` / `block-quic` / `dns-direct-*` —— 保持上游设计意图。
# ------------------------------------------------------------
TUNE_DNS = True

# 本档要写进去的 dns-server：一个 DoH（防污染，关 h3）+ 一个原生 UDP（最快）
DNS_SERVER_OVERRIDE = "https://doh.pub/dns-query#no-h3,223.5.5.5"

# 上游 dns-server 的实测基线（2026-09-29 读取）。上游一旦改动会告警，
# 而不是静默覆盖 —— 与 EXPECT_DOMAIN_LIST 同一个思路。
UPSTREAM_DNS_BASELINE = ("https://doh.pub/dns-query,"
                         "https://dns.alidns.com/dns-query,223.5.5.5,119.29.29.29")

# ------------------------------------------------------------
# 公开仓库红线
# ------------------------------------------------------------
REQUIRED_SECTIONS = ("[General]", "[Proxy Group]", "[Rule]")
PROXY_SECTION = "[Proxy]"

SECRET_RES = (
    re.compile(r"(?<![a-z])(vmess|vless|trojan|ss|ssr|hysteria2?|hy2|tuic|snell|socks|wireguard)://", re.I),
    re.compile(r"\b(obfs|psk|password|passwd|uuid|auth_key|private[-_]key)\s*=", re.I),
)

QX_PATH_RE = re.compile(r"/rule/QuantumultX/(?P<grp>[^/,\s]+)/(?P<name>[^/,\s]+)\.list")

TS_MARKER = "生成于"


# ------------------------------------------------------------
# 取文
# ------------------------------------------------------------
def fetch_text(urls, retries: int = 3) -> str:
    """依次试候选 URL，先 urllib 后 curl。全失败才抛。"""
    last = None
    for url in urls:
        for _ in range(retries):
            try:
                req = urllib.request.Request(
                    url, headers={"Cache-Control": "no-cache", "User-Agent": "antidad-build"})
                with urllib.request.urlopen(req, timeout=45) as r:
                    body = r.read().decode("utf-8", "replace")
                if body.strip():
                    return body
            except Exception as e:                       # noqa: BLE001
                last = e
            try:
                out = subprocess.run(["/usr/bin/curl", "-sL", "--max-time", "45", url],
                                     capture_output=True, check=True)
                if out.stdout.strip():
                    return out.stdout.decode("utf-8", "replace")
            except Exception as e:                       # noqa: BLE001
                last = e
    raise RuntimeError(f"拉取上游失败（{len(urls)} 个候选 × {retries} 次）：{last}")


def probe(url: str):
    """探测 URL 是否存在。返回 True / False(404) / None(网络未知，不下判断)。"""
    for _ in range(3):
        try:
            req = urllib.request.Request(
                url, headers={"Cache-Control": "no-cache", "User-Agent": "antidad-build"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
        except Exception:                                # noqa: BLE001
            pass
        try:
            out = subprocess.run(
                ["/usr/bin/curl", "-sL", "-o", "/dev/null", "-w", "%{http_code}",
                 "--max-time", "30", url],
                capture_output=True, check=True)
            code = out.stdout.decode("utf-8", "replace").strip()
            if code.endswith("200"):
                return True
            if code.endswith("404"):
                return False
        except Exception:                                # noqa: BLE001
            pass
    return None


# ------------------------------------------------------------
# 改写
# ------------------------------------------------------------
def rewrite(lines, allow_probe: bool = True):
    """把 QX 路径改成小火箭路径，并补 DOMAIN-SET。

    返回 (新行列表, changes, warnings)；changes 每项是
    (组, 名, 策略, 结果描述)。
    """
    out, changes, warnings = [], [], []
    for raw in lines:
        line = raw.rstrip("\n")
        s = line.strip()

        if not s.startswith("RULE-SET,"):
            out.append(line)
            continue

        fields = [f.strip() for f in s.split(",")]
        if len(fields) < 3:
            out.append(line)
            continue
        url, policy = fields[1], fields[2]

        m = QX_PATH_RE.search(url)
        if not m:
            out.append(line)                             # 已经是小火箭路径，原样保留
            continue

        grp, name = m.group("grp"), m.group("name")
        new_url = url.replace("/rule/QuantumultX/", "/rule/Shadowrocket/")
        dom_url = new_url.replace(f"/{name}.list", f"/{name}_Domain.list")

        if grp == "Global" and not KEEP_GLOBAL:
            out.append(f"# [已删] 上游指向 QuantumultX/{grp}/{name}.list —— 与文件末尾 "
                       f"FINAL,PROXY 近似等价，补回去只多下 ~556 KB / 多解析约 3.5 万条。")
            out.append(f"# 如需恢复，在 build_divert.py 里把 KEEP_GLOBAL 改成 True。")
            out.append(f"# RULE-SET,{new_url},{policy}")
            changes.append((grp, name, policy, "删除（≈FINAL,PROXY）"))
            continue

        # 期望值：表里没有 = 上游新增了条目，交给人确认
        if name in EXPECT_DOMAIN_LIST:
            expect = EXPECT_DOMAIN_LIST[name]
        else:
            expect = None
            warnings.append(f"{grp}/{name} 不在 EXPECT_DOMAIN_LIST 里（上游新增？），"
                            f"是否补 DOMAIN-SET 由探测结果决定，请人工确认一次。")

        # 基础文件必须可达
        if allow_probe:
            st = probe(f"{BM7_MIRROR}/{grp}/{name}.list")
            if st is False:
                raise RuntimeError(
                    f"{grp}/{name}.list 在小火箭目录下不存在（HTTP 404）—— "
                    f"上游目录结构变了，请人工核对后再改脚本。")
            if st is None:
                warnings.append(f"{grp}/{name}.list 可达性探测失败（网络未知），按可达处理。")

        out.append(f"RULE-SET,{new_url},{policy}")

        need_dom = expect
        if allow_probe:
            dst = probe(f"{BM7_MIRROR}/{grp}/{name}_Domain.list")
            if expect is True and dst is False:
                raise RuntimeError(
                    f"{grp}/{name}_Domain.list 探测为 404，但期望表说它应该有 —— "
                    f"上游结构变了，**不能静默少补一条 DOMAIN-SET**，请人工核对。")
            if expect is False and dst is True:
                warnings.append(f"{grp}/{name}_Domain.list 现在存在了（期望表说没有），"
                                f"已按存在处理，请更新 EXPECT_DOMAIN_LIST。")
            if expect is None:
                need_dom = dst is True
            elif dst is None and expect is True:
                warnings.append(f"{grp}/{name}_Domain.list 探测失败（网络未知），"
                                f"按期望表补上 DOMAIN-SET。")

        if need_dom:
            out.append(f"DOMAIN-SET,{dom_url},{policy}")
            changes.append((grp, name, policy, "RULE-SET + DOMAIN-SET"))
        else:
            changes.append((grp, name, policy, "仅 RULE-SET（上游无 _Domain.list）"))

    return out, changes, warnings


def tune_general(lines):
    """只改 [General] 段里的 `dns-server` 一行，其余参数一律原样保留。

    返回 (新行列表, dns_note, warnings)。
    dns_note 为 None 表示本次没做任何 DNS 改动（TUNE_DNS=False 或上游没这行）。
    """
    if not TUNE_DNS:
        return lines, None, []

    out, warnings = [], []
    section, done, upstream_val = None, False, None

    for raw in lines:
        line = raw.rstrip("\n")
        s = line.strip()

        if s.startswith("["):
            section = s
            out.append(line)
            continue

        # 只在 [General] 段内动手，且精确匹配 `dns-server`（不能误伤
        # `direct-dns-server` / `fallback-dns-server` / `proxy-dns-server`）
        if section != "[General]" or not re.match(r"^dns-server\s*=", s):
            out.append(line)
            continue

        upstream_val = s.split("=", 1)[1].strip()
        if upstream_val != UPSTREAM_DNS_BASELINE:
            warnings.append(
                "上游 dns-server 与基线不一致（上游改过？）—— 仍按本档设定覆盖，请人工确认一次：\n"
                f"        基线：{UPSTREAM_DNS_BASELINE}\n"
                f"        上游：{upstream_val}")
        out.append(f"# 上游原值：dns-server = {upstream_val}")
        out.append("# 调优依据：手册 §通用参数「dns-server 支持多地址，采用并行查询」"
                   "＋「doh 支持 http3 会切换，可在链接后加 #no-h3 关闭」")
        out.append(f"dns-server = {DNS_SERVER_OVERRIDE}")
        done = True

    if not done:
        warnings.append("上游 [General] 段里找不到 dns-server 行 —— 结构变了，"
                        "DNS 调优未生效，请人工核对。")
        return lines, None, warnings

    note = (f"dns-server 上游 {len(upstream_val.split(','))} 个 → "
            f"{len(DNS_SERVER_OVERRIDE.split(','))} 个（并行查询减半）"
            f"＋关掉 DoH 的 HTTP/3 自动升级（#no-h3）")
    return out, note, warnings


def make_header(ts: str, changes, dns_note=None) -> str:
    detail = "\n".join(f"#     {g:8s} → {p:8s} {r}" for g, n, p, r in changes) \
             or "#     （上游已无 Quantumult X 引用）"

    dns_block = ""
    if dns_note:
        dns_block = f"""#
# 第二件事 —— [General] 段里的 DNS 调优：
#   {dns_note}
#   依据：手册 §通用参数 ——「dns-server 支持同时添加多个地址，Shadowrocket 采用
#         并行查询的方式进行解析请求，最先返回的结果将被采用」；同段「有些
#         dns over https 支持 http3，所以将会尝试查询，如果支持就切换到
#         http3，可在 doh 链接后面加上 #no-h3 关闭」。
#   实测（3 分 53 秒的真实 PacketTunnel 日志）：68 个逻辑查询实际发出 182 次
#   请求（放大 2.68 倍，20 个查询打满 4 家）；DoH 被自动升级到 HTTP/3 后反复
#   ERR_IDLE_CLOSE 断开重连（每次重连 = QUIC 握手 + TLS 握手）。
#   本档把上游 4 个上游砍到 2 个，并关掉 DoH 的 h3 自动升级。
#   上游原值保留在 [General] 段里的注释行，便于回溯。
"""

    n_things = "两" if dns_note else "一"
    return f"""# ==========================================================================
# 自建分流订阅 · 派生自 johnshall 的 lazy_group.conf
# 本文件由 scripts/build_divert.py {TS_MARKER} {ts} (UTC+8)
# 不要直接改这里 —— 改 scripts/build_divert.py 然后重新构建。
# 上游：{UPSTREAM_LABEL}
#
# 本档做{n_things}件事，都针对「上游配置自身的缺陷」，不掺任何个人分流策略。
#
# 第一件事 —— 修掉上游 4 条「写错客户端方言」的 RULE-SET 引用：
#   上游那 4 条指向 Quantumult X 的目录（该仓库按客户端分目录），里面写的是
#   Quantumult X 方言（HOST-SUFFIX / HOST-KEYWORD / HOST-WILDCARD / IP6-CIDR），
#   小火箭不识别 → 规则一条都不生效，而且**不报错、无可见症状**。
#   （该文件自己的注释第 234/235 行示范的就是小火箭目录的路径，属漏改。）
#
#   修正明细：
{detail}
{dns_block}#
# ⚠️ 小火箭版规则集是「拆开」的：*.list 只剩非域名部分（UA / IP-CIDR /
#    DOMAIN-KEYWORD），域名全在 *_Domain.list，必须 RULE-SET + DOMAIN-SET
#    两条一起用。只换路径会丢掉几千条域名，同样不报错。
#
# 反广告不在本文件 —— 见仓库 modules/antidad-*.module。
# 仓库：https://github.com/{REPO}
# ==========================================================================

"""


# ------------------------------------------------------------
# 断言
# ------------------------------------------------------------
def active_lines(text: str) -> list:
    """生效行（非注释、非空）。断言只看这些 —— 上游的文档注释里满是
    `password=密码` 这种格式说明，把注释算进去会全线误报。"""
    return [l.strip() for l in text.splitlines()
            if l.strip() and not l.strip().startswith("#")]


def check_output(text: str, changes) -> list:
    """返回问题列表（空 = 通过）。"""
    problems = []
    active = active_lines(text)

    n_qx = sum(1 for l in active if "rule/QuantumultX" in l)
    if n_qx:
        problems.append(f"生效行里仍有 {n_qx} 条 QuantumultX 引用（应为 0）")

    for sec in REQUIRED_SECTIONS:
        if f"\n{sec}" not in "\n" + text:
            problems.append(f"缺少章节 {sec}")

    # [Proxy] 段体必须为空（上游只放注释）。这条是隐私闸门：
    # 本仓库是公开的，一旦上游把节点信息塞进来，这里必须拦住。
    body, inside = [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            inside = s == PROXY_SECTION
            continue
        if inside and s and not s.startswith("#"):
            body.append(s)
    if body:
        problems.append(
            f"[Proxy] 段里出现 {len(body)} 行非注释内容（公开仓库不允许带节点信息）：{body[:3]}")

    for rx in SECRET_RES:
        for l in active:
            hit = rx.search(l)
            if hit:
                problems.append(f"生效行命中凭据/协议特征「{hit.group(0)}」：{l[:60]}")
                break

    if not changes:
        problems.append("上游已无 Quantumult X 引用 —— 本派生物可能已无存在意义，请人工确认")

    # DNS 调优必须精确落地（不只是「有 dns-server 行」）
    if TUNE_DNS:
        want = f"dns-server = {DNS_SERVER_OVERRIDE}"
        got = [l for l in active if l.startswith("dns-server")]
        if got != [want]:
            problems.append(f"dns-server 与预期不符：\n        期望 {want!r}\n        实际 {got!r}")
        # 常量自检：每个 DoH 项都必须带 #no-h3，否则会被自动升到 HTTP/3
        # （这条拦的是「改常量时忘了加」—— 输出的整行比对拦不到常量本身的错）
        for item in DNS_SERVER_OVERRIDE.split(","):
            if item.strip().startswith("https://") and "#no-h3" not in item:
                problems.append(f"DNS_SERVER_OVERRIDE 里的 DoH 项缺 #no-h3：{item.strip()}")

    return problems


def main() -> int:
    check_only = "--check" in sys.argv
    no_probe = "--no-probe" in sys.argv

    print(f"拉取上游：{UPSTREAM_LABEL}")
    text = fetch_text(UPSTREAM_URLS)
    print(f"  上游 {len(text.encode('utf-8'))} 字节 / {len(text.splitlines())} 行")

    lines = text.splitlines()
    body, changes, warnings = rewrite(lines, allow_probe=not no_probe)
    body, dns_note, dns_warnings = tune_general(body)
    warnings.extend(dns_warnings)

    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    content = make_header(ts, changes, dns_note) + "\n".join(body) + "\n"

    print("\n改写明细：")
    for grp, name, policy, result in changes:
        print(f"  {grp:8s} → {policy:6s} {result}")
    if not changes:
        print("  （无）")
    if dns_note:
        print(f"  [General] {dns_note}")
    for w in warnings:
        print(f"  ⚠ {w}")

    problems = check_output(content, changes)
    if problems:
        print("\n自检未通过：")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    extra = "、dns-server 已按预期改写" if TUNE_DNS else ""
    print(f"\n自检通过：QX 引用 0 条、三段完整、[Proxy] 段为空、无凭据特征{extra}。")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 幂等：比较时忽略生成时间那一行
    def normalized(t: str) -> str:
        return "\n".join(l for l in t.splitlines() if TS_MARKER not in l)

    if OUT_FILE.exists() and normalized(OUT_FILE.read_text(encoding="utf-8")) == normalized(content):
        print(f"= {OUT_FILE.name} 无变化")
        return 0
    if check_only:
        print(f"!! {OUT_FILE.name} 与脚本输出不一致。请运行 python3 scripts/build_divert.py 重新生成。")
        return 1
    OUT_FILE.write_text(content, encoding="utf-8")
    print(f"+ {OUT_FILE.relative_to(ROOT)} 已生成（{len(content.encode('utf-8'))} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
