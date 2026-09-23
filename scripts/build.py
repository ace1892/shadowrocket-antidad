#!/usr/bin/env python3
"""
生成 modules/*.module

输入：
  sources.json   —— 上游规则源登记表（id / 类型 / URL / 实测基线）
  whitelist.txt  —— 误杀放行名单（人可读，改动只需动它）

输出：
  modules/antidad-full.module      域名级 · 整合版
  modules/antidad-lite.module      域名级 · 轻量版
  modules/antidad-strict.module    域名级 · 严格版
  modules/antidad-rewrite.module   ★ 主力：URL 级去广告整合（含 [URL Rewrite] 与 [Script]）
  modules/antidad-zhihu.module     URL 级 · 只要知乎（重写整合的子集）
  modules/antidad-splash.module    URL 级 · 只要开屏（重写整合的子集）

设计要点：
  1. 模块的 [Rule] 段支持 RULE-SET / DOMAIN-SET 远程引用（社区实证，官方手册无明文）。
     所以本仓库**不需要**把 5.7 MB 域名集存进来 —— 模块直接引用上游，体积只有几 KB。
  2. 白名单必须排在最前（规则自上而下、命中即停）。
  3. 引用类型不能写错：域名集必须 DOMAIN-SET，关键词/IP 集必须 RULE-SET。
  4. **段的划分由 sources.json 的 `section` 字段决定**，不做分段路由 = 规则落错段 =
     非法语法 = 静默失效（小火箭不报错）。三种段的语法各不相同：
       · 缺省 "Rule"      —— 普通规则 / 规则集引用 / `URL-REGEX,` 行
       · "URL Rewrite"    —— `^正则 target` 形态
       · "Script"         —— `名字=type=...,pattern=...,script-path=...`
  5. kind=INLINE 的源把规则**原文内联**进模块，不远程引用 —— 用于「上游会重组目录」
     的场景（本项目亲历过一次模块引用 404 静默死亡）。INLINE 源可带 mitm 字段，
     渲染时在文末生成 [MITM] hostname = %APPEND% 段（追加，不覆盖别人的声明）。
     多个源的 mitm 会去重合并，`-` 排除项统一排到末尾（先声明、后排除）。

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
        # ★ 主力档：把「所有 URL 级去广告」整合进一个模块。
        # 合并的意义不是省事，而是**把散落的 %APPEND% 解密声明收拢成一份可审计的名单**：
        # 装三个模块时，解密面是三者之和且看不见；合成一个模块后，
        # 24 个目标一眼可数，check_mitm.py 也能一次校验到位。
        #
        # 内容 = App 开屏（自建）+ 知乎（blackmatrix7 内联）+ B站（biliad 去广告部分）+ 微信公众号。
        # B站已剔除 4K 画质解锁 / 皮肤 / 标签页 / 我的页面 / CC字幕 / 屏蔽IP / SIM地区 等非去广告项。
        "file": "antidad-rewrite.module",
        "name": "反广告 · 重写整合",
        "desc": "App开屏 + 知乎 + B站 + 微信公众号 去广告 · {mitm} 个解密目标 · ⚠️ 必须开 HTTPS 解密",
        "sources": ["app-splash", "bili-rewrite", "zhihu-inline", "bili-script", "wechat-script"],
        # Qure 图标库里 AdWhite 与前三档的 Advertising、补丁档的 AdBlack 区分开。
        "icon": "https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/AdWhite.png",
    },
    {
        # 知乎广告走的是「正经域名下的路径」，域名级规则原理上拦不到（见 README）。
        # 这是一次**补丁**，不是第四档 —— 它必须开 MITM 才有意义，
        # 所以单独成文件，不愿意开解密的人可以不装。
        # （已被「反广告 · 重写整合」包含；此档保留给「只想去知乎广告、解密面要最小」的场景。）
        "file": "antidad-zhihu.module",
        "name": "反广告 · 知乎补丁",
        "desc": "知乎广告专用 · 官方 ZhihuAds 规则内联 · ⚠️ 必须开 HTTPS 解密才生效",
        "sources": ["zhihu-inline"],
        # Qure 图标库里没有 zhihu 图标（实测 404），故用 AdBlack 与前三档的 Advertising 区分。
        "icon": "https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/AdBlack.png",
    },
    {
        # 针对「URL 重写类模块太耗电」的定向方案：
        # NoAd 声明 153 个解密目标，其中含多个高流量图片/视频 CDN 通配符，
        # 导致刷电商时商品图流量全部走 TLS 解密 —— 这是发热主因。
        # 本档只保留常用 App 的**开屏广告接口**（流量极小），剔除全部 CDN 域。
        # （已被「反广告 · 重写整合」包含；此档保留给「只要开屏、不想碰 B站脚本」的场景。）
        "file": "antidad-splash.module",
        "name": "反广告 · 开屏广告",
        "desc": "常用 App 开屏广告 · 仅 {mitm} 个解密目标 · ⚠️ 必须开 HTTPS 解密才生效",
        "sources": ["app-splash"],
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


def wrap_note(note: str, width: int = 86):
    """把长注释折成多行，宽度按「CJK 算 2」计。

    按 token 折行而不是按字符 —— 一个 ASCII 词（域名、路径、代码）是不可断的原子，
    否则会生成 `blac` / `kmatrix7` 这种断词，反而难读。
    允许在空格、以及 , . / ; : ) ] 之后断开，让折行点落在自然边界上。
    """
    def w(s):
        return sum(2 if ord(c) > 0x2E80 else 1 for c in s)

    BREAK_AFTER = " ,./;:)]、，。；：）】"

    lines, cur = [], ""
    for ch in note:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if w(cur) + w(ch) > width:
            # 回退到最近一个可断点；退不动就硬断
            cut = max((cur.rfind(c) for c in BREAK_AFTER), default=-1)
            if cut >= max(0, len(cur) // 3):
                lines.append(cur[:cut + 1])
                cur = cur[cut + 1:] + ch
            else:
                lines.append(cur)
                cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def render_source_block(src, num):
    """渲染单个规则源的注释头 + 规则内容（不含段名）。"""
    m = src["measured"]
    block = [
        "",
        "# " + "-" * 74,
        f"# {chr(0x2460 + num - 1)} {src['name']}",
    ]
    if src["kind"] == "INLINE":
        block.append(
            f"#     内联 {m['entries']} 条 / {m['bytes']:,} 字节"
            f"（不远程引用，规避上游重组目录导致的静默失效）")
    else:
        block.append(
            f"#     引用类型必须 {src['kind']}"
            f" · 上游基线 {m['entries']:,} 条 / {m['bytes']:,} 字节")
    block.append(f"#     来源 {src['homepage']}")
    block += [f"#     {ln}" for ln in wrap_note(src["note"])]
    block.append("# " + "-" * 74)
    if src["kind"] == "INLINE":
        block += list(src["rules"])
    else:
        block.append(f"{src['kind']},{src['url']},REJECT")
    return block


def collect_mitm(used):
    """把各源的 mitm 字段合并成一份全局解密名单。

    同一个域名只出现一次；`-` 排除项一律排到末尾 ——
    小火箭的 hostname 是「先声明、后排除」，顺序反了排除可能不生效。
    """
    pos, neg = [], []
    for src in used:
        for chunk in (src.get("mitm") or "").split(","):
            h = chunk.strip()
            if not h or h == "%APPEND%":
                continue
            bucket = neg if h.startswith("-") else pos
            if h.lower() not in {x.lower() for x in bucket}:
                bucket.append(h)
    return pos + neg


def render(profile, sources, whitelist_rules, measured_at):
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M (UTC+8)")
    used = [sources[s] for s in profile["sources"]]
    # 按目标段分组。三种段各有自己的语法，放错段 = 非法语法 = 静默失效：
    #   section 缺省 "Rule"        → 普通规则 / 规则集引用 / URL-REGEX
    #   section == "URL Rewrite"   → `^正则 target` 形态（如 `^https?://... - reject`）
    #   section == "Script"        → `名字=type=...,pattern=...,script-path=...`
    rule_srcs = [s for s in used if s.get("section", "Rule") == "Rule"]
    rewrite_srcs = [s for s in used if s.get("section") == "URL Rewrite"]
    script_srcs = [s for s in used if s.get("section") == "Script"]
    mitm_hosts = collect_mitm(used)
    needs_mitm = bool(mitm_hosts) or bool(rewrite_srcs) or bool(script_srcs)
    icon = profile.get("icon", ICON)
    # `{mitm}` 占位符 → 真实解密目标数。手写的数字迟早会和 [MITM] 对不上，
    # 而这个数字正是用户判断「这模块费不费电」的唯一依据，必须由脚本算。
    desc = profile["desc"].replace("{mitm}", str(sum(1 for h in mitm_hosts if not h.startswith("-"))))

    out = [
        f"#!name= {profile['name']}",
        f"#!desc= {desc}",
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
        out.append("# ⚠️ 本模块需要开「HTTPS 解密」并信任根证书（含 URL 重写 / URL-REGEX）。")
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

    n = 2
    for src in rule_srcs:
        out += render_source_block(src, n)
        n += 1

    if rewrite_srcs:
        out += ["", "[URL Rewrite]"]
        for src in rewrite_srcs:
            out += render_source_block(src, n)
            n += 1

    if script_srcs:
        out += ["", "[Script]"]
        for src in script_srcs:
            out += render_source_block(src, n)
            n += 1

    if needs_mitm:
        out += [
            "",
            "[MITM]",
            "# %APPEND% = 追加到现有解密列表，不覆盖其它模块（含配置里已有的声明）。",
            "# `-` 前缀 = 排除；已统一排在末尾（先声明、后排除）。",
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
            "# · ⚠️ 未开「HTTPS 解密」+ 未信任根证书时，[URL Rewrite] 与 URL-REGEX 规则"
            "**静默不生效**（小火箭不报错）。",
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
