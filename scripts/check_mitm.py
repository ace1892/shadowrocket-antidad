#!/usr/bin/env python3
"""MITM 覆盖自查：模块里每条 URL 级规则的域名目标，必须被 [MITM] 声明覆盖。

做法：把规则里的域名模式展开成「具体候选」（\\d→0、(a|b) 递归展开），
      再用 [MITM] 的通配写法去匹配。有候选匹配不上 = 该规则静默失效。

只检查真正的 URL 级规则：
  · [URL Rewrite] 段的 `^https?://...` 行
  · [Rule] 段的 `URL-REGEX,...` 行
  · [Script] 段每条 `pattern=` 里的正则
**不检查** `RULE-SET,<url>` / `DOMAIN-SET,<url>` —— 那是规则集地址，不是解密目标。

用法：python3 scripts/check_mitm.py [modules/*.module]
"""
from __future__ import annotations
import re, sys, glob
from pathlib import Path

BSCH = chr(92)


def unesc(s: str) -> str:
    return s.replace(BSCH + '/', '/').replace(BSCH + '.', '.')


def section(text: str, name: str) -> str:
    m = re.search(r'^\[' + re.escape(name) + r'\](.*?)(?=^\[|\Z)', text, re.M | re.S)
    return m.group(1) if m else ""


def _outer_group(s: str):
    """最外层第一个 (..) 的起止下标（配平括号），无则 None。"""
    start = s.find('(')
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return start, i
    return None


def _split_top(s: str):
    """按顶层 | 切分（不切括号内的）。"""
    parts, depth, cur = [], 0, ''
    for c in s:
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        if c == '|' and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += c
    parts.append(cur)
    return parts


def expand(host: str):
    """把域名模式展开为具体候选（递归处理嵌套交替）。"""
    g = _outer_group(host)
    if g:
        a, b = g
        alts = _split_top(host[a + 1:b])
        if len(alts) > 1:
            out = []
            for alt in alts:
                out += expand(host[:a] + alt + host[b + 1:])
            return out
        return expand(host[:a] + host[a + 1:b] + host[b + 1:])   # 单元素括号，去掉
    h = re.sub(r'\\[dws]\+?', '0', host)      # \d \w \s 及量词 → 0
    h = h.replace('+', '').replace('*', '0').replace('?', '0')
    return [h] if '.' in h else []


def host_of(body: str):
    if '://' not in body:
        return None
    host = body.split('://', 1)[1].split('/')[0]
    host = re.sub(r'\(\?[=!][^)]*\)', '', host)     # 去掉前瞻/后顾
    return host or None


def script_patterns(text: str):
    """[Script] 段每条脚本的 pattern= 值。

    行内是逗号分隔的 key=value 列表，但 pattern 本身可能含 `=`（如 `(c=ad|...)`），
    所以不能按第一个 `,` 或 `=` 切 —— 用「pattern= 开始、到下一个已知键名或行尾」来取。
    """
    out = []
    for line in section(text, 'Script').splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        m = re.search(r'(?:^|,)pattern=(.*?)(?:,(?:requires-body|script-path|type|max-size|debug)=|$)', s)
        if m:
            out.append(m.group(1))
    return out


NOISE = ('RULE-SET,', 'DOMAIN-SET,', 'GEOIP,', 'IP-CIDR,', 'IP-CIDR6,')


def rule_targets(text: str):
    targets = set()
    # [URL Rewrite]：^https?://... 行（URL-REGEX 语法）
    for line in section(text, 'URL Rewrite').splitlines():
        s = line.strip()
        if s.startswith('^'):
            h = host_of(unesc(s))
            if h:
                targets.update(c.lower() for c in expand(h))
    # [Rule]：只认 URL-REGEX 行；RULE-SET / DOMAIN-SET 是规则集地址，跳过
    for line in section(text, 'Rule').splitlines():
        s = line.strip()
        if s.startswith('#'):
            continue
        if s.upper().startswith('URL-REGEX,'):
            h = host_of(unesc(s.split(',', 1)[1]))
            if h:
                targets.update(c.lower() for c in expand(h))
    # [Script]：pattern= 里的正则
    for pat in script_patterns(text):
        h = host_of(unesc(pat))
        if h:
            targets.update(c.lower() for c in expand(h))
    return targets


def mitm_entries(text: str):
    raw = section(text, 'MITM')
    raw = re.sub(r'^\s*hostname\s*=', '', raw, flags=re.M)
    out = []
    for chunk in raw.replace('%APPEND%', '').replace('\n', ',').split(','):
        c = chunk.strip().lower()
        if c and not c.startswith('#'):        # 过滤注释行，否则会被当成声明
            out.append(c)
    return out


def covered(host: str, entries) -> bool:
    for e in entries:
        if e.startswith('-'):
            continue                           # 排除项不构成覆盖
        pat = re.escape(e).replace(re.escape('*'), '[^,]*').replace(re.escape('?'), '.')
        if re.match('^' + pat + '$', host):
            return True
    return False


def main(paths):
    bad = 0
    for p in sorted(paths):
        path = Path(p)
        text = path.read_text(encoding='utf-8')
        entries = mitm_entries(text)
        targets = rule_targets(text)
        if not targets:
            print(f"=  {path.name}：无 URL 级规则，无需 MITM")
            continue
        missing = sorted(t for t in targets if not covered(t, entries))
        if missing:
            bad += 1
            print(f"!! {path.name}：{len(missing)} 个目标未被 [MITM] 覆盖 → 静默失效")
            for h in missing:
                print(f"     {h}")
        else:
            print(f"OK {path.name}：{len(targets)} 个目标全部被 {len(entries)} 条声明覆盖")
    return 1 if bad else 0


if __name__ == '__main__':
    args = sys.argv[1:] or sorted(glob.glob('modules/*.module'))
    raise SystemExit(main(args))
