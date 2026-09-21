#!/usr/bin/env python3
"""
生成 modules/*.module

输入：
  sources.json   —— 上游规则源登记表（id / 类型 / URL / 实测基线）
  whitelist.txt  —— 误杀放行名单（人可读，改动只需动它）

输出：
  modules/antidad-full.module
  modules/antidad-lite.module
  modules/antidad-strict.module

设计要点：
  1. 模块的 [Rule] 段支持 RULE-SET / DOMAIN-SET 远程引用（社区实证，官方手册无明文）。
     所以本仓库**不需要**把 5.7 MB 域名集存进来 —— 模块直接引用上游，体积只有几 KB。
  2. 白名单必须排在最前（规则自上而下、命中即停）。
  3. 引用类型不能写错：域名集必须 DOMAIN-SET，关键词/IP 集必须 RULE-SET。

用法：
  python3 scripts/build.py            # 写入 modules/
  python3 scripts/build.py --check    # 只校验是否与磁盘一致，不写（CI 用）
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "sources.json"
WHITELIST_FILE = ROOT / "whitelist.txt"
MODULES_DIR = ROOT / "modules"

REPO = "ace1892/shadowrocket-antidad"
BRANCH = "main"
ICON = ("https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Advertising.png")

# ------------------------------------------------------------
# 档位定义。sources 的顺序 = 写进模块的顺序，必须是「先放行、后拦截」。
# ------------------------------------------------------------
PROFILES = [
    {
        "file": "antidad-full.module",
        "name": "反广告 · 整合版",
        "desc": "blackmatrix7 域名集 + 关键词/IP + anti-AD 双源合并 · 纯 REJECT · 不需要 MITM",
        "sources": ["antiad", "bm-domain", "bm-keyword-ip"],
    },
    {
        "file": "antidad-lite.module",
        "name": "反广告 · 轻量版",
        "desc": "仅 blackmatrix7 AdvertisingLite 系列 · 约 0.6 MB · 误杀更少",
        "sources": ["bm-lite-domain", "bm-lite"],
    },
    {
        "file": "antidad-strict.module",
        "name": "反广告 · 严格版",
        "desc": "整合版 + LOWERTOP AntiAD（额外拦遥测/推送域，会误杀，先读 README）",
        "sources": ["antiad", "bm-domain", "bm-keyword-ip", "lt-antiad"],
    },
]

CST = timezone(timedelta(hours=8))

# ------------------------------------------------------------
# 白名单解析
# ------------------------------------------------------------
RULE_TYPES = ("DOMAIN,", "DOMAIN-SUFFIX,", "DOMAIN-KEYWORD,", "IP-CIDR,", "IP-CIDR6,", "USER-AGENT,")
POLICIES = ("DIRECT", "REJECT", "REJECT-DROP", "PROXY")


def looks_like_rule(s: str) -> bool:
    """判断一段文本像不像规则，用来统计「被注释掉的规则」，不把说明性注释算进去。"""
    s = s.strip()
    if s.startswith(RULE_TYPES):
        return True
    return " " not in s and "." in s and not s.endswith(("。", "，", "："))


def parse_whitelist(text: str):
    """返回 (生效规则列表, 被注释掉的规则条数)。"""
    rules, commented = [], 0
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            stripped = raw.strip().lstrip("#").strip()
            if raw.strip().startswith("#") and looks_like_rule(stripped):
                commented += 1
            continue
        if line.startswith(RULE_TYPES):
            parts = [p.strip() for p in line.split(",")]
            if parts[-1].upper() in POLICIES:
                rules.append(line)                      # 已写全策略，原样保留
            else:
                rules.append(f"{line},DIRECT")          # 补 DIRECT
        else:
            rules.append(f"DOMAIN-SUFFIX,{line},DIRECT")  # 裸域名 → 后缀放行
    return rules, commented


def render(profile, sources, whitelist_rules, measured_at):
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M (UTC+8)")
    out = [
        f"#!name= {profile['name']}",
        f"#!desc= {profile['desc']}",
        f"#!author= ace1892 · 仓库 https://github.com/{REPO}",
        f"#!icon= {ICON}",
        "",
        "[Rule]",
        "# " + "=" * 74,
        f"# 本文件由 scripts/build.py 生成于 {now}",
        "# 不要直接改这里 —— 改 whitelist.txt 或 sources.json，然后重新构建。",
        f"# 源基线日期：{measured_at}",
        f"# 生效白名单：{len(whitelist_rules)} 条（来自 whitelist.txt）",
        "#",
        "# 生效前提：小火箭「全局路由」必须设为「配置」，含 [Rule] 的模块才工作。",
        "# " + "=" * 74,
        "",
        "# " + "-" * 74,
        "# ① 误杀放行（必须最先：规则自上而下、命中即停）",
        "# " + "-" * 74,
    ]
    if whitelist_rules:
        out += [f"{r}" for r in whitelist_rules]
    else:
        out.append("# （whitelist.txt 当前没有生效条目）")

    for idx, sid in enumerate(profile["sources"], start=2):
        src = sources[sid]
        m = src["measured"]
        out += [
            "",
            "# " + "-" * 74,
            f"# {chr(0x2460 + idx - 1)} {src['name']}",
            f"#     引用类型必须 {src['kind']} · 上游基线 {m['entries']:,} 条 / {m['bytes']:,} 字节",
            f"#     来源 {src['homepage']}",
        ]
        if src["note"].startswith("⚠️"):
            out.append(f"#     {src['note']}")
        out.append("# " + "-" * 74)
        out.append(f"{src['kind']},{src['url']},REJECT")

    out += [
        "",
        "# " + "-" * 74,
        "# 备注",
        "# " + "-" * 74,
        "# · 纯 REJECT，不含 URL 重写 / 脚本 → 不需要开 MITM、不用装证书。",
        "# · 规则集走 jsDelivr：raw.githubusercontent.com 在本机实测间歇性不通。",
        "#   jsDelivr 的 @分支 引用约有 12 小时缓存延迟，规则集不需要实时，可接受。",
        "# · URL-REGEX 类规则未开 MITM 时不生效（无害）。",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    check_only = "--check" in sys.argv
    sources = {s["id"]: s for s in json.loads(SOURCES_FILE.read_text(encoding="utf-8"))["sources"]}
    measured_at = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))["measured_at"]
    wl_rules, wl_commented = parse_whitelist(WHITELIST_FILE.read_text(encoding="utf-8"))

    if not MODULES_DIR.is_dir():
        MODULES_DIR.mkdir(parents=True)
    drifted = []
    for prof in PROFILES:
        missing = [s for s in prof["sources"] if s not in sources]
        if missing:
            print(f"!! {prof['file']}: sources.json 里找不到 {missing}")
            return 1
        content = render(prof, sources, wl_rules, measured_at)
        target = MODULES_DIR / prof["file"]
        # 幂等：比较时忽略「生成时间」那一行，避免 CI 每次都判为漂移
        def normalized(t: str):
            return "\n".join(l for l in t.splitlines() if "生成于" not in l)
        if target.exists() and normalized(target.read_text(encoding="utf-8")) == normalized(content):
            print(f"= {prof['file']} 无变化")
            continue
        if check_only:
            drifted.append(prof["file"])
            print(f"!! {prof['file']} 与脚本输出不一致")
            continue
        target.write_text(content, encoding="utf-8")
        print(f"+ {prof['file']} 已生成（{len(content.encode())} 字节）")

    print(f"\n白名单：生效 {len(wl_rules)} 条，注释 {wl_commented} 条")
    if check_only and drifted:
        print("请运行 python3 scripts/build.py 重新生成后提交。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
