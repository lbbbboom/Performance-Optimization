# 05. Shopify 修复手册（代码）

> 上一章：[04. 案例二：reviveskincare.com](04-case-reviveskincare.md) ｜ 下一章：[06. 复测、监控与检查清单](06-retest-and-monitoring.md)
>
> 本章代码以 Online Store 2.0 主题（Dawn、Impulse、Woodstock 等）为背景。不同主题的变量名/文件名不同，**请在复制的主题（Duplicate）上修改并预览测试后再发布**。

## 5.0 修改前的准备

1. 在线商店 → 主题 → 当前主题 → **⋯ → 复制（Duplicate）**，所有修改在副本上进行。
2. 副本的“预览”链接形如 `https://你的店铺/?preview_theme_id=123456789`。可以直接把这个链接放进 Chrome DevTools 的 Lighthouse 面板测试（PSI 网站无法测试预览主题）。
3. 记录修改前的基线：同一设置测 5 次，记录中位数（见 [第 6 章](06-retest-and-monitoring.md)）。
4. 如果主题通过 GitHub 集成管理，用分支 + Pull Request 的方式提交修改，便于回滚。

## 5.1 首屏图（LCP 图片）：唯一的 eager + high

**原则：每个页面只有一个（最多两个，如移动/桌面各一张）图片使用 `loading="eager"` + `fetchpriority="high"`，其余全部 `loading="lazy"`，并且不写 `fetchpriority="high"`。**

用 `section.index`（section 在模板中的位置，从 1 开始）判断是否首屏：

```liquid
{%- liquid
  assign is_above_fold = false
  if section.index == 1 and forloop.first
    assign is_above_fold = true
  endif
-%}

{%- if is_above_fold -%}
  {{ slide.image
    | image_url: width: 1500
    | image_tag:
      loading: 'eager',
      fetchpriority: 'high',
      widths: '375, 550, 750, 1000, 1500',
      sizes: '100vw',
      alt: slide.image.alt
  }}
{%- else -%}
  {{ slide.image
    | image_url: width: 1500
    | image_tag:
      loading: 'lazy',
      widths: '375, 550, 750, 1000, 1500',
      sizes: '100vw',
      alt: slide.image.alt
  }}
{%- endif -%}
```

要点：

- `image_tag` 会自动输出 `width`/`height`（防 CLS）和基于 `widths` 的 `srcset`。
- 轮播**第一张**以外的幻灯片必须懒加载；轮播 JS 初始化前，第一张也必须是可见的（不要先 `opacity: 0` 再淡入）。
- **不要把 LCP 图片做成 CSS `background-image`**，预加载扫描器看不到它。
- 自查方法：在主题代码里全局搜索 `fetchpriority` 和 `loading: 'eager'` / `loading="eager"`，逐个确认是否真的在首屏。TORRAS 首页有 8 个元素声明了 `fetchpriority="high"`，就是这个检查没做的结果。

### 移动端和桌面端用不同的图（艺术指导）

```liquid
<picture>
  <source
    media="(max-width: 749px)"
    srcset="{{ section.settings.image_mobile | image_url: width: 750 }} 750w,
            {{ section.settings.image_mobile | image_url: width: 1080 }} 1080w"
    sizes="100vw"
    width="{{ section.settings.image_mobile.width }}"
    height="{{ section.settings.image_mobile.height }}">
  {{ section.settings.image_desktop
    | image_url: width: 2400
    | image_tag: loading: 'eager', fetchpriority: 'high',
                 widths: '1000, 1500, 2000, 2400', sizes: '100vw' }}
</picture>
```

浏览器只会下载匹配到的那一个 `source`，`fetchpriority` 写在 `<img>` 上即可对最终选中的资源生效。不要用两个 `<img>` + CSS `display:none` 来区分移动/桌面——隐藏的那张如果是 eager，照样会下载。

### 需要时可以额外 preload

`image_tag` 支持 `preload: true`，Shopify 会通过 HTTP `Link` 头提前告诉浏览器下载这张图，比 HTML 里的 `<img>` 更早：

```liquid
{{ image | image_url: width: 1500 | image_tag: preload: true, fetchpriority: 'high', loading: 'eager', widths: '750, 1100, 1500', sizes: '100vw' }}
```

只对 LCP 图片使用，用多了效果和 TORRAS 的“8 个 high”一样会互相抵消。

