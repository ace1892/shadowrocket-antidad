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
  modules/antidad-zhihu.module     （补丁档：含 [MITM]，必须开 HTTPS 解密）

设计要点：
  1. 模块的 [Rule] 段支持 RULE-SET / DOMAIN-SET 远程引用（社区实证，官方手册无明文）。
     所以本仓库**不需要**把 5.7 MB 域名集存进来 —— 模块直接引用上游，体积只有几 KB。
  2. 白名单必须排在最前（规则自上而下、命中即停）。
  3. 引用类型不能写错：域名集必须 DOMAIN-SET，关键词/IP 集必须 RULE-SET。
  4. kind=INLINE 的源把规则**原文内联**进模块，不远程引用 —— 用于「上游会重组目录」
     的场景（本项目亲历过一次模块引用 404 静默死亡）。INLINE 源可带 mitm 字段，
     渲染时在文末生成 [MITM] hostname = %APPEND% 段（追加，不覆盖别人的声明）。

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
    {
        # 知乎广告走的是「正经域名下的路径」，域名级规则原理上拦不到（见 README）。
        # 这是一次**补丁**，不是第四档 —— 它必须开 MITM 才有意义，
        # 所以单独成文件，不愿意开解密的人可以不装。
        "file": "antidad-zhihu.module",
        "name": "反广告 · 知乎补丁",
        "desc": "知乎广告专用 · 官方 ZhihuAds 规则内联 · ⚠️ 必须开 HTTPS 解密才生效",
        "sources": ["zhihu-inline"],
        # Qure 图标库里没有 zhihu 图标（实测 404），故用 AdBlack 与前三档的 Advertising 区分。
        "icon": "https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/AdBlack.png",
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
    used = [sources[s] for s in profile["sources"]]
    mitm_hosts = [s["mitm"] for s in used if s.get("mitm")]
    needs_mitm = bool(mitm_hosts)
    icon = profile.get("icon", ICON)

    out = [
        f"#!name= {profile['name']}",
        f"#!desc= {profile['desc']}",
        f"#!author= ace1892 · 仓库 https://github.com/{REPO}",
        f"#!icon= {icon}",
        "",
        "[Rule]",
        "# " + "=" * 74,
        f"# 本文件由 scripts/build.py 生成于 {now}",
        "# 不要直接改这里 —— 改 whitelist.txt 或 sources.json，然后重新构建。",
        f"# 源基线日期：{measured_at}",
        f"# 生效白名单：{len(whitelist_rules)} 条（来自 whitelist.txt）",
        "#",
        "# 生效前提：小火箭「全局路由」必须设为「配置」，含 [Rule] 的模块才工作。",
    ]
    if needs_mitm:
        out.append("# ⚠️ 本模块含 URL-REGEX → 还必须开「HTTPS 解密」并信任根证书。")
    out.append("# " + "=" * 74)
    out += [
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
        ]
        if src["kind"] == "INLINE":
            out.append(
                f"#     内联 {m['entries']} 条 / {m['bytes']:,} 字节"
                f"（不远程引用，规避上游重组目录导致的静默失效）")
        else:
            out.append(
                f"#     引用类型必须 {src['kind']}"
                f" · 上游基线 {m['entries']:,} 条 / {m['bytes']:,} 字节")
        out.append(f"#     来源 {src['homepage']}")
        if src["note"].startswith("⚠️"):
            out.append(f"#     {src['note']}")
        out.append("# " + "-" * 74)
        if src["kind"] == "INLINE":
            out += list(src["rules"])
        else:
            out.append(f"{src['kind']},{src['url']},REJECT")

    if needs_mitm:
        out += [
            "",
            "[MITM]",
            "# %APPEND% = 追加到现有解密列表，不覆盖其它模块（含配置里已有的声明）。",
            f"hostname = %APPEND% {','.join(mitm_hosts)}",
        ]

    out += [
        "",
        "# " + "-" * 74,
        "# 备注",
        "# " + "-" * 74,
    ]
    if needs_mitm:
        out += [
            "# · ⚠️ 含 URL-REGEX：未开「HTTPS 解密」+ 未信任根证书时，这些规则**静默不生效**"
            "（小火箭不报错）。",
            "# · 解密范围见上方 [MITM]。长期不用请直接卸载本模块，避免白付解密开销。",
        ]
    else:
        out.append("# · 纯 REJECT，不含 URL 重写 / 脚本 → 不需要开 MITM、不用装证书。")
    out += [
        "# · 规则集走 jsDelivr：raw.githubusercontent.com 在本机实测间歇性不通。",
        "#   jsDelivr 的 @分支 引用约有 12 小时缓存延迟，规则集不需要实时，可接受。",
    ]
    if not needs_mitm:
        out.append("# · URL-REGEX 类规则未开 MITM 时不生效（无害）。")
    out.append("")
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
