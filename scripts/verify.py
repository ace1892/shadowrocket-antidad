#!/usr/bin/env python3
"""
校验上游规则源：可达性 + 内容漂移。

漂移判定用「字节数 + 条数」双指标 —— 规则集每天更新，sha256 必然变，
所以不用哈希做判据；只有**条数变化超过阈值**或**字节数缩水**才提示。

用法：
  python3 scripts/verify.py                 # 报告，非 0 退出表示有异常
  python3 scripts/verify.py --update-baseline   # 把当前实测写回 sources.json
  python3 scripts/verify.py --quiet         # 只在异常时输出（给 Actions 用）

只用标准库，CI 里不需要装任何依赖。
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "sources.json"
CST = timezone(timedelta(hours=8))

# 条数相对基线变化超过这个比例就提示（规则集日常会有小波动）
DRIFT_RATIO = 0.15
# 字节数缩水超过这个比例视为异常（上游被清空 / 换格式）
SHRINK_RATIO = 0.30
TIMEOUT = 45


def fetch(url: str):
    req = urllib.request.Request(url, headers={
        "User-Agent": "shadowrocket-antidad-verify/1.0",
        "Cache-Control": "no-cache",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        return resp.status, raw


def count_entries(kind: str, raw: bytes) -> int:
    text = raw.decode("utf-8", errors="replace")
    if kind == "DOMAIN-SET":
        n = 0
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                n += 1
        return n
    n = 0
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "," in line:
            n += 1
    return n


def main() -> int:
    quiet = "--quiet" in sys.argv
    update = "--update-baseline" in sys.argv
    doc = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    problems: list[str] = []
    stamp = datetime.now(CST).strftime("%Y-%m-%d %H:%M (UTC+8)")

    if not quiet:
        print(f"上游规则源校验 · {stamp}\n")
        print(f"{'状态':<6}{'条数':>9}{'字节':>11}  {'名称'}")

    for src in doc["sources"]:
        base = src["measured"]
        # verify=local：url 只是「出处」，不是规则本体 —— 内联源常常只取了上游的一个子集
        # （例如开屏补丁只从 NoAd 里挑 9 条），拿上游文件的条数去比会误判成漂移。
        # 这类源只做本地自洽校验：sources.json 里登记的条数必须等于 rules 数组长度。
        if src.get("verify") == "local":
            n = len(src.get("rules", []))
            ok = (n == base["entries"])
            if not ok:
                problems.append(
                    f"{src['id']}: 内联条数登记 {base['entries']} 条，实际 {n} 条 —— sources.json 自相矛盾")
            if not quiet or not ok:
                print(f"{'OK' if ok else 'BAD':<6}{n:>9,}{'—':>11}  {src['name']}（内联，仅本地校验）")
            continue
        try:
            status, raw = fetch(src["url"])
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            problems.append(f"{src['id']}: 不可达 — {exc}")
            print(f"{'FAIL':<6}{'-':>9}{'-':>11}  {src['name']}  ← {exc}")
            continue

        entries = count_entries(src["kind"], raw)
        size = len(raw)
        digest = hashlib.sha256(raw).hexdigest()[:16]

        flag = "OK"
        if status != 200:
            flag = "BAD"
            problems.append(f"{src['id']}: HTTP {status}")
        elif entries < base["entries"] * (1 - DRIFT_RATIO):
            flag = "DRIFT"
            problems.append(
                f"{src['id']}: 条数 {base['entries']:,} → {entries:,}"
                f"（降幅 {1 - entries / base['entries']:.0%}，超过 {DRIFT_RATIO:.0%} 阈值）")
        elif size < base["bytes"] * (1 - SHRINK_RATIO):
            flag = "DRIFT"
            problems.append(
                f"{src['id']}: 字节 {base['bytes']:,} → {size:,}"
                f"（缩水 {1 - size / base['bytes']:.0%}）")

        if not quiet or flag != "OK":
            print(f"{flag:<6}{entries:>9,}{size:>11,}  {src['name']}")
        if update:
            base.update(entries=entries, bytes=size, sha256_16=digest)

    if update:
        doc["measured_at"] = datetime.now(CST).strftime("%Y-%m-%d")
        SOURCES_FILE.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if not quiet:
            print("\nsources.json 基线已更新。")

    if problems:
        print("\n发现异常：")
        for p in problems:
            print(f"  · {p}")
        return 1
    if not quiet:
        print("\n全部正常。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
