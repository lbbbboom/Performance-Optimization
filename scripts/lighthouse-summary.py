#!/usr/bin/env python3
"""从 Lighthouse JSON（或 PSI API 返回的 JSON）中提取最常用的性能诊断信息。

用法:
    python scripts/lighthouse-summary.py report.json [--top 10]
"""
import argparse
import json
import sys
from collections import defaultdict

METRICS = [
    ("first-contentful-paint", "FCP"),
    ("largest-contentful-paint", "LCP"),
    ("total-blocking-time", "TBT"),
    ("cumulative-layout-shift", "CLS"),
    ("speed-index", "SI"),
]


def load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # PSI API 的返回值把 Lighthouse 结果放在 lighthouseResult 里
    return data.get("lighthouseResult", data), data.get("loadingExperience")


def table_items(audit):
    details = (audit or {}).get("details") or {}
    if details.get("type") == "table":
        return details.get("items", [])
    items = []
    for child in details.get("items", []) or []:
        if isinstance(child, dict) and child.get("type") == "table":
            items.extend(child.get("items", []))
    return items


def kib(n):
    return f"{(n or 0) / 1024:,.0f} KiB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()
    lh, field = load(args.report)
    audits = lh["audits"]
    top = args.top

    print(f"URL: {lh.get('finalDisplayedUrl') or lh.get('finalUrl')}")
    print(f"Lighthouse {lh.get('lighthouseVersion')} | formFactor={lh['configSettings'].get('formFactor')}")
    print(f"Performance score: {round((lh['categories']['performance']['score'] or 0) * 100)}")
    for key, name in METRICS:
        a = audits.get(key, {})
        print(f"  {name:4} {a.get('displayValue', '-'):>10}  (score {a.get('score')})")

    if field and field.get("metrics"):
        print("\n[Field / CrUX p75]", field.get("overall_category"))
        for k, v in field["metrics"].items():
            print(f"  {k}: {v.get('percentile')} ({v.get('category')})")

    print("\n[LCP breakdown]")
    for it in table_items(audits.get("lcp-breakdown-insight")):
        label = it.get("label") or it.get("subpart")
        print(f"  {label:26} {it.get('duration', 0):8.0f} ms")

    print("\n[Render-blocking requests]")
    for it in table_items(audits.get("render-blocking-insight"))[:top]:
        print(f"  {kib(it.get('totalBytes') or it.get('transferSize')):>9}  {it.get('url')}")

    print("\n[JS execution time by script]")
    for it in sorted(table_items(audits.get("bootup-time")), key=lambda x: -x.get("total", 0))[:top]:
        print(f"  {it.get('total', 0):7.0f} ms  {it.get('url')}")

    print("\n[3rd parties by main-thread time]")
    tp = sorted(table_items(audits.get("third-party-summary")), key=lambda x: -x.get("mainThreadTime", 0))
    for it in tp[:top]:
        ent = it.get("entity")
        ent = ent.get("text") if isinstance(ent, dict) else ent
        print(f"  {it.get('mainThreadTime', 0):7.0f} ms  {kib(it.get('transferSize')):>9}  {ent}")

    print("\n[Transfer size by resource type]")
    by_type = defaultdict(int)
    for it in table_items(audits.get("network-requests")):
        by_type[it.get("resourceType") or "Other"] += it.get("transferSize", 0)
    for t, size in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:12} {kib(size):>10}")

    print("\n[Largest requests]")
    for it in table_items(audits.get("total-byte-weight"))[:top]:
        print(f"  {kib(it.get('totalBytes')):>9}  {it.get('url')}")

    print("\n[DOM size]")
    for it in table_items(audits.get("dom-size-insight") or audits.get("dom-size"))[:3]:
        print(f"  {it.get('statistic')}: {it.get('value')}")


if __name__ == "__main__":
    sys.exit(main())
