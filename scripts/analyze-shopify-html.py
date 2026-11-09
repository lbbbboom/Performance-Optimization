#!/usr/bin/env python3
"""统计 Shopify 页面 HTML 的“体积账单”：哪些内联脚本/样式/section 让 HTML 变大。

用法:
    python scripts/analyze-shopify-html.py https://torraslife.com/
    python scripts/analyze-shopify-html.py saved-page.html
"""
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (Linux; Android 11; moto g power) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"


def fetch(src):
    if src.startswith("http"):
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    with open(src, encoding="utf-8", errors="replace") as f:
        return f.read()


def size(s):
    return len(s.encode("utf-8"))


def kb(n):
    return f"{n / 1024:,.1f} KB"


def main():
    html = fetch(sys.argv[1])
    total = size(html)
    head_end = html.find("</head>")
    print(f"HTML 总体积（未压缩）: {kb(total)}")
    if head_end > 0:
        print(f"<head> 体积: {kb(size(html[:head_end]))}")

    m = re.search(r'Shopify\.theme\s*=\s*(\{.*?\});', html)
    if m:
        print("主题:", m.group(1)[:200])

    blocks = []
    for tag in ("script", "style", "svg"):
        for b in re.finditer(rf"<{tag}\b[^>]*>.*?</{tag}>", html, re.S | re.I):
            if tag == "script" and re.match(r"<script[^>]+\bsrc=", b.group(0), re.I):
                continue
            blocks.append((size(b.group(0)), tag, re.sub(r"\s+", " ", b.group(0))[:110]))

    print("\n内联内容合计:")
    for tag in ("script", "style", "svg"):
        items = [b for b in blocks if b[1] == tag]
        print(f"  <{tag}> x{len(items)}: {kb(sum(b[0] for b in items))}")

    print("\n最大的 15 个内联块:")
    for n, tag, preview in sorted(blocks, reverse=True)[:15]:
        print(f"  {kb(n):>10}  <{tag}>  {preview}")

    print("\n最大的 15 个 section（按输出 HTML 体积）:")
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'<(?:div|section)[^>]+id="shopify-section-([^"]+)"', html)]
    sections = []
    for i, (pos, sid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(html)
        sections.append((size(html[pos:end]), sid))
    for n, sid in sorted(sections, reverse=True)[:15]:
        print(f"  {kb(n):>10}  {sid}")

    print("\n其它信号:")
    print("  外部 <script src>:", len(re.findall(r"<script[^>]+\bsrc=", html, re.I)))
    print("  stylesheet <link>:", len(re.findall(r'rel=["\']?stylesheet', html, re.I)))
    print("  <img>:", len(re.findall(r"<img\b", html, re.I)), "| loading=lazy:", len(re.findall(r'loading=["\']?lazy', html, re.I)))
    print("  fetchpriority 属性:", len(re.findall(r"fetchpriority=", html, re.I)),
          "| 其中 high:", len(re.findall(r'fetchpriority=["\']?high', html, re.I)))
    print("  preconnect:", len(re.findall(r'rel=["\']?preconnect', html, re.I)))
    print("  base64 图片:", len(re.findall(r"data:image/[a-z+]+;base64", html, re.I)))
    print("  <video>:", len(re.findall(r"<video\b", html, re.I)), "| autoplay:", len(re.findall(r"<video[^>]*autoplay", html, re.I)))
    print("  <iframe>:", len(re.findall(r"<iframe\b", html, re.I)))
    ext = sorted(set(re.findall(r"/extensions/[0-9a-f-]+/([a-z0-9-]+)", html)))
    print("  Theme app extensions:", ", ".join(ext) or "-")


if __name__ == "__main__":
    main()