## 5.2 非首屏图片：正确的 `srcset` 和 `sizes`

`sizes` 告诉浏览器“这张图在页面上大概多宽”。写错 `sizes` 是“下载的图比显示的大”最常见的原因：

| 布局 | `sizes` 写法 |
| --- | --- |
| 全宽 Banner | `100vw` |
| 手机 1 列 / 桌面 2 列 | `(min-width: 750px) 50vw, 100vw` |
| 商品网格：手机 2 列 / 桌面 4 列，页面最大宽 1400px | `(min-width: 1400px) 330px, (min-width: 750px) calc((100vw - 120px) / 4), calc((100vw - 35px) / 2)` |

```liquid
{{ product.featured_image
  | image_url: width: 800
  | image_tag:
    loading: 'lazy',
    widths: '165, 360, 533, 720, 800',
    sizes: '(min-width: 750px) calc((100vw - 120px) / 4), calc((100vw - 35px) / 2)',
    alt: product.featured_image.alt | escape
}}
```

其它要点：

- Shopify CDN 会根据浏览器 `Accept` 头自动返回 WebP/AVIF，**不需要手动转格式**，但 GIF 动图不会被转成视频（见 5.10）。
- `srcset=""` 为空（TORRAS 的视频封面）等于没有响应式图片。检查自定义 section 里拼接 `srcset` 的循环。
- **上传规范**：照片长边 ≤ 2400–3000 px、JPG 质量 80 左右；需要透明背景才用 PNG。

## 5.3 懒加载“首屏之下”的一切

```html
<!-- 首屏以下的 iframe（YouTube、地图、Instagram 等） -->
<iframe src="https://www.youtube.com/embed/xxxx" loading="lazy" width="560" height="315" title="…"></iframe>
```

更好的做法是 **“门面（facade）”模式**：先放一张封面图 + 播放按钮，用户点击后才插入 iframe。一个 YouTube iframe 会加载约 1 MB 的 JS。

## 5.4 首屏视频：先画封面，再加载视频

ReVive 的问题是首屏 2.9 MB 视频和 LCP 封面图一起下载。目标：**封面图作为 LCP 尽快出来；视频在页面 `load` 后、且只为当前设备加载一个合适码率的版本。**

```liquid
{%- liquid
  assign video = section.settings.video
  assign mp4_source = nil
  for source in video.sources
    if source.mime_type == 'video/mp4' and source.height <= 720
      assign mp4_source = source
    endif
  endfor
-%}

<div class="hero-video" data-hero-video>
  {{ video.preview_image
    | image_url: width: 1080
    | image_tag: loading: 'eager', fetchpriority: 'high',
                 widths: '540, 720, 1080', sizes: '100vw',
                 class: 'hero-video__poster' }}

  {%- if mp4_source -%}
    <video class="hero-video__video" muted playsinline loop preload="none"
           data-src="{{ mp4_source.url }}"
           width="{{ mp4_source.width }}" height="{{ mp4_source.height }}"></video>
  {%- endif -%}
</div>

<script>
  (() => {
    const start = () => {
      document.querySelectorAll('[data-hero-video] video[data-src]').forEach((video) => {
        // 只给当前可见的那个 <video> 加载（CSS 隐藏的不会加载）
        if (video.offsetParent === null) return;
        video.src = video.dataset.src;
        video.removeAttribute('data-src');
        video.play().catch(() => {});
        video.addEventListener('playing', () => video.classList.add('is-playing'), { once: true });
      });
    };
    if (document.readyState === 'complete') start();
    else window.addEventListener('load', start, { once: true });
  })();
</script>

<style>
  .hero-video { position: relative; aspect-ratio: 9 / 16; }
  @media (min-width: 750px) { .hero-video { aspect-ratio: 16 / 9; } }
  .hero-video > * { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .hero-video__video { opacity: 0; transition: opacity .3s; }
  .hero-video__video.is-playing { opacity: 1; }
</style>
```

说明：

