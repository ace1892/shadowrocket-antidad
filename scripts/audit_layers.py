#!/usr/bin/env python3
"""层级自查：断言「域名级模块只管域名、URL 级模块只管 URL」。

把 2026-09-28 那次手工审计固化成可重复运行的检查。四类断言：

  1. 一个模块**不得**同时含域名层与 URL 层规则。
     域名层 = DOMAIN / DOMAIN-SUFFIX / DOMAIN-KEYWORD / IP-CIDR / RULE-SET / DOMAIN-SET
     URL 层 = URL-REGEX 行 / [URL Rewrite] 段 / [Script] 段 / [MITM] 段
     —— 混装意味着「零解密的模块」里塞了只有解密才生效的规则，
        或者「URL 级模块」在做连接层拦截，两个方向的错都在这里抓。
  2. 误杀放行白名单只允许出现在**含域名级黑名单**的档里。
     两个模块出现逐字重复的 3 行白名单，正是这次要消灭的重叠。
  3. 子集档（splash / zhihu）声明为「两层都含」，但**每一条规则都必须在父档里存在**
     —— 它们是「替代父档的小个子」，不是「额外叠加的东西」。
     这一条能抓住子集档悄悄跑偏、与父档不一致的情况。
  4. URL 级模块的每条 URL 规则目标都必须被它自己的 [MITM] 声明覆盖
     —— 这条由 check_mitm.py 负责，此处不重复。

用法：python3 scripts/audit_layers.py [modules/*.module]
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

DOMAIN_TYPES = ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6")
WHITELIST_MARK = "domain-suffix,wxs.qq.com"

# 子集档：设计上就同时含两层，定位是「替代父档的小个子」。
# 装了父档就别再装它 —— 与 antidad-splash ⊂ antidad-rewrite 同理。
SUBSETS = {
    "antidad-splash.module": ["antidad-rewrite.module"],
    "antidad-zhihu.module": ["antidad-full.module", "antidad-rewrite.module"],
}


def sect(text: str, name: str) -> str:
    m = re.search(r"^\[" + re.escape(name) + r"\](.*?)(?=^\[|\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def body(text: str, name: str):
    return [l.strip() for l in sect(text, name).splitlines()
            if l.strip() and not l.strip().startswith("#")]


def mitm_items(text: str):
    """[MITM] 里的 hostname 条目集合。

    ⚠️ 必须**逐行**处理、先丢掉注释行再切分 —— 直接对整个段做 `[,\\s]+` 切分，
    注释里的中文散文会被切成一堆假 hostname（实测让 27 条变成 57 条）。
    """
    items = set()
    for line in sect(text, "MITM").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        s = re.sub(r"^hostname\s*=", "", s).replace("%APPEND%", " ")
        for c in re.split(r"[,\s]+", s):
            if c.strip():
                items.add(c.strip().lower())
    return items


def parse(path: Path):
    text = path.read_text(encoding="utf-8")
    rule = body(text, "Rule")
    return {
        "path": path,
        "rule": rule,
        "domain_rules": [l for l in rule if re.match(
            r"^(" + "|".join(DOMAIN_TYPES) + r"),", l, re.I)],
        "url_regex": [l for l in rule if l.upper().startswith("URL-REGEX,")],
        "sets": [l for l in rule if l.upper().startswith(("RULE-SET,", "DOMAIN-SET,"))],
        "rewrite": [l for l in body(text, "URL Rewrite") if l.startswith("^")],
        "scripts": body(text, "Script"),
        "mitm": mitm_items(text),
        "whitelist": any(l.lower().startswith(WHITELIST_MARK) for l in rule),
    }


def audit(info, pool):
    name = info["path"].name
    domain_level = bool(info["domain_rules"] or info["sets"])
    url_level = bool(info["url_regex"] or info["rewrite"] or info["scripts"] or info["mitm"])

    problems = []
    if name in SUBSETS:
        # 子集档：允许两层都有，但每条都必须在父档里存在
        parents = [pool[p] for p in SUBSETS[name] if p in pool]
        if not parents:
            problems.append(f"声明的父档不存在：{SUBSETS[name]}")
        else:
            p_rule = {l for p in parents for l in p["rule"]}
            p_rw = {l for p in parents for l in p["rewrite"]}
            p_sc = {l for p in parents for l in p["scripts"]}
            p_mitm = {m for p in parents for m in p["mitm"]}
            for label, mine, theirs in (
                    ("[Rule]", info["rule"], p_rule),
                    ("[URL Rewrite]", info["rewrite"], p_rw),
                    ("[Script]", info["scripts"], p_sc),
                    ("[MITM]", sorted(info["mitm"]), p_mitm)):
                extra = [x for x in mine if x not in theirs]
                if extra:
                    problems.append(f"{label} 有 {len(extra)} 条不在父档里 → "
                                    f"「子集档」不成立：{extra[:3]}")
        kind = "子集档"
    else:
        if domain_level and url_level:
            problems.append(
                f"域名层与 URL 层混装：域名规则 {len(info['domain_rules'])} 条 · "
                f"URL-REGEX {len(info['url_regex'])} 条 · 重写 {len(info['rewrite'])} 条 · "
                f"脚本 {len(info['scripts'])} 条 · MITM {len(info['mitm'])} 条")
        if url_level and not domain_level and info["domain_rules"]:
            problems.append("URL 级模块里出现域名级规则："
                            + "、".join(info["domain_rules"][:4]))
        if domain_level and not url_level and info["url_regex"]:
            problems.append("域名级模块里出现 URL-REGEX（URL 层规则）")
        if info["whitelist"] and not domain_level:
            problems.append("URL 级模块里出现误杀放行白名单"
                            "（本模块没有域名级 REJECT，白名单没有放行对象）")
        kind = ("域名级" if domain_level and not url_level
                else "URL 级" if url_level and not domain_level
                else "空" if not url_level and not domain_level else "混合")

    print(f"{'OK ' if not problems else '!! '}{name:26s} {kind:6s} "
          f"域名规则 {len(info['domain_rules']):>4} · 规则集 {len(info['sets'])} · "
          f"URL-REGEX {len(info['url_regex']):>2} · 重写 {len(info['rewrite']):>2} · "
          f"脚本 {len(info['scripts']):>2} · MITM {len(info['mitm']):>2} · "
          f"白名单 {'有' if info['whitelist'] else '无'}")
    for p in problems:
        print(f"     ↳ {p}")
    return len(problems)


def main(paths):
    infos = [parse(Path(p)) for p in sorted(paths)]
    pool = {i["path"].name: i for i in infos}
    bad = sum(audit(i, pool) for i in infos)
    print()
    print(f"发现 {bad} 处层级问题 —— 见上方 ↳" if bad
          else "层级自检通过：域名级只管域名，URL 级只管 URL，无重叠。")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or sorted(glob.glob("modules/*.module"))))
