# 06. 复测、监控与检查清单

> 上一章：[05. Shopify 修复手册](05-shopify-fix-playbook.md) ｜ 返回 [README](../README.md)

优化最容易出问题的地方不是“改”，而是“证明改好了”。本章给出一套可信的复测方法和长期监控方案。

## 6.1 可信的前后对比

| 规则 | 原因 |
| --- | --- |
| 修改前先记录基线 | 没有基线就无法证明效果 |
| **同一工具、同一设备类型、同一 URL** | PSI、DevTools Lighthouse、本地 CLI 的结果不可互相比较（见 [1.5](01-pagespeed-basics.md#15-为什么每次测出来的分数都不一样)） |
| 每个条件至少测 5 次，取**中位数** | 单次波动可达 5–10 分 |
| 一次只改一类东西 | 否则不知道哪项改动带来了收益（或回退） |
| 比较**指标和诊断明细**，而不仅是分数 | 例如：HTML 体积、LCP breakdown 各阶段、TBT、请求数 |
| 上线后看 Field 数据 4 周 | CrUX 是 28 天滚动窗口 |

推荐的记录表：

| 日期 | 改动 | 工具/设备 | 5 次中位数：分数 / LCP / TBT / CLS | 关键诊断变化 |
| --- | --- | --- | --- | --- |
| 2026-11-09 | 基线 | PSI 移动端 | 69 / 11.0 s / 10 ms / 0.056 | HTML 429.84 KiB（传输） |
| … | 移除首页 Globo 配置 | PSI 移动端 | … | HTML ? KiB，LCP load delay ? ms |

## 6.2 测试未发布的主题

PSI 网站只能测公开 URL。测试主题副本：

1. 打开主题副本的预览链接（`?preview_theme_id=…`）。
2. Chrome DevTools → **Lighthouse** → Mode: Navigation，Device: Mobile，勾选 Performance → *Analyze page load*。
3. 使用无痕窗口，关闭所有浏览器扩展（扩展会注入脚本，干扰结果）。
4. 同一台电脑上对比“当前线上主题的预览链接”与“副本的预览链接”，避免比较不同环境。

## 6.3 用命令行批量测试

### Lighthouse CLI

```bash
npm i -g lighthouse
# 移动端（默认），输出 JSON + HTML
lighthouse https://torraslife.com/ \
  --only-categories=performance \
  --output=json --output=html --output-path=./torras-mobile \
  --chrome-flags="--headless=new"

# 桌面端
lighthouse https://torraslife.com/ --preset=desktop --only-categories=performance \
  --output=json --output-path=./torras-desktop.report.json --chrome-flags="--headless=new"

# 用本仓库脚本提取关键诊断
python scripts/lighthouse-summary.py torras-mobile.report.json
```

### PageSpeed Insights API

```bash
# 没有 API Key 时很容易遇到 HTTP 429（配额不足）；在 Google Cloud Console 免费申请一个 Key
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://reviveskincare.com/&strategy=mobile&category=performance&key=$PSI_API_KEY" \
  -o revive-psi.json
# 返回值中 lighthouseResult 与 Lighthouse JSON 结构相同；loadingExperience 是 CrUX 数据
python scripts/lighthouse-summary.py revive-psi.json
```

> 本教程写作时，未带 Key 的 API 请求返回了 `429 Quota exceeded`，所以截图都来自 PSI 网页版。这只是配额问题，与被测站点无关。

### Lighthouse CI：多次运行 + 阈值断言

```json
{
  "ci": {
    "collect": {
      "url": ["https://torraslife.com/", "https://torraslife.com/collections/all"],
      "numberOfRuns": 5,
      "settings": { "onlyCategories": ["performance"] }
    },
    "assert": {
      "assertions": {
        "largest-contentful-paint": ["warn", { "maxNumericValue": 4000 }],
        "total-blocking-time": ["warn", { "maxNumericValue": 600 }],
        "cumulative-layout-shift": ["error", { "maxNumericValue": 0.1 }],
        "total-byte-weight": ["warn", { "maxNumericValue": 4000000 }]
      }
    },
    "upload": { "target": "temporary-public-storage" }
  }
}
```

保存为 `lighthouserc.json`，运行 `npx @lhci/cli autorun`。主题使用 GitHub 集成时，可以把它放进 GitHub Actions，在每次合并主题改动后自动运行，防止性能回退。

## 6.4 真实用户数据的长期监控

| 渠道 | 能看到什么 | 适合 |
| --- | --- | --- |
| Shopify 后台 → 在线商店 → 主题页面的 **Web performance** 报告 | 店铺的 LCP、INP、CLS 趋势，可按页面类型查看，并标注了主题/App 变更事件 | 店主/运营日常查看 |
| PSI 顶部 Field 数据 | 某个 URL / 整个 Origin 近 28 天 p75 | 快速检查 |
| [CrUX Vis](https://cruxvis.withgoogle.com/) / CrUX History API | 过去数月的每周趋势 | 验证优化是否生效、发现回退 |
| Google Search Console → 核心网页指标 | 按 URL 分组的达标/不达标页面 | SEO 视角 |
| 自建 RUM（[5.12](05-shopify-fix-playbook.md#512-用-web-vitals-采集真实用户-inp-归因)） | 具体是哪个元素、哪个交互、哪段脚本慢 | 定位 INP 根因 |

## 6.5 建立“性能预算”，防止回退

性能问题大多不是一次造成的，而是“又装了一个 App”“又加了一个 section”慢慢累积的。建议约定：

| 预算项 | 建议值（移动端首页） | TORRAS 实测 | ReVive 实测 |
| --- | --- | --- | --- |
| HTML 传输体积 | ≤ 150 KiB | 429.84 KiB（PSI） | 86.28 KiB（PSI） |
| DOM 元素数 | ≤ 1,500 | 6,744 | — |
| 带 `fetchpriority="high"` 的元素 | 1（LCP） | 8 | — |
| 渲染阻塞 CSS | ≤ 2 个文件 | 7 个 | 4 个 |
| 首屏视频 | ≤ 1 MB，`load` 后加载 | 多个 `autoplay` 视频 | 2.9 MB（1080p） |
| 第三方脚本 JS 执行时间（PSI） | ≤ 1 s | — | 仅 Sentry 就 2.2 s |
| 新增 App 前 | 必须做一次“装前/装后”Lighthouse 对比 | | |

## 6.6 上线前检查清单

### 首屏 / LCP

- [ ] 用 PSI 或 DevTools Performance 确认 LCP 元素是谁
- [ ] LCP 图片是 `<img>`（不是 CSS 背景），在初始 HTML 中，`loading="eager"` + `fetchpriority="high"`
- [ ] 页面上**只有** LCP 图片带 `fetchpriority="high"`
- [ ] 轮播只有第一张 eager，首张不依赖 JS 才显示，没有首屏入场动画
- [ ] 移动/桌面不同图片用 `<picture>`，没有“隐藏但仍下载”的 eager 图
- [ ] 首屏视频：封面图为 LCP、低码率、`preload="none"`、`load` 后加载
- [ ] 渲染阻塞 CSS ≤ 2 个，关键 CSS 内联
- [ ] 首屏字体 ≤ 2 个文件并预加载，`font-display: swap`
- [ ] `preconnect` ≤ 4 个且都是首屏必需的域名

### HTML / DOM

- [ ] HTML 传输体积 ≤ 150 KiB；没有 App 在 `<head>` 中内联巨型配置
- [ ] 购物车抽屉、多级菜单、国家选择器、快速查看按需渲染
- [ ] SVG 图标使用 sprite，没有大量 base64 内联图片
- [ ] DOM 元素 ≤ 1,500

### JavaScript / 第三方

- [ ] 已删除不用的 App，并清理残留主题代码和 App embeds
- [ ] 同类工具（热图、录屏、聊天、评价）只保留一个
- [ ] 只在需要的模板加载对应脚本（`template.name`）
- [ ] 首屏之下的组件进入视口再加载；营销/客服脚本在空闲时错峰加载
- [ ] 没有把所有脚本都堆到“第一次交互”时加载
- [ ] 监控 SDK（Sentry 等）使用精简包、低采样率
- [ ] 广告/分析像素迁移到 Customer events（Web Pixels）

### 图片 / 媒体

- [ ] 所有 `<img>` 有 `width`/`height`，有正确的 `srcset` 和 `sizes`
- [ ] 首屏以下图片、iframe 全部 `loading="lazy"`
- [ ] 没有同时写 `loading="lazy"` 和 `fetchpriority="high"` 的矛盾属性
- [ ] GIF 已转为 MP4/WebM
- [ ] 上传规范：长边 ≤ 2400–3000 px；第三方弹窗素材已压缩

### 验证

- [ ] 修改前后各测 5 次，记录中位数和关键诊断明细
- [ ] 在桌面端和移动端都测试过
- [ ] 测试了首页、集合页、商品页、购物车四类模板
- [ ] 上线后 4 周跟踪 CrUX / Shopify Web performance 报告