- `video.sources` 是 Shopify 为上传视频生成的多种清晰度（与 ReVive 页面上看到的 `HD-1080p-4.8Mbps`、`HD-720p-2.1Mbps` 对应）。按 `height` 选一个手机够用的版本。
- 封面图用 `aspect-ratio` 占位，视频播放后淡入覆盖，不会产生布局偏移。
- 更进一步：在 `save-data` 或慢网络（`navigator.connection.effectiveType` 为 `2g`/`3g`）时不加载视频，只显示封面。
- TORRAS 首页的多个 `autoplay` 视频（`preload="metadata"`）同理：首屏之下的视频用 `IntersectionObserver` 进入视口再设置 `src`。

## 5.5 第三方脚本与 App：删除、按页面加载、延后加载

### 第一步：盘点

1. 后台 → 应用：列出所有已安装 App，问一句“这个 App 现在还在产生价值吗？”
2. 主题编辑器 → 左侧 **App embeds**：关闭不再使用的 embed。**卸载 App 并不一定会删除它曾经写入主题的代码**（尤其是 Online Store 2.0 之前的 App），需要在 `theme.liquid`、`snippets/` 里搜索 App 名称手动清理。
3. Google Tag Manager：导出容器，清理不再投放的广告平台标签。
4. 设置 → **客户事件（Customer events）**：广告/分析像素尽量迁移为 Web Pixel（Shopify 会在沙箱中运行，与主题脚本隔离），而不是在 `theme.liquid` 里直接插 `<script>`。

用 DevTools 的 *Block request domain* 逐个屏蔽，测量每个 App 对 TBT/LCP 的影响，把数据作为“删不删”的依据。

### 第二步：只在需要的页面加载

```liquid
{%- comment -%} layout/theme.liquid {%- endcomment -%}
{%- if template.name == 'product' -%}
  <script src="{{ 'product-reviews-widget.js' | asset_url }}" defer></script>
{%- endif -%}

{%- if template.name == 'index' or template.name == 'collection' -%}
  {%- render 'collection-quick-view-scripts' -%}
{%- endif -%}

{%- comment -%} 首页不输出表单 App 的巨型配置（TORRAS 的 Globo 案例） {%- endcomment -%}
{%- if template.name == 'page' and page.handle contains 'contact' -%}
  {%- render 'globo-form-config' -%}
{%- endif -%}
```

> 对于通过 App embed 注入的脚本，主题无法直接加条件。可以：在 App 设置里限定生效页面；改用 App block（只放在需要的模板里）；或联系 App 开发者。

### 第三步：延后加载，并且错峰

```html
<script>
  window.loadScriptLater = (src, { trigger = 'idle', selector, attrs = {} } = {}) => {
    const load = () => {
      if (document.querySelector('script[src="' + src + '"]')) return;
      const s = document.createElement('script');
      s.src = src; s.async = true;
      Object.entries(attrs).forEach(([k, v]) => s.setAttribute(k, v));
      document.head.appendChild(s);
    };

    if (trigger === 'visible' && selector) {
      const el = document.querySelector(selector);
      if (!el) return;
      new IntersectionObserver((entries, io) => {
        if (entries.some((e) => e.isIntersecting)) { io.disconnect(); load(); }
      }, { rootMargin: '300px' }).observe(el);
      return;
    }

    // 'idle'：等页面 load 后，再等浏览器空闲
    const idle = () => ('requestIdleCallback' in window)
      ? requestIdleCallback(load, { timeout: 5000 })
      : setTimeout(load, 3000);
    if (document.readyState === 'complete') idle();
    else addEventListener('load', idle, { once: true });
  };

  // 评价组件：滚动到评价区域附近再加载
  loadScriptLater('https://example-reviews.com/widget.js', { trigger: 'visible', selector: '#reviews' });
  // 聊天、营销弹窗：页面空闲后
  loadScriptLater('https://example-chat.com/loader.js');
</script>
```

注意：

- **不要把所有脚本都挂到“第一次交互（scroll/click/touchstart）”时加载**。这种做法能让 Lab 分数变好看，但用户第一次点击时所有脚本一起执行，INP 会变差（见 [3.4](03-case-torraslife.md#34-第-4-步inp-诊断field-不达标的根因)）。
- 风控、同意管理（Cookie consent）、A/B 测试类脚本有特定的加载时序要求，延后前先与供应商确认。
- **监控类 SDK（如 Sentry）**：ReVive 的 Sentry 完整包消耗 2.2 s CPU。只做错误监控时使用 Sentry 的 Loader Script 懒加载 SDK，关闭或降低 Session Replay 与 Performance Tracing 的采样率。

## 5.6 用 Section Rendering API 按需渲染购物车抽屉/菜单

TORRAS 的 `cart-drawer` section 在每个页面输出约 1 MB HTML。思路：页面里只保留抽屉的空壳，用户打开时再请求内容。

```liquid
{%- comment -%} layout/theme.liquid：只输出空壳 {%- endcomment -%}
<cart-drawer id="CartDrawer" class="drawer" hidden>
  <div class="drawer__inner" data-cart-drawer-content>
    <div class="drawer__loading" aria-busy="true"></div>
  </div>
</cart-drawer>
```

```js
// assets/cart-drawer-lazy.js
class LazyCartDrawer extends HTMLElement {
  async open() {
    this.hidden = false;
    if (!this.loaded) {
      const url = window.Shopify.routes.root + '?sections=cart-drawer';
      const json = await fetch(url).then((r) => r.json());
      const html = new DOMParser().parseFromString(json['cart-drawer'], 'text/html');
      this.querySelector('[data-cart-drawer-content]')
        .replaceChildren(...html.querySelector('[data-cart-drawer-content]').childNodes);
      this.loaded = true;
    }
  }
}
customElements.define('cart-drawer', LazyCartDrawer);
```

- `?sections=cart-drawer` 会返回 `{"cart-drawer": "<div …>…</div>"}`，即该 section 用最新购物车数据渲染的 HTML。加购后的刷新也可以复用这个接口（Dawn 主题的 `/cart/add.js` 请求就带 `sections` 参数）。
- 同样的模式适用于：手机菜单的二、三级菜单、国家/语言选择器（TORRAS 有 230 个选项）、快速查看弹窗。
- 鼠标悬停或 `touchstart` 时可以预取（`fetch` 但不渲染），让打开时几乎无延迟。

## 5.7 CSS：关键 CSS 内联，其余异步

```liquid
{%- comment -%} layout/theme.liquid {%- endcomment -%}
<style>{% render 'critical-css' %}</style>

<link rel="preload" href="{{ 'theme.css' | asset_url }}" as="style" onload="this.onload=null;this.rel='stylesheet'">
<noscript>{{ 'theme.css' | asset_url | stylesheet_tag }}</noscript>

{%- comment -%} 只在用到的地方加载的样式（例如国家旗帜） {%- endcomment -%}
{%- if localization.available_countries.size > 1 -%}
  <link rel="stylesheet" href="{{ 'country-flags.css' | asset_url }}" media="print" onload="this.media='all'">
{%- endif -%}
```

`snippets/critical-css.liquid` 中只放首屏需要的规则：header、首屏 section、字体声明、基础排版。可以用 [critical](https://github.com/addyosmani/critical) 等工具从页面提取，再人工精简（建议 < 15 KB）。

Section 级样式写在 section 文件里，只在 section 被使用时输出：

```liquid
{%- comment -%} sections/image-banner.liquid {%- endcomment -%}
{{ 'section-image-banner.css' | asset_url | stylesheet_tag }}
```

对于首屏之下的 section，可以把样式改为 `media="print" onload="this.media='all'"` 的异步方式（注意它可能造成该区域的短暂无样式状态，测试 CLS）。

> ReVive 的 `theme-customizations.css`（30.6 KiB）几乎和主题主样式（38.8 KiB）一样大。定制样式长期“追加”到一个文件是常见的技术债，建议定期合并和删除不再使用的规则（DevTools → Coverage 面板可查看未使用比例）。

## 5.8 字体

```liquid
{%- comment -%} 预加载首屏正文字体（只预加载 1–2 个） {%- endcomment -%}
<link rel="preload" as="font" type="font/woff2" crossorigin
      href="{{ settings.type_body_font | font_url }}">

<style>
  {{ settings.type_body_font | font_face: font_display: 'swap' }}
  {%- assign body_bold = settings.type_body_font | font_modify: 'weight', 'bold' -%}
  {{ body_bold | font_face: font_display: 'swap' }}
</style>
```

- 首屏使用的字重越少越好；每多一个字重就多一个文件。
- **第三方组件自带的字体**（ReVive 的 Yotpo `nunito_sans`）会形成 “HTML → 第三方 CSS → 字体” 的长链。在组件设置里改为继承站点字体，或者让组件延后加载。
- 预连接（`preconnect`）最多保留 2–4 个首屏真正需要的第三方域名。

## 5.9 INP：让交互先画出来

INP 由三段组成：输入延迟（主线程忙）、处理时间（事件处理函数）、呈现延迟（样式/布局/绘制）。

```js
// 让出主线程：优先使用 scheduler.yield，不支持时回退到 setTimeout
const yieldToMain = () =>
  globalThis.scheduler?.yield ? scheduler.yield() : new Promise((r) => setTimeout(r, 0));

addToCartButton.addEventListener('click', async (event) => {
  // 1. 先做用户能看到的反馈
  addToCartButton.setAttribute('aria-busy', 'true');
  addToCartButton.classList.add('is-loading');

  // 2. 让浏览器先把这一帧画出来
  await yieldToMain();

  // 3. 再做重活：请求、刷新购物车、埋点
  const res = await fetch(window.Shopify.routes.root + 'cart/add.js', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: [{ id: variantId, quantity: 1 }], sections: 'cart-drawer' }),
  });
  const data = await res.json();
  renderCartDrawer(data.sections['cart-drawer']);

  await yieldToMain();
  sendAnalytics('add_to_cart', data); // 埋点放在最后
});
```

减少“呈现延迟”的通用原则：

- **减小 DOM**（5.6），尤其是菜单和抽屉。
- 只切换受影响元素的类名，不要给 `<html>`、`<body>`、`<header>` 这种大容器切换类名。
- 能用 CSS 完成的交互（`:hover`、`details[open]`、`:focus-within`）不用 JS。
- 对首屏之下的大区块使用 `content-visibility: auto; contain-intrinsic-size: auto 800px;`，跳过屏幕外区域的渲染工作。
- 避免在同一个函数里“写样式 → 读 `offsetHeight` → 再写”（Forced reflow 条目里列出的就是这类代码）。

## 5.10 GIF 改为视频

ReVive 的 617 KiB GIF 是典型例子。把 GIF 转成 MP4（例如 `ffmpeg -i in.gif -movflags +faststart -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" out.mp4`），上传到 Shopify（内容 → 文件），然后：

```html
<video autoplay muted loop playsinline preload="none" width="750" height="750"
       poster="{{ 'before-after-poster.jpg' | file_url }}">
  <source src="{{ 'before-after.mp4' | file_url }}" type="video/mp4">
</video>
```

首屏之下的视频结合 5.4 的 `IntersectionObserver` 写法加载。

## 5.11 CLS：给所有媒体留位置

- `image_tag` 自动输出 `width`/`height`；手写 `<img>` 时务必带上 `width`/`height`。
- 视频、iframe、App 区块容器使用 `aspect-ratio` 或 `min-height` 占位。
- 公告条、倒计时、评价星级等由 JS 插入的内容，预先在 HTML 中留出同样高度的占位。
- 字体：`font-display: swap` 会造成轻微重排，可配合 `size-adjust` 的回退字体减小差异。

## 5.12 用 web-vitals 采集真实用户 INP 归因

PSI 的 Field 数据只告诉你“INP 是 219 ms”，不告诉你**是哪个按钮、哪段脚本**。在主题里加入 web-vitals 的 attribution 版本：

```html
<script type="module">
  import { onINP, onLCP, onCLS } from 'https://unpkg.com/web-vitals@4/dist/web-vitals.attribution.js?module';

  const send = (metric) => {
    const a = metric.attribution || {};
    const body = JSON.stringify({
      name: metric.name,
      value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
      rating: metric.rating,
      page: location.pathname,
      // INP：哪个元素、哪种交互、慢在哪一段
      target: a.interactionTarget,
      type: a.interactionType,
      inputDelay: a.inputDelay,
      processing: a.processingDuration,
      presentation: a.presentationDelay,
      // LCP：哪个元素/资源
      lcpElement: a.target,
      lcpUrl: a.url,
    });
    navigator.sendBeacon?.('/apps/your-endpoint/vitals', body); // 或者发送到 GA4
  };

  onINP(send); onLCP(send); onCLS(send);
</script>
```

> 生产环境建议把 web-vitals 打包进主题自己的 JS，而不是依赖 unpkg；也可以发送到 GA4 的自定义事件，在探索报告中按 `target` 汇总最慢的交互。
